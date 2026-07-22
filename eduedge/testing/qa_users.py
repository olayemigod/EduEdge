from __future__ import annotations

import frappe
from frappe.permissions import add_permission, setup_custom_perms, update_permission_property
from frappe.utils import cint


DEFAULT_PASSWORD = "EduEdgeQA#2026"
CUSTOM_ROLE = "Subject Coordinator"
QUESTION_DOCTYPE = "EduEdge CBT Question"
BRANCH_ACCESS_DOCTYPE = "EduEdge User Branch Access"

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


def _ensure_subject_coordinator_role() -> None:
	if not frappe.db.exists("Role", CUSTOM_ROLE):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": CUSTOM_ROLE,
				"desk_access": 1,
			}
		).insert(ignore_permissions=True)
	else:
		frappe.db.set_value("Role", CUSTOM_ROLE, "desk_access", 1, update_modified=False)

	setup_custom_perms(QUESTION_DOCTYPE)
	filters = {
		"parent": QUESTION_DOCTYPE,
		"role": CUSTOM_ROLE,
		"permlevel": 0,
		"if_owner": 0,
	}
	if not frappe.db.exists("Custom DocPerm", filters):
		add_permission(QUESTION_DOCTYPE, CUSTOM_ROLE, permlevel=0, ptype="read")

	desired_rights = {"read", "create", "write", "report", "print"}
	managed_rights = {
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
	for permission_type in sorted(managed_rights):
		update_permission_property(
			QUESTION_DOCTYPE,
			CUSTOM_ROLE,
			0,
			permission_type,
			int(permission_type in desired_rights),
			validate=False,
		)
	frappe.clear_cache(doctype=QUESTION_DOCTYPE)


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
		"note": "Development/test users only. Disable or remove them before production use.",
	}
