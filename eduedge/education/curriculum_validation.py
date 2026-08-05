from __future__ import annotations

import frappe
from frappe import _

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.curriculum_fields import TOPIC_COURSE_FIELD
from eduedge.education.curriculum_permissions import assigned_courses, is_teacher_user


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
	if is_teacher_user() and course not in assigned_courses():
		frappe.throw(_("You can manage Topics only for Courses / Subjects actively assigned to you."), frappe.PermissionError)
