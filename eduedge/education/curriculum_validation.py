from __future__ import annotations

import frappe
from frappe import _

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.academic_validation import before_validate_course as validate_course_context
from eduedge.education.curriculum_fields import TOPIC_COURSE_FIELD
from eduedge.education.curriculum_permissions import assigned_courses, is_teacher_user

COURSE_IDENTITY_FIELDS = (
	"course_name",
	"department",
	INSTITUTION_FIELD,
	"default_grading_scale",
)
CHILD_META_FIELDS = {
	"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx",
	"parent", "parentfield", "parenttype", "doctype",
}


def _child_signature(rows) -> list[dict]:
	return [
		{
			key: value
			for key, value in row.as_dict(no_nulls=False).items()
			if key not in CHILD_META_FIELDS
		}
		for row in rows or []
	]


def before_validate_course(doc, method=None) -> None:
	validate_course_context(doc, method)
	if not is_teacher_user():
		return
	if doc.is_new():
		frappe.throw(_("Assigned teachers cannot create Course / Subject master records."), frappe.PermissionError)
	if doc.name not in assigned_courses():
		frappe.throw(_("This Course / Subject is not actively assigned to you."), frappe.PermissionError)
	before = doc.get_doc_before_save()
	if not before:
		return
	for fieldname in COURSE_IDENTITY_FIELDS:
		if doc.get(fieldname) != before.get(fieldname):
			frappe.throw(
			_("Assigned teachers cannot change Course / Subject identity, department, Institution, or grading governance."),
			frappe.PermissionError,
		)
	if _child_signature(doc.get("assessment_criteria")) != _child_signature(before.get("assessment_criteria")):
		frappe.throw(
			_("Assigned teachers cannot change Course assessment criteria from the curriculum workspace."),
			frappe.PermissionError,
		)


def before_validate_topic(doc, method=None) -> None:
	course = doc.get(TOPIC_COURSE_FIELD)
	if not course:
		if is_teacher_user():
			frappe.throw(_("Owning Course / Subject is required for teacher-managed Topics."), frappe.ValidationError)
		return
	institution = frappe.db.get_value("Course", course, INSTITUTION_FIELD)
	if not institution:
		frappe.throw(_("The selected Course / Subject has no Institution context."), frappe.ValidationError)
	doc.set(INSTITUTION_FIELD, institution)
	if not is_teacher_user():
		return
	if course not in assigned_courses():
		frappe.throw(_("You can manage Topics only for Courses / Subjects actively assigned to you."), frappe.PermissionError)
	before = doc.get_doc_before_save()
	if before and (
		doc.get("topic_name") != before.get("topic_name")
		or doc.get(TOPIC_COURSE_FIELD) != before.get(TOPIC_COURSE_FIELD)
	):
		frappe.throw(
			_("Assigned teachers cannot rename a saved Topic or move it to another Course / Subject."),
			frappe.PermissionError,
		)
