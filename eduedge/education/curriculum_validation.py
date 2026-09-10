from __future__ import annotations

import frappe
from frappe import _

from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.academic_validation import before_validate_course as validate_course_context
from eduedge.education.curriculum_fields import (
	TOPIC_COURSE_FIELD,
	TOPIC_GROUP_FIELD,
	TOPIC_OFFERING_FIELD,
	TOPIC_SCOPE_CLASS,
	TOPIC_SCOPE_CLASS_ARM,
	TOPIC_SCOPE_FIELD,
	TOPIC_SCOPE_INSTITUTION,
	TOPIC_SCOPES,
)
from eduedge.education.curriculum_permissions import is_teacher_user
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.teaching_assignments import require_course_assignment

COURSE_GOVERNANCE_FIELDS = (
	"course_name",
	"department",
	INSTITUTION_FIELD,
	"default_grading_scale",
	"description",
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
	if getattr(frappe.flags, "in_eduedge_topic_link_update", False):
		before = doc.get_doc_before_save()
		if not before:
			frappe.throw(_("A Subject / Course master cannot be created through Topic linking."), frappe.PermissionError)
		if any(doc.get(fieldname) != before.get(fieldname) for fieldname in COURSE_GOVERNANCE_FIELDS):
			frappe.throw(_("Topic linking cannot change Subject / Course identity or grading governance."), frappe.PermissionError)
		if _child_signature(doc.get("assessment_criteria")) != _child_signature(before.get("assessment_criteria")):
			frappe.throw(_("Topic linking cannot change Subject / Course assessment criteria."), frappe.PermissionError)
		return
	frappe.throw(
		_("Subject / Course masters and grading governance are controlled by authorised academic managers. Use the class-aware Curriculum workspace for assigned Topics and learning operations."),
		frappe.PermissionError,
	)


def _validate_topic_scope(doc, institution: str) -> tuple[str | None, str | None]:
	scope = doc.get(TOPIC_SCOPE_FIELD) or TOPIC_SCOPE_INSTITUTION
	if scope not in TOPIC_SCOPES:
		frappe.throw(_("Select a valid Topic Teaching Scope."), frappe.ValidationError)
	doc.set(TOPIC_SCOPE_FIELD, scope)
	if scope == TOPIC_SCOPE_INSTITUTION:
		doc.set(TOPIC_OFFERING_FIELD, None)
		doc.set(TOPIC_GROUP_FIELD, None)
		return None, None
	offering_name = doc.get(TOPIC_OFFERING_FIELD)
	if not offering_name:
		frappe.throw(_("Class / Programme Offering is required for a class-scoped Topic."), frappe.ValidationError)
	offering = frappe.db.get_value(
		"EduEdge Program Offering",
		offering_name,
		["name", "institution", "school_branch", "program", "is_active"],
		as_dict=True,
	)
	if not offering or not offering.is_active:
		frappe.throw(_("Select an active Class / Programme Offering."), frappe.ValidationError)
	if offering.institution != institution:
		frappe.throw(_("Topic, Subject / Course and Class must belong to the same Institution."), frappe.ValidationError)
	if not frappe.db.exists(
		"Program Course",
		{"parent": offering.program, "parenttype": "Program", "course": doc.get(TOPIC_COURSE_FIELD)},
	):
		frappe.throw(_("Subject / Course is not configured for the selected Class / Programme."), frappe.ValidationError)
	if scope == TOPIC_SCOPE_CLASS:
		doc.set(TOPIC_GROUP_FIELD, None)
		return offering.school_branch, None
	group_name = doc.get(TOPIC_GROUP_FIELD)
	if not group_name:
		frappe.throw(_("Class Arm / Student Group is required for a Class Arm Topic."), frappe.ValidationError)
	meta = frappe.get_meta("Student Group")
	fields = ["name", BRANCH_FIELD, "program", "disabled"]
	if meta.has_field(OFFERING_FIELD):
		fields.append(OFFERING_FIELD)
	group = frappe.db.get_value("Student Group", group_name, fields, as_dict=True)
	if not group or group.disabled:
		frappe.throw(_("Select an active Class Arm / Student Group."), frappe.ValidationError)
	if group.get(BRANCH_FIELD) != offering.school_branch or group.program != offering.program:
		frappe.throw(_("Class Arm / Student Group must belong to the selected Class / Programme Offering."), frappe.ValidationError)
	if meta.has_field(OFFERING_FIELD) and group.get(OFFERING_FIELD) and group.get(OFFERING_FIELD) != offering.name:
		frappe.throw(_("Class Arm / Student Group must belong to the selected Class / Programme Offering."), frappe.ValidationError)
	return offering.school_branch, group.name


def before_validate_topic(doc, method=None) -> None:
	course = doc.get(TOPIC_COURSE_FIELD)
	if not course:
		if is_teacher_user():
			frappe.throw(_("Owning Subject / Course is required for teacher-managed Topics."), frappe.ValidationError)
		return
	institution = frappe.db.get_value("Course", course, INSTITUTION_FIELD)
	if not institution:
		frappe.throw(_("The selected Subject / Course has no Institution context."), frappe.ValidationError)
	doc.set(INSTITUTION_FIELD, institution)
	branch, group = _validate_topic_scope(doc, institution)
	if is_teacher_user():
		if doc.get(TOPIC_SCOPE_FIELD) == TOPIC_SCOPE_INSTITUTION:
			frappe.throw(_("Assigned teachers cannot create or edit Institution-wide Topics."), frappe.PermissionError)
		require_course_assignment(
			course,
			branch=branch,
			program_offering=doc.get(TOPIC_OFFERING_FIELD),
			student_group=group,
		)
	before = doc.get_doc_before_save()
	if before and is_teacher_user():
		protected = (
			"topic_name",
			TOPIC_COURSE_FIELD,
			TOPIC_SCOPE_FIELD,
			TOPIC_OFFERING_FIELD,
			TOPIC_GROUP_FIELD,
		)
		if any(doc.get(fieldname) != before.get(fieldname) for fieldname in protected):
			frappe.throw(
				_("Assigned teachers cannot rename a saved Topic or move it to another Subject, Class, or Class Arm."),
				frappe.PermissionError,
			)
