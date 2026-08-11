from __future__ import annotations

import frappe

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.services.branch_context import get_allowed_institutions, is_branch_access_enforced

PRIVILEGED_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
}
DIRECT_INSTITUTION_DOCTYPES = {
	"EduEdge Academic Section",
	"EduEdge Academic Level",
	"EduEdge Institution Academic Calendar",
}
LEGACY_OPTIONAL_DOCTYPES = {
	"Department",
	"Program",
	"Course",
	"Student Batch Name",
	"Student House",
	"Instructor",
	"Assessment Group",
	"Grading Scale",
	"Fee Structure",
}


def academic_section_query(user: str | None = None) -> str:
	return _institution_query("EduEdge Academic Section", "institution", user)


def academic_level_query(user: str | None = None) -> str:
	return _institution_query("EduEdge Academic Level", "institution", user)


def academic_calendar_query(user: str | None = None) -> str:
	return _institution_query("EduEdge Institution Academic Calendar", "institution", user)


def department_query(user: str | None = None) -> str:
	return _institution_query("Department", INSTITUTION_FIELD, user)


def program_query(user: str | None = None) -> str:
	return _institution_query("Program", INSTITUTION_FIELD, user)


def course_query(user: str | None = None) -> str:
	return _institution_query("Course", INSTITUTION_FIELD, user)


def student_batch_query(user: str | None = None) -> str:
	return _institution_query("Student Batch Name", INSTITUTION_FIELD, user)


def student_house_query(user: str | None = None) -> str:
	return _institution_query("Student House", INSTITUTION_FIELD, user)


def instructor_query(user: str | None = None) -> str:
	"""Keep historical Instructor identities visible inside allowed Institutions.

	The central Institution resolver remains authoritative. Legacy Instructor masters
	with a blank Home Institution may still be visible when historical Branch or
	Academic Assignments place them inside one of those allowed Institutions.
	"""
	resolved_user = user or frappe.session.user
	if not _should_scope(resolved_user):
		return ""
	institutions = _allowed_institutions(resolved_user)
	if not institutions:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(institutions))
	conditions: list[str] = []
	meta = frappe.get_meta("Instructor")
	if meta.has_field(INSTITUTION_FIELD):
		conditions.append(f"`tabInstructor`.`{INSTITUTION_FIELD}` in ({values})")
	if frappe.db.exists("DocType", "EduEdge Instructor Branch Assignment"):
		conditions.append(
			"exists (select 1 from `tabEduEdge Instructor Branch Assignment` branch_assignment "
			"inner join `tabEduEdge School Branch` branch on branch.name = branch_assignment.school_branch "
			"where branch_assignment.instructor = `tabInstructor`.name "
			f"and branch.institution in ({values}))"
		)
	if frappe.db.exists("DocType", "EduEdge Instructor Assignment"):
		conditions.append(
			"exists (select 1 from `tabEduEdge Instructor Assignment` academic_assignment "
			"where academic_assignment.instructor = `tabInstructor`.name "
			f"and academic_assignment.institution in ({values}))"
		)
	return "(" + " OR ".join(conditions) + ")" if conditions else "1=0"


def assessment_group_query(user: str | None = None) -> str:
	return _institution_query("Assessment Group", INSTITUTION_FIELD, user)


def grading_scale_query(user: str | None = None) -> str:
	return _institution_query("Grading Scale", INSTITUTION_FIELD, user)


def fee_structure_query(user: str | None = None) -> str:
	return _institution_query("Fee Structure", INSTITUTION_FIELD, user)


def has_academic_institution_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	if doc and getattr(doc, "doctype", None) == "Instructor":
		return has_instructor_permission(doc, resolved_user, permission_type)
	if not doc or not _should_scope(resolved_user):
		return True
	meta = frappe.get_meta(doc.doctype)
	fieldname = "institution" if doc.doctype in DIRECT_INSTITUTION_DOCTYPES else INSTITUTION_FIELD
	if not meta.has_field(fieldname):
		return True
	institution = doc.get(fieldname)
	if not institution:
		# Blank legacy masters are visible only to privileged users. Restricted users
		# must not see unclassified records on a shared-hosted site.
		return False
	return institution in _allowed_institutions(resolved_user)


def has_instructor_permission(doc, user=None, permission_type=None) -> bool:
	"""Record-level Instructor permission with safe legacy-history fallback."""
	resolved_user = user or frappe.session.user
	if not _should_scope(resolved_user):
		return True
	if not doc or getattr(doc, "is_new", lambda: False)():
		return True
	institutions = _allowed_institutions(resolved_user)
	if not institutions:
		return False
	if doc.meta.has_field(INSTITUTION_FIELD) and doc.get(INSTITUTION_FIELD) in institutions:
		return True
	if frappe.db.exists("DocType", "EduEdge Instructor Assignment") and frappe.db.exists(
		"EduEdge Instructor Assignment",
		{"instructor": doc.name, "institution": ["in", sorted(institutions)]},
	):
		return True
	if frappe.db.exists("DocType", "EduEdge Instructor Branch Assignment"):
		institution_branches = frappe.get_all(
			"EduEdge School Branch",
			filters={"institution": ["in", sorted(institutions)]},
			pluck="name",
			limit_page_length=0,
		)
		if institution_branches and frappe.db.exists(
			"EduEdge Instructor Branch Assignment",
			{"instructor": doc.name, "school_branch": ["in", institution_branches]},
		):
			return True
	return False


def _institution_query(doctype: str, fieldname: str, user: str | None) -> str:
	resolved_user = user or frappe.session.user
	if not _should_scope(resolved_user):
		return ""
	if not frappe.db.exists("DocType", doctype) or not frappe.get_meta(doctype).has_field(fieldname):
		return ""
	institutions = _allowed_institutions(resolved_user)
	if not institutions:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(institutions))
	# Fail closed for restricted users. Privileged users bypass _should_scope and
	# remain able to classify legacy records with a blank Institution.
	return f"`tab{doctype}`.`{fieldname}` in ({values})"


def _allowed_institutions(user: str) -> set[str]:
	return {
		row.get("name")
		for row in get_allowed_institutions(user=user)
		if row.get("name")
	}


def _should_scope(user: str) -> bool:
	if not is_branch_access_enforced() or not user or user in {"Guest", "Administrator"}:
		return False
	roles = set(frappe.get_roles(user))
	return not bool(roles.intersection(PRIVILEGED_ROLES))
