from __future__ import annotations

from collections.abc import Iterable

import frappe
from frappe.permissions import get_valid_perms
from frappe.utils import cint


PERMISSION_TYPES = (
	"read",
	"create",
	"write",
	"delete",
	"report",
	"import",
	"export",
	"print",
)

# Resource keys are stable UI/API identifiers. DocType names remain the Frappe
# permission source of truth and can be changed through Role Permission Manager.
RESOURCE_DOCTYPES = {
	"institution": "EduEdge Institution",
	"company_operations_settings": "EduEdge Company Operations Settings",
	"school_branch": "EduEdge School Branch",
	"user_branch_access": "EduEdge User Branch Access",
	"instructor_branch_assignment": "EduEdge Instructor Branch Assignment",
	"question_responsibility_assignment": "EduEdge Question Responsibility Assignment",
	"student_admission": "Student Admission",
	"student_applicant": "Student Applicant",
	"student": "Student",
	"program": "Program",
	"course": "Course",
	"topic": "Topic",
	"academic_year": "Academic Year",
	"academic_term": "Academic Term",
	"program_offering": "EduEdge Program Offering",
	"student_group": "Student Group",
	"room": "Room",
	"course_schedule": "Course Schedule",
	"student_attendance": "Student Attendance",
	"assessment_plan": "Assessment Plan",
	"assessment_result": "Assessment Result",
	"result_publication": "EduEdge Result Publication",
	"report_card_review": "EduEdge Report Card Review",
	"examination_centre": "EduEdge Examination Centre",
	"cbt_question": "EduEdge CBT Question",
	"cbt_template": "EduEdge CBT Exam Template",
	"cbt_schedule": "EduEdge CBT Exam Schedule",
	"cbt_candidate_assignment": "EduEdge CBT Candidate Assignment",
	"cbt_intervention_log": "EduEdge CBT Intervention Log",
	"eduedge_settings": "EduEdge Settings",
	"training_course": "EduEdge Training Course",
	"training_progress": "EduEdge Training Progress",
}

# Each route is available when any listed resource/permission pair is allowed.
# Record-level branch and user permissions continue to filter the records shown.
# Operational pages intentionally require an operational right rather than a
# broad Read right, because their interfaces expose create/update actions.
ROUTE_REQUIREMENTS = {
	"/app/eduedge-home": (),
	"/app/eduedge-academic-operations": (
		("student_attendance", "create"),
		("student_attendance", "write"),
	),
	"/app/eduedge-admissions": (("student_admission", "read"),),
	"/app/eduedge-applicants": (("student_applicant", "read"),),
	"/app/eduedge-students": (("student", "read"),),
	"/app/eduedge-programs": (("program", "read"),),
	"/app/eduedge-program-offerings": (("program_offering", "read"),),
	"/app/eduedge-cbt-operations": (
		("examination_centre", "read"),
		("cbt_question", "read"),
		("cbt_template", "read"),
		("cbt_schedule", "read"),
	),
	"/app/eduedge-cbt-schedules": (
		("cbt_schedule", "read"),
		("cbt_candidate_assignment", "read"),
		("cbt_intervention_log", "read"),
	),
	"/app/eduedge-exam-templates": (("cbt_template", "read"),),
	"/app/eduedge-exam-template-builder": (
		("cbt_template", "read"),
		("cbt_template", "create"),
		("cbt_template", "write"),
	),
	"/app/eduedge-question-bank": (("cbt_question", "read"),),
	"/app/eduedge-question-responsibilities": (("question_responsibility_assignment", "read"),),
	"/app/eduedge-question-builder": (
		("cbt_question", "read"),
		("cbt_question", "create"),
		("cbt_question", "write"),
	),
	"/app/eduedge-question-batch": (("cbt_question", "create"),),
	"/app/eduedge-assessment-operations": (
		("assessment_plan", "create"),
		("assessment_plan", "write"),
		("assessment_result", "create"),
		("assessment_result", "write"),
	),
	"/app/eduedge-report-cards": (
		("result_publication", "read"),
		("report_card_review", "read"),
		("assessment_result", "read"),
	),
	"/app/eduedge-school-branches": (("school_branch", "read"),),
	"/app/eduedge-institution-operations-settings": (
		("institution", "read"),
		("company_operations_settings", "read"),
	),
	"/app/eduedge-branch-governance": (
		("user_branch_access", "read"),
		("instructor_branch_assignment", "read"),
		("school_branch", "write"),
	),
	"/app/eduedge-setup-center": (("eduedge_settings", "read"),),
	"/app/eduedge-settings-center": (("eduedge_settings", "read"),),
	"/app/eduedge-training-centre": (
		("training_course", "read"),
		("training_progress", "read"),
	),
}


def _doctype_exists(doctype: str) -> bool:
	try:
		return bool(frappe.db.exists("DocType", doctype))
	except Exception:
		return False


def user_has_role_permission(
	doctype: str,
	permission_type: str = "read",
	user: str | None = None,
) -> bool:
	"""Check effective role rows without invoking query/has_permission hooks.

	This helper is safe inside permission hooks and makes custom school roles
	participate in branch isolation as soon as Role Permission Manager grants them
	access to a branch-aware DocType.
	"""
	resolved_user = user or frappe.session.user
	if resolved_user == "Administrator":
		return True
	if not resolved_user or resolved_user == "Guest" or not _doctype_exists(doctype):
		return False
	roles = set(frappe.get_roles(resolved_user))
	for row in get_valid_perms(doctype):
		if row.role not in roles or cint(row.permlevel) != 0:
			continue
		if cint(row.get(permission_type)):
			return True
	return False


def _has_permission(doctype: str, permission_type: str, user: str) -> bool:
	if user == "Administrator":
		return True
	if not _doctype_exists(doctype):
		return False
	try:
		return bool(frappe.has_permission(doctype, permission_type, user=user))
	except (frappe.DoesNotExistError, frappe.PermissionError):
		return False


def _resource_permissions(doctype: str, user: str) -> dict[str, bool]:
	return {
		permission_type: _has_permission(doctype, permission_type, user)
		for permission_type in PERMISSION_TYPES
	}


def _route_allowed(
	requirements: Iterable[tuple[str, str]],
	resources: dict[str, dict[str, bool]],
) -> bool:
	requirements = tuple(requirements)
	if not requirements:
		return any(values.get("read") for values in resources.values())
	return any(resources.get(resource, {}).get(permission_type, False) for resource, permission_type in requirements)


def build_access_manifest(user: str | None = None) -> dict:
	resolved_user = user or frappe.session.user
	if not resolved_user or resolved_user == "Guest":
		return {"resources": {}, "routes": {}, "can_access_eduedge": False}

	resources = {
		key: _resource_permissions(doctype, resolved_user)
		for key, doctype in RESOURCE_DOCTYPES.items()
	}
	routes = {
		route: _route_allowed(requirements, resources)
		for route, requirements in ROUTE_REQUIREMENTS.items()
	}
	can_access_eduedge = any(routes.values())
	if not can_access_eduedge:
		routes["/app/eduedge-home"] = False

	return {
		"resources": resources,
		"routes": routes,
		"can_access_eduedge": can_access_eduedge,
	}


@frappe.whitelist()
def get_access_manifest() -> dict:
	return build_access_manifest(frappe.session.user)
