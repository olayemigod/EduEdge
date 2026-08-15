from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.api import class_arms as class_arm_api
from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.class_arm_identity import (
	CLASS_ARM_DOCTYPE,
	CLASS_ARM_FIELD,
	generate_operational_group_name,
)
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.platform.access import require_eduedge_access

MAX_SELECTION = 500


DOWNSTREAM_ALIGNMENT = {
	"class_arm_scope": "Academic Session",
	"term_scope": "Assessment Plans, Result Publication and CBT Schedules",
	"assessment_plans_carried_forward": False,
	"assessment_results_carried_forward": False,
	"cbt_schedules_carried_forward": False,
	"cbt_attempts_or_results_carried_forward": False,
	"message": (
		"Only the next-session Class Arm Student Group and destination-session eligible roster are prepared. "
		"Assessment Plans, Assessment Results, CBT Schedules, attempts and results remain exact historical records. "
		"Create the destination session/term academic activities against the newly prepared Student Group."
	),
}


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_create_permission() -> None:
	_require_login()
	if not frappe.has_permission("Student Group", "create"):
		frappe.throw(
			_("You are not permitted to create Class Arms for the next Academic Session."),
			frappe.PermissionError,
		)


def _parse_identity_selection(value: Any) -> list[str]:
	if isinstance(value, str):
		value = frappe.parse_json(value)
	if not isinstance(value, list):
		frappe.throw(_("Select one or more Class Arms to carry forward."), frappe.ValidationError)

	result: list[str] = []
	seen: set[str] = set()
	for raw in value:
		if isinstance(raw, dict):
			identity = str(raw.get("class_arm_identity") or raw.get("name") or "").strip()
		else:
			identity = str(raw or "").strip()
		if not identity or identity in seen:
			continue
		seen.add(identity)
		result.append(identity)

	if not result:
		frappe.throw(_("Select at least one ready Class Arm to carry forward."), frappe.ValidationError)
	if len(result) > MAX_SELECTION:
		frappe.throw(
			_("A maximum of {0} Class Arms can be prepared in one batch.").format(MAX_SELECTION),
			frappe.ValidationError,
		)
	return result


def _selected_plan_rows(plan: dict, identities: list[str]) -> list[dict]:
	rows_by_identity = {
		str(row.get("class_arm_identity")): row
		for row in plan.get("rows") or []
		if row.get("class_arm_identity")
	}
	unknown = [identity for identity in identities if identity not in rows_by_identity]
	if unknown:
		frappe.throw(
			_(
				"One or more selected Class Arms are no longer part of the source-session rollover plan. Refresh the preview and try again."
			),
			frappe.ValidationError,
		)
	return [rows_by_identity[identity] for identity in identities]


def _create_destination_group(row: dict, branch: str) -> tuple[dict, bool]:
	"""Create exactly one destination-session Student Group from a revalidated plan row."""
	if row.get("status") != "ready":
		frappe.throw(_("Only a ready Class Arm can be created."), frappe.ValidationError)

	source_doc = frappe.get_doc("Student Group", row.get("source"))
	source_doc.check_permission("read")
	if source_doc.get(BRANCH_FIELD) != branch:
		frappe.throw(_("Source Class Arm belongs to another Branch / Campus."), frappe.PermissionError)

	# Serialise by reusable Class Arm identity so two concurrent requests cannot
	# intentionally prepare the same destination Class Arm twice.
	identity = frappe.get_doc(CLASS_ARM_DOCTYPE, row.get("class_arm_identity"), for_update=True)
	identity.check_permission("read")
	destination = class_arm_api._get_offering(row.get("destination_offering"), branch)

	existing = frappe.db.exists(
		"Student Group",
		{
			CLASS_ARM_FIELD: identity.name,
			OFFERING_FIELD: destination.name,
			"academic_term": ["is", "not set"],
		},
	)
	if existing:
		return {
			"name": existing,
			"display_name": identity.class_arm_name,
			"source": source_doc.name,
			"destination_offering": destination.name,
			"eligible_count": cint(row.get("eligible_count")),
			"excluded_count": cint(row.get("excluded_count")),
		}, False

	doc = frappe.new_doc("Student Group")
	doc.student_group_name = generate_operational_group_name(
		friendly_name=identity.class_arm_name,
		branch=branch,
		program=destination.program,
		offering=destination.name,
		academic_year=destination.academic_year,
	)
	class_arm_api._set_operational_context(
		doc,
		destination,
		identity,
		previous_student_group=source_doc.name,
	)
	doc.group_based_on = source_doc.group_based_on
	doc.course = source_doc.course
	doc.max_strength = source_doc.max_strength
	doc.disabled = 0
	class_arm_api._merge_students(
		doc,
		[{"student": student.get("name")} for student in row.get("eligible_students") or []],
	)
	doc.save()
	return {
		"name": doc.name,
		"display_name": identity.class_arm_name,
		"source": source_doc.name,
		"destination_offering": destination.name,
		"eligible_count": cint(row.get("eligible_count")),
		"excluded_count": cint(row.get("excluded_count")),
	}, True


def _single_source_context(source: str) -> tuple[frappe.model.document.Document, str]:
	_require_login()
	doc = frappe.get_doc("Student Group", source)
	doc.check_permission("read")
	if cint(doc.disabled):
		frappe.throw(_("A disabled Class Arm cannot be carried forward."), frappe.ValidationError)
	if doc.academic_term:
		frappe.throw(
			_("Historical term-bound Class Arms cannot be carried forward individually. Use the sessional Class Arm."),
			frappe.ValidationError,
		)
	if not doc.get(CLASS_ARM_FIELD):
		frappe.throw(_("This Class Arm has no reusable Class Arm identity."), frappe.ValidationError)
	if not doc.academic_year:
		frappe.throw(_("Source Class Arm has no Academic Session."), frappe.ValidationError)
	branch = str(doc.get(BRANCH_FIELD) or "").strip()
	if not branch:
		frappe.throw(_("Source Class Arm has no Branch / Campus."), frappe.ValidationError)
	class_arm_api.assert_branch_access(branch)
	return doc, branch


def _single_plan(source: str, destination_academic_year: str) -> tuple[dict, dict]:
	doc, branch = _single_source_context(source)
	plan = class_arm_api._session_rollover_plan(
		branch,
		doc.academic_year,
		destination_academic_year,
	)
	identity = doc.get(CLASS_ARM_FIELD)
	row = next(
		(
			candidate
			for candidate in plan.get("rows") or []
			if candidate.get("source") == doc.name
			or (
				candidate.get("class_arm_identity") == identity
				and candidate.get("status") == "blocked"
			)
		),
		None,
	)
	if not row:
		frappe.throw(
			_("This Class Arm is no longer an eligible source for the selected Academic Session. Refresh and try again."),
			frappe.ValidationError,
		)
	return plan, row


@frappe.whitelist(methods=["POST"])
def execute_selected_class_arm_session_rollover(
	branch: str,
	source_academic_year: str,
	destination_academic_year: str,
	class_arm_identities: Any,
) -> dict:
	"""Prepare only the Class Arms explicitly selected from a fresh rollover plan."""
	_require_create_permission()
	require_eduedge_access(feature_key="academics", action="execute_selected_class_arm_session_rollover")
	identities = _parse_identity_selection(class_arm_identities)
	plan = class_arm_api._session_rollover_plan(branch, source_academic_year, destination_academic_year)
	rows = _selected_plan_rows(plan, identities)

	created: list[dict] = []
	existing: list[dict] = []
	blocked: list[dict] = []
	for row in rows:
		if row.get("status") == "blocked":
			blocked.append(row)
			continue
		if row.get("status") == "existing":
			existing.append(row)
			continue
		result, was_created = _create_destination_group(row, branch)
		(created if was_created else existing).append(result)

	return {
		"source_academic_year": source_academic_year,
		"destination_academic_year": destination_academic_year,
		"selected_count": len(identities),
		"created": created,
		"existing": existing,
		"blocked": blocked,
		"created_count": len(created),
		"existing_count": len(existing),
		"blocked_count": len(blocked),
		"downstream_alignment": dict(DOWNSTREAM_ALIGNMENT),
	}


@frappe.whitelist(methods=["POST"])
def preview_single_class_arm_session_rollover(source: str, destination_academic_year: str) -> dict:
	"""Preview one explicit sessional Class Arm against a later Academic Session."""
	_require_login()
	require_eduedge_access(feature_key="academics", action="preview_single_class_arm_session_rollover")
	plan, row = _single_plan(source, destination_academic_year)
	return {
		"source_academic_year": plan.get("source_academic_year"),
		"destination_academic_year": plan.get("destination_academic_year"),
		"row": row,
		"downstream_alignment": dict(DOWNSTREAM_ALIGNMENT),
	}


@frappe.whitelist(methods=["POST"])
def execute_single_class_arm_session_rollover(source: str, destination_academic_year: str) -> dict:
	"""Carry one explicit sessional Class Arm forward using the same governed planner as bulk."""
	_require_create_permission()
	require_eduedge_access(feature_key="academics", action="execute_single_class_arm_session_rollover")
	plan, row = _single_plan(source, destination_academic_year)
	if row.get("status") == "blocked":
		frappe.throw(str(row.get("reason") or _("This Class Arm is blocked from carry-forward.")), frappe.ValidationError)
	if row.get("status") == "existing":
		return {
			"source_academic_year": plan.get("source_academic_year"),
			"destination_academic_year": plan.get("destination_academic_year"),
			"created_count": 0,
			"existing_count": 1,
			"blocked_count": 0,
			"existing": [row],
			"downstream_alignment": dict(DOWNSTREAM_ALIGNMENT),
		}

	branch = str(plan.get("branch", {}).get("name") or "").strip()
	result, was_created = _create_destination_group(row, branch)
	return {
		"source_academic_year": plan.get("source_academic_year"),
		"destination_academic_year": plan.get("destination_academic_year"),
		"created_count": 1 if was_created else 0,
		"existing_count": 0 if was_created else 1,
		"blocked_count": 0,
		"created": [result] if was_created else [],
		"existing": [] if was_created else [result],
		"downstream_alignment": dict(DOWNSTREAM_ALIGNMENT),
	}
