from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, getdate

from eduedge.api import class_arms as class_arm_api
from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.academic_progression import PROGRESSION_LEVEL_FIELD
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
	"student_roster_carried_forward": False,
	"student_progression_required": True,
	"term_scope": "Assessment Plans, Result Publication and CBT Schedules",
	"assessment_plans_carried_forward": False,
	"assessment_results_carried_forward": False,
	"cbt_schedules_carried_forward": False,
	"cbt_attempts_or_results_carried_forward": False,
	"message": (
		"Next-session Class Arm preparation creates structure only and does not copy Students. "
		"Student Progression prepares and submits each destination Program Enrollment, then allocates the Student "
		"to a prepared destination Class Arm. Assessment Plans, Assessment Results, CBT Schedules, attempts and "
		"results remain exact historical records."
	),
}


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_read_permission() -> None:
	_require_login()
	if not frappe.has_permission("Student Group", "read"):
		frappe.throw(_("You are not permitted to view Class Arms."), frappe.PermissionError)


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


def _source_student_count(student_group: str | None) -> int:
	if not student_group:
		return 0
	return cint(
		frappe.db.count(
			"Student Group Student",
			{
				"parent": student_group,
				"parenttype": "Student Group",
				"active": 1,
			},
		)
	)


def _structural_rollover_row(source: dict, destinations: list[dict]) -> dict:
	"""Plan destination structure without depending on next-session enrollment.

	Class Arms are prepared before Student Progression. The source roster is shown only
	as an operational count; no learner is copied to the destination Student Group here.
	"""
	if source.get("blocked_reason"):
		return {
			"class_arm_identity": source.get("class_arm_identity"),
			"status": "blocked",
			"reason": source.get("blocked_reason"),
		}

	identity = frappe.db.get_value(
		CLASS_ARM_DOCTYPE,
		source.get(CLASS_ARM_FIELD),
		["name", "class_arm_name", "class_arm_code", "program", "enabled"],
		as_dict=True,
	)
	if not identity or not cint(identity.enabled):
		return {
			"source": source.get("name"),
			"class_arm_identity": source.get(CLASS_ARM_FIELD),
			"status": "blocked",
			"reason": "Reusable Class Arm identity is missing or disabled.",
		}

	source_offering_name = source.get(OFFERING_FIELD)
	if not source_offering_name:
		return {
			"source": source.get("name"),
			"class_arm_identity": identity.name,
			"display_name": identity.class_arm_name,
			"program": identity.program,
			"status": "blocked",
			"reason": "Source Class Arm has no Programme Offering.",
		}

	source_offering = class_arm_api._get_offering(
		source_offering_name,
		source.get(BRANCH_FIELD),
		require_enrollment=False,
		allow_legacy_term=True,
		require_active=False,
	)
	destination, reason = class_arm_api._match_destination_offering(source_offering, destinations)
	if reason:
		return {
			"source": source.get("name"),
			"class_arm_identity": identity.name,
			"display_name": identity.class_arm_name,
			"program": identity.program,
			"status": "blocked",
			"legacy_source": bool(source.get("legacy_source")),
			"reason": reason,
		}

	existing = frappe.db.exists(
		"Student Group",
		{
			CLASS_ARM_FIELD: identity.name,
			OFFERING_FIELD: destination["name"],
			"academic_term": ["is", "not set"],
		},
	)
	source_count = _source_student_count(source.get("name"))
	return {
		"source": source.get("name"),
		"class_arm_identity": identity.name,
		"display_name": identity.class_arm_name,
		"class_arm_code": identity.class_arm_code,
		"program": identity.program,
		"source_offering": source_offering.name,
		"destination_offering": destination["name"],
		"destination_academic_year": destination["academic_year"],
		"status": "existing" if existing else "ready",
		"existing_student_group": existing,
		"legacy_source": bool(source.get("legacy_source")),
		"source_student_count": source_count,
		"students_pending_progression": source_count,
		# Compatibility metrics remain zero because structural rollover deliberately
		# does not classify or copy destination students before progression approval.
		"eligible_students": [],
		"eligible_count": 0,
		"excluded_students": [],
		"excluded_count": 0,
	}


def _structural_session_rollover_plan(
	branch: str,
	source_academic_year: str,
	destination_academic_year: str,
) -> dict:
	_require_read_permission()
	branch, selected_branch, _branches = class_arm_api._resolve_branch(branch)
	if not source_academic_year or not destination_academic_year:
		frappe.throw(_("Source and destination Academic Sessions are required."), frappe.ValidationError)
	if source_academic_year == destination_academic_year:
		frappe.throw(_("Destination Academic Session must be different from the source Session."), frappe.ValidationError)
	class_arm_api._assert_year_read(source_academic_year)
	class_arm_api._assert_year_read(destination_academic_year)
	source_start = frappe.db.get_value("Academic Year", source_academic_year, "year_start_date")
	destination_start = frappe.db.get_value("Academic Year", destination_academic_year, "year_start_date")
	if source_start and destination_start and getdate(destination_start) <= getdate(source_start):
		frappe.throw(_("Select a later destination Academic Session."), frappe.ValidationError)

	destinations = class_arm_api._destination_offerings(branch, destination_academic_year)
	rows = [
		_structural_rollover_row(source, destinations)
		for source in class_arm_api._select_source_groups(branch, source_academic_year)
	]
	return {
		"branch": selected_branch,
		"source_academic_year": source_academic_year,
		"destination_academic_year": destination_academic_year,
		"rows": rows,
		"summary": {
			"total": len(rows),
			"ready": sum(1 for row in rows if row.get("status") == "ready"),
			"existing": sum(1 for row in rows if row.get("status") == "existing"),
			"blocked": sum(1 for row in rows if row.get("status") == "blocked"),
			"source_students": sum(cint(row.get("source_student_count")) for row in rows),
			"students_pending_progression": sum(cint(row.get("students_pending_progression")) for row in rows),
			# Compatibility fields retained for older clients; structural rollover never
			# copies learners into the destination group.
			"students_to_carry": 0,
			"students_excluded": 0,
		},
		"downstream_alignment": dict(DOWNSTREAM_ALIGNMENT),
	}


def _create_destination_group(row: dict, branch: str) -> tuple[dict, bool]:
	"""Create one empty next-session Student Group from a revalidated structural plan."""
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
			"source_student_count": cint(row.get("source_student_count")),
			"students_pending_progression": cint(row.get("students_pending_progression")),
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
	if doc.meta.has_field(PROGRESSION_LEVEL_FIELD) and source_doc.meta.has_field(PROGRESSION_LEVEL_FIELD):
		# The structural Class Arm/lecture group remains at the same Academic Level
		# across sessions. Student Progression moves learners to a different Level/group;
		# Class Arm rollover must not silently promote the structure itself.
		doc.set(PROGRESSION_LEVEL_FIELD, source_doc.get(PROGRESSION_LEVEL_FIELD))
	# Deliberately leave the destination roster empty. Student Progression creates a
	# submitted destination Program Enrollment first, then allocates the learner to
	# the selected destination Class Arm. This keeps structure preparation independent
	# from progression approval and prevents circular next-session setup dependencies.
	doc.save()
	return {
		"name": doc.name,
		"display_name": identity.class_arm_name,
		"source": source_doc.name,
		"destination_offering": destination.name,
		"source_student_count": cint(row.get("source_student_count")),
		"students_pending_progression": cint(row.get("students_pending_progression")),
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
	plan = _structural_session_rollover_plan(
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
def preview_class_arm_session_rollover(
	branch: str,
	source_academic_year: str,
	destination_academic_year: str,
) -> dict:
	"""Preview next-session Class Arm structure without copying learner rosters."""
	_require_login()
	require_eduedge_access(feature_key="academics", action="preview_class_arm_session_rollover")
	return _structural_session_rollover_plan(branch, source_academic_year, destination_academic_year)


@frappe.whitelist(methods=["POST"])
def execute_selected_class_arm_session_rollover(
	branch: str,
	source_academic_year: str,
	destination_academic_year: str,
	class_arm_identities: Any,
) -> dict:
	"""Prepare only explicitly selected Class Arm structures from a fresh plan."""
	_require_create_permission()
	require_eduedge_access(feature_key="academics", action="execute_selected_class_arm_session_rollover")
	identities = _parse_identity_selection(class_arm_identities)
	plan = _structural_session_rollover_plan(branch, source_academic_year, destination_academic_year)
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
def execute_all_class_arm_session_rollover(
	branch: str,
	source_academic_year: str,
	destination_academic_year: str,
) -> dict:
	"""Compatibility action: prepare every ready structural Class Arm in one governed batch."""
	_require_create_permission()
	require_eduedge_access(feature_key="academics", action="execute_all_class_arm_session_rollover")
	plan = _structural_session_rollover_plan(branch, source_academic_year, destination_academic_year)
	identities = [
		row.get("class_arm_identity")
		for row in plan.get("rows") or []
		if row.get("status") == "ready" and row.get("class_arm_identity")
	]
	if not identities:
		return {
			"source_academic_year": source_academic_year,
			"destination_academic_year": destination_academic_year,
			"selected_count": 0,
			"created": [],
			"existing": [row for row in plan.get("rows") or [] if row.get("status") == "existing"],
			"blocked": [row for row in plan.get("rows") or [] if row.get("status") == "blocked"],
			"created_count": 0,
			"existing_count": sum(1 for row in plan.get("rows") or [] if row.get("status") == "existing"),
			"blocked_count": sum(1 for row in plan.get("rows") or [] if row.get("status") == "blocked"),
			"downstream_alignment": dict(DOWNSTREAM_ALIGNMENT),
		}
	return execute_selected_class_arm_session_rollover(
		branch=branch,
		source_academic_year=source_academic_year,
		destination_academic_year=destination_academic_year,
		class_arm_identities=identities,
	)


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
