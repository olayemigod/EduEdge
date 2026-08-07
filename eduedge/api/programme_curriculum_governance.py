from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.platform.access import require_eduedge_access


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _programme(programme: str, permission_type: str = "write"):
	_require_login()
	name = str(programme or "").strip()
	if not name:
		frappe.throw(_("Select a Class / Programme."), frappe.ValidationError)
	doc = frappe.get_doc("Program", name)
	doc.check_permission(permission_type)
	institution = str(doc.get(INSTITUTION_FIELD) or "").strip()
	if not institution:
		frappe.throw(_("The selected Class / Programme has no Institution context."), frappe.ValidationError)
	institution_doc = frappe.get_doc("EduEdge Institution", institution)
	institution_doc.check_permission("read")
	if not cint(institution_doc.enabled):
		frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)
	return doc, institution


def _course(programme_institution: str, course: str):
	name = str(course or "").strip()
	if not name:
		frappe.throw(_("Select a Subject / Course."), frappe.ValidationError)
	doc = frappe.get_doc("Course", name)
	doc.check_permission("read")
	course_institution = str(doc.get(INSTITUTION_FIELD) or "").strip()
	if course_institution and course_institution != programme_institution:
		frappe.throw(
			_("Subject / Course {0} belongs to another Institution.").format(doc.course_name or doc.name),
			frappe.ValidationError,
		)
	return doc


def _child_row(programme_doc, course: str):
	return next(
		(row for row in programme_doc.get("courses") or [] if str(row.course or "").strip() == course),
		None,
	)


def _list_values(value) -> list[str]:
	if isinstance(value, str):
		try:
			value = frappe.parse_json(value)
		except Exception:
			value = [value]
	if not isinstance(value, (list, tuple, set)):
		return []
	result = []
	for entry in value:
		name = str(entry or "").strip()
		if name and name not in result:
			result.append(name)
	return result


def _programme_offerings(programme: str) -> list[str]:
	if not frappe.db.exists("DocType", "EduEdge Program Offering"):
		return []
	return frappe.get_all(
		"EduEdge Program Offering",
		filters={"program": programme},
		pluck="name",
		limit_page_length=0,
	)


def _count_dependency(doctype: str, filters: dict[str, Any]) -> int:
	if not frappe.db.exists("DocType", doctype):
		return 0
	meta = frappe.get_meta(doctype)
	usable = {key: value for key, value in filters.items() if meta.has_field(key)}
	# Never fall back to a global Subject-only check. Removal is blocked only by
	# dependencies that can be tied to this exact Program or one of its Offerings.
	if len(usable) < 2:
		return 0
	return cint(frappe.db.count(doctype, filters=usable))


def _dependency_summary(programme: str, course: str) -> list[dict]:
	"""Return exact, programme-scoped operational dependencies for a curriculum row."""
	offerings = _programme_offerings(programme)
	specs = (
		("EduEdge Instructor Assignment", "Instructor Assignments", {"course": course, "program_offering": ["in", offerings]}),
		("Course Schedule", "Course Schedules", {"course": course, "program": programme}),
		("Assessment Plan", "Assessment Plans", {"course": course, "program": programme}),
		("Assessment Result", "Assessment Results", {"course": course, "program": programme}),
		("EduEdge CBT Exam Schedule", "CBT Exam Schedules", {"course": course, "program_offering": ["in", offerings]}),
		("EduEdge CBT Exam Template", "CBT Exam Templates", {"course": course, "program": programme}),
	)
	dependencies = []
	for doctype, label, filters in specs:
		if any(isinstance(value, list) and value == ["in", []] for value in filters.values()):
			continue
		count = _count_dependency(doctype, filters)
		if count:
			dependencies.append({"doctype": doctype, "label": label, "count": count})
	return dependencies


def _curriculum_state(programme_doc) -> list[dict]:
	return [
		{
			"course": str(row.course or "").strip(),
			"required": cint(row.get("required", 1)),
			"idx": cint(row.idx),
		}
		for row in programme_doc.get("courses") or []
		if row.course
	]


@frappe.whitelist(methods=["POST"])
def add_programme_courses(
	programme: str,
	courses: str | list | None = None,
	required: int | str = 1,
) -> dict:
	require_eduedge_access(feature_key="academics", action="add_programme_courses")
	doc, institution = _programme(programme, "write")
	selected = _list_values(courses)
	if not selected:
		frappe.throw(_("Select at least one Institution Subject / Course to add."), frappe.ValidationError)
	required_value = 1 if cint(required) else 0
	existing = {str(row.course or "").strip() for row in doc.get("courses") or [] if row.course}
	added = []
	for name in selected:
		_course(institution, name)
		if name in existing:
			continue
		doc.append("courses", {"course": name, "required": required_value})
		existing.add(name)
		added.append(name)
	if added:
		doc.save()
	return {
		"added": added,
		"added_count": len(added),
		"required": required_value,
		"curriculum": _curriculum_state(doc),
	}


@frappe.whitelist(methods=["POST"])
def update_programme_course_requirement(programme: str, course: str, required: int | str) -> dict:
	require_eduedge_access(feature_key="academics", action="update_programme_course_requirement")
	doc, institution = _programme(programme, "write")
	course_doc = _course(institution, course)
	row = _child_row(doc, course_doc.name)
	if not row:
		frappe.throw(_("The selected Subject / Course is not configured for this Class."), frappe.DoesNotExistError)
	row.required = 1 if cint(required) else 0
	doc.save()
	return {
		"programme": doc.name,
		"course": course_doc.name,
		"required": cint(row.required),
		"curriculum": _curriculum_state(doc),
	}


@frappe.whitelist(methods=["POST"])
def remove_programme_course(programme: str, course: str) -> dict:
	require_eduedge_access(feature_key="academics", action="remove_programme_course")
	doc, institution = _programme(programme, "write")
	course_doc = _course(institution, course)
	row = _child_row(doc, course_doc.name)
	if not row:
		frappe.throw(_("The selected Subject / Course is not configured for this Class."), frappe.DoesNotExistError)
	dependencies = _dependency_summary(doc.name, course_doc.name)
	if dependencies:
		detail = "\n".join(_("• {0}: {1}").format(item["label"], item["count"]) for item in dependencies)
		frappe.throw(
			_("{0} cannot be removed from {1} because it is already used by:\n{2}\n\nExisting academic history will not be altered.").format(
				course_doc.course_name or course_doc.name,
				doc.program_name or doc.name,
				detail,
			),
			frappe.ValidationError,
		)
	doc.remove(row)
	doc.save()
	return {
		"programme": doc.name,
		"course": course_doc.name,
		"removed": True,
		"subject_master_deleted": False,
		"curriculum": _curriculum_state(doc),
	}
