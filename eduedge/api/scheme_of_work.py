from __future__ import annotations

from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from eduedge.education.instructor_assignment_capabilities import (
	assignment_capability_enforcement_enabled,
	get_matching_instructor_capability_assignments,
)
from eduedge.education.instructor_scope import is_limited_instructor_user
from eduedge.education.offerings import assert_branch_access
from eduedge.eduedge.doctype.eduedge_scheme_of_work.eduedge_scheme_of_work import (
	SCHEME_ACTION_FLAG,
	snapshot_scheme_context,
)
from eduedge.platform.access import require_eduedge_access

SCHEME_DOCTYPE = "EduEdge Scheme of Work"
SCHEME_MANAGER_ROLES = {
	"Administrator",
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
}
EDITABLE_FIELDS = ("school_branch", "program_offering", "student_group", "course", "notes")
ITEM_FIELDS = (
	"sequence",
	"week_no",
	"topic",
	"learning_objective",
	"planned_start_date",
	"planned_end_date",
	"estimated_periods",
	"notes",
)


def _parse_payload(payload) -> dict:
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	if not isinstance(payload, dict):
		frappe.throw(_("A valid Scheme of Work payload is required."), frappe.ValidationError)
	return payload


def _is_manager() -> bool:
	return frappe.session.user == "Administrator" or bool(
		SCHEME_MANAGER_ROLES.intersection(set(frappe.get_roles(frappe.session.user)) | {frappe.session.user})
	)


def _context_authorized(doc, *, write: bool) -> bool:
	assert_branch_access(doc.school_branch)
	if _is_manager():
		permission = "write" if write and not doc.is_new() else "create" if write else "read"
		if not frappe.has_permission(SCHEME_DOCTYPE, permission):
			frappe.throw(_("You are not permitted to manage Schemes of Work."), frappe.PermissionError)
		return True
	if not is_limited_instructor_user():
		frappe.throw(_("You are not permitted to manage Schemes of Work."), frappe.PermissionError)
	identity_status, _instructor, assignments = get_matching_instructor_capability_assignments(
		user=frappe.session.user,
		school_branch=doc.school_branch,
		program_offering=doc.program_offering,
		student_group=doc.student_group,
		course=doc.course,
		on_date=doc.period_start_date,
	)
	if identity_status != "resolved" or not assignments:
		frappe.throw(
			_("Your exact Instructor Assignment does not cover this Scheme's Branch, Class, Class Arm and Subject context."),
			frappe.PermissionError,
		)
	if assignment_capability_enforcement_enabled():
		capability = "can_manage_subject_topics" if write else "can_view_subject_content"
		if not any(cint(row.get(capability)) for row in assignments):
			frappe.throw(
				_("Your exact Instructor Assignment does not grant the required curriculum capability for this Scheme of Work."),
				frappe.PermissionError,
			)
	return True


@contextmanager
def _scheme_action():
	previous = getattr(frappe.flags, SCHEME_ACTION_FLAG, False)
	setattr(frappe.flags, SCHEME_ACTION_FLAG, True)
	try:
		yield
	finally:
		setattr(frappe.flags, SCHEME_ACTION_FLAG, previous)


def _serialize(doc) -> dict:
	return {
		"name": doc.name,
		"scheme_title": doc.scheme_title,
		"status": doc.status,
		"version_no": cint(doc.version_no),
		"supersedes_scheme": doc.supersedes_scheme or "",
		"institution": doc.institution,
		"school_branch": doc.school_branch,
		"program_offering": doc.program_offering,
		"student_group": doc.student_group or "",
		"course": doc.course,
		"academic_year": doc.academic_year,
		"academic_term": doc.academic_term or "",
		"period_start_date": doc.period_start_date,
		"period_end_date": doc.period_end_date,
		"prepared_by": doc.prepared_by or "",
		"approved_by": doc.approved_by or "",
		"approved_on": doc.approved_on,
		"snapshot_on": doc.snapshot_on,
		"offering_title_snapshot": doc.offering_title_snapshot or "",
		"student_group_name_snapshot": doc.student_group_name_snapshot or "",
		"course_name_snapshot": doc.course_name_snapshot or "",
		"notes": doc.notes or "",
		"items": [
			{
				"name": row.name,
				"sequence": cint(row.sequence),
				"week_no": cint(row.week_no),
				"topic": row.topic,
				"topic_name_snapshot": row.topic_name_snapshot or "",
				"topic_description_snapshot": row.topic_description_snapshot or "",
				"learning_objective": row.learning_objective or "",
				"planned_start_date": row.planned_start_date,
				"planned_end_date": row.planned_end_date,
				"estimated_periods": cint(row.estimated_periods),
				"notes": row.notes or "",
			}
			for row in doc.get("items") or []
		],
	}


@frappe.whitelist()
def get_scheme(name: str) -> dict:
	require_eduedge_access(feature_key="academics", action="view_scheme_of_work")
	doc = frappe.get_doc(SCHEME_DOCTYPE, name)
	_context_authorized(doc, write=False)
	return _serialize(doc)


@frappe.whitelist()
def get_schemes(
	school_branch: str,
	program_offering: str | None = None,
	student_group: str | None = None,
	course: str | None = None,
	status: str | None = None,
	start: int = 0,
	page_length: int = 25,
) -> dict:
	require_eduedge_access(feature_key="academics", action="view_scheme_of_work")
	branch = str(school_branch or "").strip()
	assert_branch_access(branch)
	filters = {"school_branch": branch}
	for fieldname, value in {
		"program_offering": program_offering,
		"student_group": student_group,
		"course": course,
		"status": status,
	}.items():
		if value:
			filters[fieldname] = value
	rows = frappe.get_all(
		SCHEME_DOCTYPE,
		filters=filters,
		fields=[
			"name", "scheme_title", "status", "version_no", "school_branch", "program_offering",
			"student_group", "course", "academic_year", "academic_term", "period_start_date", "period_end_date",
		],
		order_by="academic_year desc, academic_term desc, course asc, version_no desc",
		start=max(cint(start), 0),
		page_length=min(max(cint(page_length) or 25, 1), 50) + 1,
	)
	visible = []
	for row in rows:
		doc = frappe.get_doc(SCHEME_DOCTYPE, row.name)
		try:
			_context_authorized(doc, write=False)
		except frappe.PermissionError:
			continue
		visible.append(dict(row))
	limit = min(max(cint(page_length) or 25, 1), 50)
	return {"rows": visible[:limit], "has_more": len(visible) > limit}


@frappe.whitelist(methods=["POST"])
def save_scheme(payload) -> dict:
	require_eduedge_access(feature_key="academics", action="save_scheme_of_work")
	data = _parse_payload(payload)
	name = str(data.get("name") or "").strip()
	if name:
		doc = frappe.get_doc(SCHEME_DOCTYPE, name)
		if doc.status != "Draft":
			frappe.throw(_("Approved Schemes of Work are immutable. Create a new version instead."), frappe.ValidationError)
	else:
		doc = frappe.new_doc(SCHEME_DOCTYPE)
		doc.version_no = 1
	for fieldname in EDITABLE_FIELDS:
		if fieldname in data:
			doc.set(fieldname, data.get(fieldname))
	if "items" in data:
		doc.set("items", [])
		for item in data.get("items") or []:
			doc.append("items", {fieldname: item.get(fieldname) for fieldname in ITEM_FIELDS})
	doc.run_method("validate")
	_context_authorized(doc, write=True)
	if doc.is_new():
		doc.insert(ignore_permissions=not _is_manager())
	else:
		doc.save(ignore_permissions=not _is_manager())
	return _serialize(doc)


@frappe.whitelist(methods=["POST"])
def approve_scheme(name: str) -> dict:
	require_eduedge_access(feature_key="academics", action="approve_scheme_of_work")
	if not _is_manager():
		frappe.throw(_("Only academic management can approve a Scheme of Work."), frappe.PermissionError)
	frappe.db.savepoint("eduedge_scheme_approve")
	try:
		frappe.db.sql("select name from `tabEduEdge Scheme of Work` where name = %s for update", (name,))
		doc = frappe.get_doc(SCHEME_DOCTYPE, name)
		doc.check_permission("write")
		if doc.status == "Approved":
			return _serialize(doc)
		if doc.status != "Draft":
			frappe.throw(_("Only a Draft Scheme of Work can be approved."), frappe.ValidationError)
		if not doc.get("items"):
			frappe.throw(_("Add at least one Scheme item before approval."), frappe.ValidationError)
		with _scheme_action():
			doc.run_method("validate")
			snapshot_scheme_context(doc)
			doc.status = "Approved"
			doc.approved_by = frappe.session.user
			doc.approved_on = now_datetime()
			doc.snapshot_on = doc.approved_on
			if doc.supersedes_scheme:
				previous = frappe.get_doc(SCHEME_DOCTYPE, doc.supersedes_scheme)
				if previous.status == "Approved":
					previous.status = "Retired"
					previous.save()
			doc.save()
		doc.add_comment("Info", _("Scheme of Work approved and curriculum labels snapshotted."))
		return _serialize(doc)
	except Exception:
		frappe.db.rollback(save_point="eduedge_scheme_approve")
		raise


@frappe.whitelist(methods=["POST"])
def create_next_version(name: str) -> dict:
	require_eduedge_access(feature_key="academics", action="version_scheme_of_work")
	if not _is_manager():
		frappe.throw(_("Only academic management can create a governed Scheme version."), frappe.PermissionError)
	source = frappe.get_doc(SCHEME_DOCTYPE, name)
	source.check_permission("read")
	if source.status not in {"Approved", "Retired"}:
		frappe.throw(_("Only an Approved or Retired Scheme can start a new version."), frappe.ValidationError)
	with _scheme_action():
		doc = frappe.copy_doc(source)
		doc.name = None
		doc.status = "Draft"
		doc.version_no = cint(source.version_no) + 1
		doc.supersedes_scheme = source.name
		doc.prepared_by = frappe.session.user
		doc.approved_by = None
		doc.approved_on = None
		doc.snapshot_on = None
		doc.offering_title_snapshot = None
		doc.student_group_name_snapshot = None
		doc.course_name_snapshot = None
		for row in doc.get("items") or []:
			row.topic_name_snapshot = None
			row.topic_description_snapshot = None
		doc.insert()
	return _serialize(doc)


@frappe.whitelist(methods=["POST"])
def retire_scheme(name: str) -> dict:
	require_eduedge_access(feature_key="academics", action="retire_scheme_of_work")
	if not _is_manager():
		frappe.throw(_("Only academic management can retire a Scheme of Work."), frappe.PermissionError)
	doc = frappe.get_doc(SCHEME_DOCTYPE, name)
	doc.check_permission("write")
	if doc.status == "Retired":
		return _serialize(doc)
	if doc.status != "Approved":
		frappe.throw(_("Only an Approved Scheme of Work can be retired."), frappe.ValidationError)
	with _scheme_action():
		doc.status = "Retired"
		doc.save()
	doc.add_comment("Info", _("Scheme of Work retired; historical snapshot retained."))
	return _serialize(doc)
