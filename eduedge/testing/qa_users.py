from __future__ import annotations

import frappe
from frappe.permissions import add_permission, setup_custom_perms, update_permission_property
from frappe.utils import cint


DEFAULT_PASSWORD = "EduEdgeQA#2026"
CUSTOM_ROLE = "Subject Coordinator"
CURRICULUM_VIEWER_ROLE = "QA Curriculum Viewer"
QUESTION_DOCTYPE = "EduEdge CBT Question"
BRANCH_ACCESS_DOCTYPE = "EduEdge User Branch Access"
QUESTION_RIGHTS = {"read", "create", "write", "report", "print"}
QUESTION_SUPPORT_DOCTYPES = ("Course", "Topic")
CURRICULUM_VIEWER_RIGHTS = {
	"Program": {"read"},
	"Course": {"read"},
	"Department": {"read"},
	"EduEdge Institution": {"read"},
	"EduEdge Program Offering": {"read"},
	"EduEdge School Branch": {"read"},
}
MANAGED_PERMISSION_TYPES = {
	"read",
	"create",
	"write",
	"delete",
	"report",
	"import",
	"export",
	"print",
	"email",
	"share",
}

QA_USERS = (
	{
		"email": "qa.school.admin@example.com",
		"first_name": "QA School",
		"last_name": "Administrator",
		"roles": ("School Administrator",),
		"branch_role": "School Administrator",
	},
	{
		"email": "qa.academic.admin@example.com",
		"first_name": "QA Academic",
		"last_name": "Administrator",
		"roles": ("Academic Administrator",),
		"branch_role": "Academic Administrator",
	},
	{
		"email": "qa.teacher@example.com",
		"first_name": "QA",
		"last_name": "Teacher",
		"roles": ("Teacher",),
		"branch_role": "Teacher",
	},
	{
		"email": "qa.invigilator@example.com",
		"first_name": "QA CBT",
		"last_name": "Invigilator",
		"roles": ("CBT Invigilator",),
		"branch_role": "CBT Invigilator",
	},
	{
		"email": "qa.registrar@example.com",
		"first_name": "QA",
		"last_name": "Registrar",
		"roles": ("Registrar",),
		"branch_role": "Admissions Officer",
	},
	{
		"email": "qa.bursar@example.com",
		"first_name": "QA",
		"last_name": "Bursar",
		"roles": ("Bursar",),
		"branch_role": "Bursar",
	},
	{
		"email": "qa.subject.coordinator@example.com",
		"first_name": "QA Subject",
		"last_name": "Coordinator",
		"roles": (CUSTOM_ROLE,),
		"branch_role": "Other",
	},
	{
		"email": "qa.curriculum.viewer@example.com",
		"first_name": "QA Curriculum",
		"last_name": "Viewer",
		"roles": (CURRICULUM_VIEWER_ROLE,),
		"branch_role": "Other",
	},
)

BROWSER_QA_PHASES = (
	{
		"phase": "Programme/Class Curriculum Manager - manager positive paths",
		"user": "qa.academic.admin@example.com",
		"route": "/app/eduedge-programs",
	},
	{
		"phase": "Programme/Class Curriculum Manager - restricted-role negative paths",
		"user": "qa.curriculum.viewer@example.com",
		"route": "/app/eduedge-programs",
	},
	{
		"phase": "Instructor Assignment - manager planning/save",
		"user": "qa.academic.admin@example.com",
		"route": "/app/eduedge-instructor-assignments",
	},
	{
		"phase": "Instructor Assignment - instructor visibility",
		"user": "qa.teacher@example.com",
		"route": "/app/eduedge-instructor-assignments",
	},
	{
		"phase": "Question authoring - standard teacher",
		"user": "qa.teacher@example.com",
		"route": "/app/eduedge-question-builder",
	},
	{
		"phase": "Question authoring - delegated Subject Coordinator",
		"user": "qa.subject.coordinator@example.com",
		"route": "/app/eduedge-question-builder",
	},
	{
		"phase": "Question review/governance - school manager",
		"user": "qa.school.admin@example.com",
		"route": "/app/eduedge-question-bank",
	},
	{
		"phase": "CBT invigilation",
		"user": "qa.invigilator@example.com",
		"route": "/app/eduedge-cbt-invigilation",
	},
	{
		"phase": "Admissions and enrolment",
		"user": "qa.registrar@example.com",
		"route": "/app/eduedge-admissions",
	},
	{
		"phase": "Finance-context read-only regression",
		"user": "qa.bursar@example.com",
		"route": "/app/eduedge-home",
	},
)


def _assert_qa_site() -> None:
	if cint(frappe.conf.get("developer_mode")) or cint(frappe.conf.get("allow_tests")):
		return
	frappe.throw(
		"EduEdge QA users can be seeded only when developer_mode or allow_tests is enabled.",
		frappe.PermissionError,
	)


def _resolve_branch(branch: str | None = None) -> dict:
	fields = ["name", "branch_name", "company", "enabled"]
	if branch:
		row = frappe.db.get_value("EduEdge School Branch", branch, fields, as_dict=True)
		if not row:
			frappe.throw(f"EduEdge School Branch {branch} does not exist.", frappe.DoesNotExistError)
		if not row.enabled:
			frappe.throw(f"Enable EduEdge School Branch {branch} before seeding QA users.")
		return row

	branches = frappe.get_all(
		"EduEdge School Branch",
		filters={"enabled": 1},
		fields=fields,
		order_by="creation asc",
		page_length=2,
	)
	if not branches:
		frappe.throw("Create and enable an EduEdge School Branch before seeding QA users.")
	if len(branches) > 1:
		frappe.throw(
			"More than one enabled EduEdge School Branch exists. Pass branch explicitly to avoid assigning QA users to the wrong campus."
		)
	return branches[0]


def _set_exact_role_permissions(doctype: str, desired_rights: set[str], role: str = CUSTOM_ROLE) -> None:
	if not frappe.db.exists("DocType", doctype):
		frappe.throw(f"Required DocType {doctype} does not exist.", frappe.DoesNotExistError)

	setup_custom_perms(doctype)
	filters = {
		"parent": doctype,
		"role": role,
		"permlevel": 0,
		"if_owner": 0,
	}
	if not frappe.db.exists("Custom DocPerm", filters):
		initial = "read" if "read" in desired_rights else sorted(desired_rights)[0]
		add_permission(doctype, role, permlevel=0, ptype=initial)

	for permission_type in sorted(MANAGED_PERMISSION_TYPES):
		update_permission_property(
			doctype,
			role,
			0,
			permission_type,
			int(permission_type in desired_rights),
			validate=False,
		)
	frappe.clear_cache(doctype=doctype)


def _ensure_desk_role(role: str) -> None:
	if not frappe.db.exists("Role", role):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": role,
				"desk_access": 1,
			}
		).insert(ignore_permissions=True)
	else:
		frappe.db.set_value("Role", role, "desk_access", 1, update_modified=False)


def _ensure_subject_coordinator_role() -> None:
	_ensure_desk_role(CUSTOM_ROLE)
	_set_exact_role_permissions(QUESTION_DOCTYPE, QUESTION_RIGHTS, role=CUSTOM_ROLE)
	for doctype in QUESTION_SUPPORT_DOCTYPES:
		_set_exact_role_permissions(doctype, {"read"}, role=CUSTOM_ROLE)


def _ensure_curriculum_viewer_role() -> None:
	_ensure_desk_role(CURRICULUM_VIEWER_ROLE)
	for doctype, rights in CURRICULUM_VIEWER_RIGHTS.items():
		_set_exact_role_permissions(doctype, rights, role=CURRICULUM_VIEWER_ROLE)


def _ensure_required_roles(roles: tuple[str, ...]) -> None:
	missing = [role for role in roles if not frappe.db.exists("Role", role)]
	if missing:
		frappe.throw(f"Required role(s) are missing: {', '.join(missing)}")


def _ensure_user(spec: dict, password: str) -> str:
	email = spec["email"].strip().lower()
	is_new = not frappe.db.exists("User", email)
	if is_new:
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": spec["first_name"],
				"last_name": spec["last_name"],
				"enabled": 1,
				"user_type": "System User",
				"send_welcome_email": 0,
			}
		)
	else:
		user = frappe.get_doc("User", email)
		user.first_name = spec["first_name"]
		user.last_name = spec["last_name"]
		user.enabled = 1
		user.user_type = "System User"
		user.send_welcome_email = 0

	user.flags.no_welcome_mail = True
	user.set("roles", [])
	for role in spec["roles"]:
		user.append("roles", {"role": role})
	user.new_password = password

	if is_new:
		user.insert(ignore_permissions=True)
	else:
		user.save(ignore_permissions=True)
	return email


def _ensure_branch_access(user: str, branch: dict, branch_role: str) -> str:
	filters = {
		"user": user,
		"hq_all_branch_access": 0,
		"school_branch": branch.name,
	}
	name = frappe.db.exists(BRANCH_ACCESS_DOCTYPE, filters)
	if name:
		access = frappe.get_doc(BRANCH_ACCESS_DOCTYPE, name)
	else:
		access = frappe.new_doc(BRANCH_ACCESS_DOCTYPE)
		access.user = user
		access.hq_all_branch_access = 0
		access.school_branch = branch.name

	access.branch_role = branch_role
	access.company = branch.company
	access.is_default_branch = 1
	access.can_switch_branch = 0
	access.enabled = 1
	if name:
		access.save(ignore_permissions=True)
	else:
		access.insert(ignore_permissions=True)
	return access.name


def seed(branch: str | None = None, password: str = DEFAULT_PASSWORD) -> dict:
	"""Create or refresh reusable EduEdge QA users on a development/test site.

	Run with bench execute. The function is intentionally not whitelisted and
	refuses to run unless developer_mode or allow_tests is enabled.
	"""
	_assert_qa_site()
	if not password or len(password) < 10:
		frappe.throw("Use a QA password with at least 10 characters.")

	resolved_branch = _resolve_branch(branch)
	_ensure_subject_coordinator_role()
	_ensure_curriculum_viewer_role()
	all_roles = tuple({role for spec in QA_USERS for role in spec["roles"]})
	_ensure_required_roles(all_roles)

	created_or_updated = []
	for spec in QA_USERS:
		email = _ensure_user(spec, password)
		access_name = _ensure_branch_access(email, resolved_branch, spec["branch_role"])
		created_or_updated.append(
			{
				"email": email,
				"full_name": f"{spec['first_name']} {spec['last_name']}",
				"roles": list(spec["roles"]),
				"branch_access": access_name,
			}
		)

	frappe.db.commit()
	return {
		"branch": resolved_branch.name,
		"branch_name": resolved_branch.branch_name,
		"company": resolved_branch.company,
		"password": password,
		"users": created_or_updated,
		"browser_qa_phases": list(BROWSER_QA_PHASES),
		"note": "Development/test users only. Disable or remove them before production use.",
	}


def readiness(branch: str | None = None) -> dict:
	"""Report whether the seeded browser-QA personas are ready on this test site."""
	_assert_qa_site()
	resolved_branch = _resolve_branch(branch)
	rows = []
	for spec in QA_USERS:
		email = spec["email"]
		exists = bool(frappe.db.exists("User", email))
		roles = set(frappe.get_roles(email)) if exists else set()
		access = frappe.db.exists(
			BRANCH_ACCESS_DOCTYPE,
			{
				"user": email,
				"school_branch": resolved_branch.name,
				"hq_all_branch_access": 0,
				"enabled": 1,
			},
		) if exists else None
		expected_roles = set(spec["roles"])
		rows.append(
			{
				"email": email,
				"ready": bool(exists and expected_roles.issubset(roles) and access),
				"expected_roles": sorted(expected_roles),
				"branch_access": access or "",
			}
		)
	return {
		"branch": resolved_branch.name,
		"ready": all(row["ready"] for row in rows),
		"users": rows,
		"browser_qa_phases": list(BROWSER_QA_PHASES),
	}
