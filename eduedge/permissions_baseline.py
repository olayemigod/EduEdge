from __future__ import annotations

from collections import defaultdict

import frappe
from frappe.permissions import (
	add_permission,
	get_valid_perms,
	setup_custom_perms,
	update_permission_property,
)


VIEW = ("read", "report", "print")
VIEW_EXPORT = VIEW + ("export",)
OPERATE = VIEW + ("create", "write")
MANAGE = OPERATE + ("delete", "import", "email", "share", "export")
SELF_PROGRESS = ("read", "create", "write")
TRAINING_OVERSIGHT = SELF_PROGRESS + ("report", "export", "print")
AUDIT_PERMISSION_TYPES = (
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
)

PLATFORM_MANAGERS = (
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
)
SCHOOL_MANAGERS = (
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
)
ACADEMIC_OPERATORS = (
	"Academics User",
	"Teacher",
	"Instructor",
)
ADMISSION_OPERATORS = ("Registrar", "Admission Officer")
FINANCE_READERS = ("Bursar", "Accounts User", "Accounts Manager")

# These ERPNext roles keep their native ERPNext permissions. EduEdge does not
# grant them unrelated school-academic access merely because ERPNext is present.
NO_EDUEDGE_DEFAULT_GRANTS = (
	"HR User",
	"HR Manager",
	"Purchase User",
	"Purchase Manager",
	"Stock User",
	"Stock Manager",
	"Asset User",
	"Asset Manager",
	"Sales User",
	"Sales Manager",
	"Projects User",
	"Projects Manager",
)
PORTAL_ONLY_ROLES = ("Student", "Guardian", "EduEdge Parent")

EDUEDGE_DESK_ROLES = tuple(
	dict.fromkeys(
		PLATFORM_MANAGERS
		+ ("EduEdge Public Exam Administrator",)
		+ SCHOOL_MANAGERS
		+ ACADEMIC_OPERATORS
		+ ADMISSION_OPERATORS
		+ FINANCE_READERS
		+ (
			"CBT Invigilator",
			"Student Safety Officer",
			"School Operations Manager",
			"School HR Officer",
			"Procurement Officer",
		)
	)
)
STANDARD_EDUEDGE_PAGES = (
	"eduedge-home",
	"eduedge-my-profile",
	"eduedge-academic-foundation",
	"eduedge-academic-operations",
	"eduedge-admissions",
	"eduedge-applicants",
	"eduedge-students",
	"eduedge-programs",
	"eduedge-program-offerings",
	"eduedge-cbt-operations",
	"eduedge-cbt-schedules",
	"eduedge-cbt-invigilation",
	"eduedge-cbt-marking",
	"eduedge-cbt-review-workbench",
	"eduedge-exam-templates",
	"eduedge-exam-template-builder",
	"eduedge-question-bank",
	"eduedge-question-responsibilities",
	"eduedge-question-builder",
	"eduedge-question-batch",
	"eduedge-assessment-operations",
	"eduedge-report-cards",
	"eduedge-institution-profile",
	"eduedge-institution-structure",
	"eduedge-institution-operations-settings",
	"eduedge-school-branches",
	"eduedge-branch-governance",
	"eduedge-setup-center",
	"eduedge-settings-center",
	"eduedge-training-centre",
)


def get_eduedge_page_names() -> list[str]:
	"""Discover every installed EduEdge Page from one authoritative helper."""
	page_names = set(STANDARD_EDUEDGE_PAGES)
	if not frappe.db.exists("DocType", "Page"):
		return sorted(page_names)
	for filters in ({"module": "EduEdge"}, {"name": ["like", "eduedge-%"]}):
		try:
			page_names.update(
				frappe.get_all("Page", filters=filters, pluck="name", page_length=0)
			)
		except (frappe.PermissionError, frappe.DoesNotExistError):
			continue
	return sorted(name for name in page_names if name)


def _grant(matrix: dict, doctype: str, roles, rights) -> None:
	for role in roles:
		matrix[doctype][role].update(rights)


def get_default_permission_matrix() -> dict[str, dict[str, set[str]]]:
	matrix: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
	managers = PLATFORM_MANAGERS + SCHOOL_MANAGERS

	for doctype in (
		"Program",
		"Course",
		"Topic",
		"Academic Year",
		"Academic Term",
		"Assessment Group",
		"Room",
	):
		_grant(matrix, doctype, managers, MANAGE)
		_grant(matrix, doctype, ACADEMIC_OPERATORS + ADMISSION_OPERATORS + ("CBT Invigilator",), VIEW)

	for doctype in ("Student Admission", "Student Applicant"):
		_grant(matrix, doctype, managers + ADMISSION_OPERATORS, MANAGE)
		_grant(matrix, doctype, ("Academics User",), VIEW)

	_grant(matrix, "Student", managers + ADMISSION_OPERATORS, MANAGE)
	_grant(
		matrix,
		"Student",
		ACADEMIC_OPERATORS
		+ FINANCE_READERS
		+ ("CBT Invigilator", "Student Safety Officer", "School Operations Manager"),
		VIEW,
	)
	_grant(matrix, "Guardian", managers + ADMISSION_OPERATORS, MANAGE)
	_grant(matrix, "Guardian", ("Teacher", "Instructor", "Student Safety Officer"), VIEW)
	_grant(matrix, "Program Enrollment", managers + ADMISSION_OPERATORS, MANAGE)
	_grant(matrix, "Program Enrollment", ("Academics User",), OPERATE)
	_grant(matrix, "Program Enrollment", ("Teacher", "Instructor") + FINANCE_READERS, VIEW)

	for doctype in (
		"Student Group",
		"Course Schedule",
		"Student Attendance",
		"Assessment Plan",
		"Assessment Result",
	):
		_grant(matrix, doctype, managers, MANAGE)
		_grant(matrix, doctype, ACADEMIC_OPERATORS, OPERATE)
	_grant(matrix, "Student Group", ("CBT Invigilator", "Student Safety Officer"), VIEW)
	_grant(matrix, "Assessment Plan", ("CBT Invigilator",), VIEW)
	_grant(matrix, "Assessment Result", ("Bursar",), VIEW)

	_grant(matrix, "EduEdge School Branch", PLATFORM_MANAGERS + ("School Administrator",), MANAGE)
	_grant(
		matrix,
		"EduEdge School Branch",
		(
			"Academic Administrator",
			"Education Manager",
			"Academics User",
			"Teacher",
			"Instructor",
			"Registrar",
			"Admission Officer",
			"Bursar",
			"Accounts User",
			"Accounts Manager",
			"CBT Invigilator",
			"Student Safety Officer",
			"School Operations Manager",
		),
		VIEW,
	)
	_grant(matrix, "EduEdge User Branch Access", PLATFORM_MANAGERS + ("School Administrator",), MANAGE)
	_grant(matrix, "EduEdge User Branch Access", ("Academic Administrator",), VIEW)
	_grant(matrix, "EduEdge Instructor Branch Assignment", managers, MANAGE)
	_grant(matrix, "EduEdge Instructor Branch Assignment", ("Teacher", "Instructor"), VIEW)
	_grant(matrix, "EduEdge Program Offering", managers, MANAGE)
	_grant(matrix, "EduEdge Program Offering", ACADEMIC_OPERATORS + ADMISSION_OPERATORS, VIEW)
	_grant(matrix, "EduEdge Result Publication", managers, MANAGE)
	_grant(matrix, "EduEdge Result Publication", ACADEMIC_OPERATORS + ("Bursar",), VIEW)
	_grant(matrix, "EduEdge Report Card Review", managers, MANAGE)
	_grant(matrix, "EduEdge Report Card Review", ("Teacher", "Instructor"), OPERATE)
	_grant(matrix, "EduEdge Report Card Review", ("Academics User", "Bursar"), VIEW)
	_grant(matrix, "EduEdge Settings", PLATFORM_MANAGERS + ("School Administrator",), MANAGE)
	_grant(matrix, "EduEdge Settings", ("Academic Administrator", "Bursar"), VIEW)

	cbt_managers = managers + ("EduEdge Public Exam Administrator",)
	_grant(matrix, "EduEdge Examination Centre", cbt_managers, MANAGE)
	_grant(
		matrix,
		"EduEdge Examination Centre",
		("Academics User", "Teacher", "Instructor", "CBT Invigilator"),
		VIEW_EXPORT,
	)
	_grant(matrix, "EduEdge CBT Question", cbt_managers, MANAGE)
	_grant(matrix, "EduEdge CBT Question", ("Teacher", "Instructor"), OPERATE)
	_grant(matrix, "EduEdge CBT Question", ("Academics User",), VIEW)
	_grant(matrix, "EduEdge CBT Exam Template", cbt_managers, MANAGE)
	_grant(matrix, "EduEdge CBT Exam Template", ("Teacher", "Instructor"), OPERATE)
	_grant(matrix, "EduEdge CBT Exam Template", ("Academics User", "CBT Invigilator"), VIEW)

	# Every Desk user records only their own training progress by default. Report
	# is the explicit oversight capability for school/platform managers and the
	# School HR Officer. Delete is deliberately absent for audit integrity.
	_grant(matrix, "EduEdge Training Progress", EDUEDGE_DESK_ROLES, SELF_PROGRESS)
	_grant(
		matrix,
		"EduEdge Training Progress",
		managers + ("School HR Officer",),
		TRAINING_OVERSIGHT,
	)
	return matrix


def _ensure_permission_row(doctype: str, role: str, rights: set[str]) -> bool:
	if not frappe.db.exists("DocType", doctype) or not frappe.db.exists("Role", role):
		return False

	# Preserve all standard Frappe/ERPNext rows before adding EduEdge defaults.
	setup_custom_perms(doctype)
	filters = {
		"parent": doctype,
		"role": role,
		"permlevel": 0,
		"if_owner": 0,
	}
	row_exists = frappe.db.exists("Custom DocPerm", filters)
	if not row_exists:
		initial = "read" if "read" in rights else sorted(rights)[0]
		add_permission(doctype, role, permlevel=0, ptype=initial)

	changed = not bool(row_exists)
	for permission_type in sorted(rights):
		if frappe.db.get_value("Custom DocPerm", filters, permission_type):
			continue
		update_permission_property(
			doctype,
			role,
			0,
			permission_type,
			1,
			validate=False,
		)
		changed = True
	return changed


def apply_default_permission_baseline() -> dict:
	"""Seed defaults once; later Role Permission Manager choices remain authoritative."""
	changed_doctypes = set()
	for doctype, role_permissions in get_default_permission_matrix().items():
		for role, rights in role_permissions.items():
			if _ensure_permission_row(doctype, role, rights):
				changed_doctypes.add(doctype)
	for doctype in changed_doctypes:
		frappe.clear_cache(doctype=doctype)
	return {"changed_doctypes": sorted(changed_doctypes)}


def ensure_eduedge_page_role_baseline() -> dict:
	"""Remove duplicate Page role gates; menus, APIs and DocTypes govern access."""
	changed_pages = []
	for page_name in get_eduedge_page_names():
		if not frappe.db.exists("Page", page_name):
			continue
		count = frappe.db.count(
			"Has Role",
			{"parent": page_name, "parenttype": "Page", "parentfield": "roles"},
		)
		if not count:
			continue
		frappe.db.delete(
			"Has Role",
			{"parent": page_name, "parenttype": "Page", "parentfield": "roles"},
		)
		changed_pages.append(page_name)
	if changed_pages:
		frappe.clear_cache()
	return {"changed_pages": changed_pages}


def _role_classification(role: str, managed_roles: set[str]) -> str:
	if role in PORTAL_ONLY_ROLES:
		return "portal_only"
	if role in NO_EDUEDGE_DEFAULT_GRANTS:
		return "native_erpnext_no_eduedge_default"
	if role in managed_roles:
		return "eduedge_managed_default"
	return "custom_or_unclassified"


def _effective_role_rights(audited_doctypes: list[str]) -> dict[str, list[dict]]:
	rights_by_role: dict[str, list[dict]] = defaultdict(list)
	for doctype in audited_doctypes:
		for row in get_valid_perms(doctype):
			if int(row.permlevel or 0) != 0:
				continue
			rights = [permission for permission in AUDIT_PERMISSION_TYPES if int(row.get(permission) or 0)]
			if rights:
				rights_by_role[row.role].append({"doctype": doctype, "rights": rights})
	return rights_by_role


def _sensitive_permission_warnings(rights_by_role: dict[str, list[dict]]) -> list[dict]:
	warnings = []
	for role in PORTAL_ONLY_ROLES + NO_EDUEDGE_DEFAULT_GRANTS:
		for permission in rights_by_role.get(role, []):
			if permission["doctype"].startswith("EduEdge "):
				warnings.append(
					{
						"role": role,
						"doctype": permission["doctype"],
						"rights": permission["rights"],
						"reason": "Role should not receive automatic EduEdge Desk permissions.",
					}
				)
	for role, permissions in rights_by_role.items():
		for permission in permissions:
			if permission["doctype"] == "EduEdge Training Progress" and "delete" in permission["rights"]:
				warnings.append(
					{
						"role": role,
						"doctype": permission["doctype"],
						"rights": permission["rights"],
						"reason": "Training progress history must not be deletable.",
					}
				)
	return warnings


def get_role_permission_audit() -> dict:
	"""Audit every installed role against EduEdge and Frappe Education access."""
	matrix = get_default_permission_matrix()
	missing_doctypes = sorted(doctype for doctype in matrix if not frappe.db.exists("DocType", doctype))
	audited_doctypes = sorted(doctype for doctype in matrix if frappe.db.exists("DocType", doctype))
	missing_defaults = []
	for doctype in audited_doctypes:
		valid_rows = get_valid_perms(doctype)
		for role, expected in matrix[doctype].items():
			if not frappe.db.exists("Role", role):
				continue
			role_rows = [row for row in valid_rows if row.role == role and int(row.permlevel or 0) == 0]
			actual = {
				permission_type
				for permission_type in expected
				if any(int(row.get(permission_type) or 0) for row in role_rows)
			}
			missing = sorted(set(expected) - actual)
			if missing:
				missing_defaults.append({"doctype": doctype, "role": role, "missing": missing})

	rights_by_role = _effective_role_rights(audited_doctypes)
	managed_roles = {
		role
		for role_permissions in matrix.values()
		for role in role_permissions
	}
	installed_roles = frappe.get_all(
		"Role",
		fields=["name", "desk_access", "disabled"],
		order_by="name asc",
		page_length=0,
	)
	roles = []
	unclassified_desk_roles = []
	portal_roles_with_desk_access = []
	for row in installed_roles:
		classification = _role_classification(row.name, managed_roles)
		role_payload = {
			"role": row.name,
			"desk_access": bool(row.desk_access),
			"disabled": bool(row.disabled),
			"classification": classification,
			"audited_permissions": rights_by_role.get(row.name, []),
		}
		roles.append(role_payload)
		if classification == "custom_or_unclassified" and row.desk_access and not row.disabled:
			unclassified_desk_roles.append(row.name)
		if classification == "portal_only" and row.desk_access and not row.disabled:
			portal_roles_with_desk_access.append(row.name)

	page_names = get_eduedge_page_names()
	remaining_page_role_gates = frappe.get_all(
		"Has Role",
		filters={
			"parent": ["in", page_names],
			"parenttype": "Page",
			"parentfield": "roles",
		},
		fields=["parent", "role"],
		order_by="parent asc, role asc",
		page_length=0,
	)
	return {
		"audited_doctypes": audited_doctypes,
		"audited_pages": page_names,
		"missing_doctypes": missing_doctypes,
		"missing_defaults": missing_defaults,
		"sensitive_permission_warnings": _sensitive_permission_warnings(rights_by_role),
		"roles": roles,
		"unclassified_desk_roles": unclassified_desk_roles,
		"portal_roles_with_desk_access": portal_roles_with_desk_access,
		"remaining_page_role_gates": remaining_page_role_gates,
		"no_eduedge_default_grants": list(NO_EDUEDGE_DEFAULT_GRANTS),
		"portal_only_roles": list(PORTAL_ONLY_ROLES),
	}
