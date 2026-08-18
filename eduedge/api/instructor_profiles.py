from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.instructor_scope import (
	get_instructor_identity_state,
	get_instructor_identity_states,
)
from eduedge.education.people_fields import INSTRUCTOR_PRIMARY_BRANCH_FIELD
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import (
	get_allowed_institutions,
	get_allowed_school_branches,
	get_current_school_branch,
)

MAX_PAGE_LENGTH = 50
MAX_EMPLOYEE_OPTIONS = 250
ALL_INSTITUTIONS_KEY = "__all__"
GLOBAL_INSTRUCTOR_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
}
INSTRUCTOR_FIELDS = (
	"instructor_name",
	"employee",
	"gender",
	"status",
	"department",
	INSTITUTION_FIELD,
	INSTRUCTOR_PRIMARY_BRANCH_FIELD,
	"eduedge_email",
	"eduedge_mobile",
	"eduedge_qualification",
	"eduedge_specialisation",
	"eduedge_employment_type",
)


def _require_login() -> None:
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_permission(permission_type: str) -> None:
	_require_login()
	if not frappe.has_permission("Instructor", permission_type):
		frappe.throw(
			_("You are not permitted to {0} Instructor records.").format(permission_type),
			frappe.PermissionError,
		)


def _parse_payload(payload: str | dict | None) -> dict:
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	if not isinstance(payload, dict):
		frappe.throw(_("A valid Instructor payload is required."), frappe.ValidationError)
	return payload


def _is_global_instructor_admin() -> bool:
	return frappe.session.user == "Administrator" or bool(
		GLOBAL_INSTRUCTOR_ROLES.intersection(frappe.get_roles())
	)


def _row_fields(doctype: str, desired: list[str]) -> list[str]:
	meta = frappe.get_meta(doctype)
	return [fieldname for fieldname in desired if fieldname == "name" or meta.has_field(fieldname)]


def _allowed_institutions() -> list[dict]:
	rows = get_allowed_institutions() or []
	result = []
	for source in rows:
		row = dict(source)
		name = str(row.get("name") or "").strip()
		if not name:
			continue
		if not row.get("institution_name"):
			details = frappe.db.get_value(
				"EduEdge Institution",
				name,
				["institution_name", "institution_type", "company", "enabled"],
				as_dict=True,
			) or {}
			row.update(details)
		if not cint(row.get("enabled", 1)):
			continue
		result.append(row)
	return result


def _allowed_branches() -> list[dict]:
	rows = get_allowed_school_branches() or []
	result = []
	for source in rows:
		row = dict(source)
		name = str(row.get("name") or "").strip()
		if not name:
			continue
		if not row.get("branch_name") or not row.get("institution"):
			details = frappe.db.get_value(
				"EduEdge School Branch",
				name,
				["branch_name", "branch_code", "institution", "company", "enabled"],
				as_dict=True,
			) or {}
			row.update(details)
		if not cint(row.get("enabled", 1)):
			continue
		if row.get("institution") and not row.get("institution_name"):
			row["institution_name"] = frappe.db.get_value(
				"EduEdge Institution", row["institution"], "institution_name"
			)
		result.append(row)
	return result


def _resolve_filters(institution: str | None, branch: str | None) -> tuple[str, str, list[dict], list[dict]]:
	institutions = _allowed_institutions()
	branches = _allowed_branches()
	institution_names = {row["name"] for row in institutions}
	branch_map = {row["name"]: row for row in branches}
	global_view = _is_global_instructor_admin()
	resolved_institution = str(institution or "").strip()
	resolved_branch = str(branch or "").strip()

	if resolved_institution == ALL_INSTITUTIONS_KEY and not global_view:
		frappe.throw(_("Only EduEdge administrators can use the All Institutions Instructor view."), frappe.PermissionError)
	if resolved_institution and resolved_institution != ALL_INSTITUTIONS_KEY and resolved_institution not in institution_names:
		frappe.throw(_("The selected Institution is not available to your user."), frappe.PermissionError)
	if resolved_branch:
		if resolved_branch not in branch_map:
			frappe.throw(_("The selected Branch is not available to your user."), frappe.PermissionError)
		branch_institution = branch_map[resolved_branch].get("institution")
		if resolved_institution not in {"", ALL_INSTITUTIONS_KEY, branch_institution}:
			frappe.throw(_("The selected Branch does not belong to the selected Institution."), frappe.ValidationError)
		resolved_institution = branch_institution or resolved_institution

	if not resolved_institution:
		current = get_current_school_branch() or {}
		current_institution = str(current.get("institution") or "").strip()
		if global_view:
			resolved_institution = ALL_INSTITUTIONS_KEY
		elif current_institution in institution_names:
			resolved_institution = current_institution
		elif len(institutions) == 1:
			resolved_institution = institutions[0]["name"]
		else:
			resolved_institution = institutions[0]["name"] if institutions else ""

	return resolved_institution, resolved_branch, institutions, branches


def _operational_instructor_names(institution: str, branch: str, branches: list[dict]) -> set[str] | None:
	if institution == ALL_INSTITUTIONS_KEY and not branch:
		return None
	eligible_branches = [
		row["name"]
		for row in branches
		if (not institution or row.get("institution") == institution)
		and (not branch or row["name"] == branch)
	]
	branch_assignment_names = set(
		frappe.get_list(
			"EduEdge Instructor Branch Assignment",
			filters={"school_branch": ["in", eligible_branches]},
			pluck="instructor",
			limit_page_length=0,
		)
	) if eligible_branches and frappe.db.exists("DocType", "EduEdge Instructor Branch Assignment") else set()
	academic_assignment_names = set(
		frappe.get_list(
			"EduEdge Instructor Assignment",
			filters={"school_branch": ["in", eligible_branches]},
			pluck="instructor",
			limit_page_length=0,
		)
	) if eligible_branches and frappe.db.exists("DocType", "EduEdge Instructor Assignment") else set()

	filters: dict[str, Any] = {}
	meta = frappe.get_meta("Instructor")
	if branch and meta.has_field(INSTRUCTOR_PRIMARY_BRANCH_FIELD):
		filters[INSTRUCTOR_PRIMARY_BRANCH_FIELD] = branch
	elif institution and institution != ALL_INSTITUTIONS_KEY and meta.has_field(INSTITUTION_FIELD):
		filters[INSTITUTION_FIELD] = institution
	home_names = set(
		frappe.get_list("Instructor", filters=filters, pluck="name", limit_page_length=0)
	) if filters else set()
	return branch_assignment_names | academic_assignment_names | home_names


def _earliest(values: list) -> Any:
	available = [value for value in values if value]
	return min(available, key=getdate) if available else None


def _latest(values: list) -> Any:
	available = [value for value in values if value]
	return max(available, key=getdate) if available else None


def _summarise_branch_eligibility(rows: list[dict]) -> list[dict]:
	"""Return one profile card per Branch while retaining the underlying periods."""
	grouped: dict[str, list[dict]] = {}
	for source in rows:
		row = dict(source)
		branch = str(row.get("school_branch") or "").strip()
		if branch:
			grouped.setdefault(branch, []).append(row)

	result: list[dict] = []
	for branch, periods in grouped.items():
		active_periods = [row for row in periods if cint(row.get("enabled"))]
		visible_periods = active_periods or periods
		primary = next((row for row in active_periods if cint(row.get("is_primary"))), None)
		identity = primary or visible_periods[0]
		open_ended = any(not row.get("valid_to") for row in visible_periods)
		result.append(
			{
				"name": identity.get("name"),
				"school_branch": branch,
				"is_primary": 1 if primary else 0,
				"enabled": 1 if active_periods else 0,
				"valid_from": _earliest([row.get("valid_from") for row in visible_periods]),
				"valid_to": None if open_ended else _latest([row.get("valid_to") for row in visible_periods]),
				"period_count": len(periods),
				"periods": periods,
			}
		)
	return sorted(
		result,
		key=lambda row: (
			0 if cint(row.get("is_primary")) else 1,
			str(row.get("school_branch") or "").lower(),
		),
	)


def _instructor_detail(name: str) -> dict:
	doc = frappe.get_doc("Instructor", name)
	doc.check_permission("read")
	result = doc.as_dict(no_nulls=False)
	result["identity"] = get_instructor_identity_state(doc.name)
	result["assignments"] = frappe.get_list(
		"EduEdge Instructor Assignment",
		filters={"instructor": doc.name},
		fields=[
			"name", "assignment_title", "institution", "school_branch", "program_offering",
			"student_group", "course", "assignment_type", "assignment_scope", "enabled",
		],
		order_by="modified desc",
		limit_page_length=100,
	) if frappe.db.exists("DocType", "EduEdge Instructor Assignment") else []
	periods = frappe.get_list(
		"EduEdge Instructor Branch Assignment",
		filters={"instructor": doc.name},
		fields=["name", "school_branch", "is_primary", "enabled", "valid_from", "valid_to"],
		order_by="is_primary desc, school_branch asc, valid_from asc",
		limit_page_length=500,
	) if frappe.db.exists("DocType", "EduEdge Instructor Branch Assignment") else []
	result["branch_eligibility_periods"] = periods
	result["branch_eligibility"] = _summarise_branch_eligibility(periods)
	return result


def _departments(institution: str) -> list[dict]:
	if not institution or institution == ALL_INSTITUTIONS_KEY or not frappe.has_permission("Department", "read"):
		return []
	filters = {INSTITUTION_FIELD: institution} if frappe.get_meta("Department").has_field(INSTITUTION_FIELD) else {}
	return frappe.get_list(
		"Department",
		filters=filters,
		fields=["name", "department_name"],
		order_by="department_name asc",
		limit_page_length=500,
	)


def _employee_options(institution: str) -> list[dict]:
	"""Return only active Employees relevant to the selected Home Institution.

	Employee is a dependent field of Home Institution. Do not expose/load the entire
	Employee table into the Instructor page. Global administrators select a Home
	Institution first; the UI then reloads this bounded, company-scoped option set.
	"""
	if (
		not institution
		or institution == ALL_INSTITUTIONS_KEY
		or not frappe.db.exists("DocType", "Employee")
		or not frappe.has_permission("Employee", "read")
	):
		return []
	company = frappe.db.get_value("EduEdge Institution", institution, "company")
	if not company:
		return []
	return frappe.get_list(
		"Employee",
		filters={"status": "Active", "company": company},
		fields=["name", "employee_name", "department", "gender", "user_id", "status", "company"],
		order_by="employee_name asc",
		limit_page_length=MAX_EMPLOYEE_OPTIONS,
	)


@frappe.whitelist()
def get_instructors_page(
	institution: str | None = None,
	branch: str | None = None,
	search: str | None = None,
	instructor: str | None = None,
	start: int = 0,
	page_length: int = 25,
) -> dict:
	_require_permission("read")
	resolved_institution, resolved_branch, institutions, branches = _resolve_filters(institution, branch)
	operational_names = _operational_instructor_names(resolved_institution, resolved_branch, branches)
	filters: dict[str, Any] = {}
	if operational_names is not None:
		filters["name"] = ["in", sorted(operational_names)] if operational_names else ["in", ["__none__"]]
	or_filters = None
	if str(search or "").strip():
		needle = f"%{str(search).strip()}%"
		or_filters = {
			"name": ["like", needle],
			"instructor_name": ["like", needle],
			"eduedge_email": ["like", needle],
			"eduedge_mobile": ["like", needle],
		}
	length = min(max(cint(page_length), 1), MAX_PAGE_LENGTH)
	start = max(cint(start), 0)
	rows = frappe.get_list(
		"Instructor",
		filters=filters,
		or_filters=or_filters,
		fields=_row_fields(
			"Instructor",
			[
				"name", "instructor_name", "employee", "department", "status", "image",
				INSTITUTION_FIELD, INSTRUCTOR_PRIMARY_BRANCH_FIELD, "eduedge_email", "eduedge_mobile",
			],
		),
		order_by="instructor_name asc",
		start=start,
		page_length=length + 1,
	)
	has_more = len(rows) > length
	rows = rows[:length]
	institution_map = {row["name"]: row for row in institutions}
	branch_map = {row["name"]: row for row in branches}
	identity_map = get_instructor_identity_states([row.name for row in rows])
	for row in rows:
		home = institution_map.get(row.get(INSTITUTION_FIELD)) or {}
		primary = branch_map.get(row.get(INSTRUCTOR_PRIMARY_BRANCH_FIELD)) or {}
		row["institution_name"] = home.get("institution_name") or row.get(INSTITUTION_FIELD)
		row["primary_branch_name"] = primary.get("branch_name") or row.get(INSTRUCTOR_PRIMARY_BRANCH_FIELD)
		row["identity"] = identity_map.get(row.name, {})

	selected_institution = institution_map.get(resolved_institution) or {}
	selected_branch = branch_map.get(resolved_branch) or {}
	return {
		"all_institutions_key": ALL_INSTITUTIONS_KEY,
		"can_view_all_institutions": _is_global_instructor_admin(),
		"allowed_institutions": institutions,
		"allowed_branches": branches,
		"selected_institution": selected_institution,
		"selected_institution_name": "All Institutions" if resolved_institution == ALL_INSTITUTIONS_KEY else selected_institution.get("institution_name"),
		"selected_branch": selected_branch,
		"filters": {"institution": resolved_institution, "branch": resolved_branch},
		"instructors": rows,
		"instructor": _instructor_detail(instructor) if instructor else None,
		"departments": _departments(resolved_institution),
		"employees": _employee_options(resolved_institution),
		"genders": frappe.get_list("Gender", fields=["name"], order_by="name asc", limit_page_length=100),
		"permissions": {
			"can_create": frappe.has_permission("Instructor", "create"),
			"can_write": frappe.has_permission("Instructor", "write"),
		},
		"paging": {"start": start, "page_length": length, "has_more": has_more},
	}


def _covers_date(row, day) -> bool:
	return bool(
		cint(row.get("enabled"))
		and (not row.get("valid_from") or getdate(row.get("valid_from")) <= day)
		and (not row.get("valid_to") or getdate(row.get("valid_to")) >= day)
	)


def _ensure_branch_eligibility(instructor: str, branch: str) -> None:
	"""Make the selected Branch primary for *current* eligibility without rewriting history."""
	today = getdate(nowdate())
	periods = frappe.get_all(
		"EduEdge Instructor Branch Assignment",
		filters={"instructor": instructor},
		fields=["name", "school_branch", "enabled", "is_primary", "valid_from", "valid_to"],
		order_by="valid_from asc, modified asc",
		limit_page_length=0,
	)
	current_target = [row for row in periods if row.school_branch == branch and _covers_date(row, today)]
	if len(current_target) > 1:
		frappe.throw(
			_("More than one current Branch eligibility period exists for this Instructor and Branch. Resolve Branch eligibility before setting a Primary Branch."),
			frappe.ValidationError,
		)

	# Demote only another *currently effective* primary period. Historical and future
	# primary periods are not rewritten by saving the Instructor profile.
	for row in periods:
		if row.school_branch == branch or not cint(row.is_primary) or not _covers_date(row, today):
			continue
		other = frappe.get_doc("EduEdge Instructor Branch Assignment", row.name)
		other.check_permission("write")
		other.is_primary = 0
		other.save()

	if current_target:
		doc = frappe.get_doc("EduEdge Instructor Branch Assignment", current_target[0].name)
		doc.check_permission("write")
		if not cint(doc.is_primary):
			doc.is_primary = 1
			doc.save()
		return

	if not frappe.has_permission("EduEdge Instructor Branch Assignment", "create"):
		frappe.throw(_("You are not permitted to create Instructor Branch eligibility."), frappe.PermissionError)
	doc = frappe.new_doc("EduEdge Instructor Branch Assignment")
	doc.instructor = instructor
	doc.school_branch = branch
	doc.enabled = 1
	doc.is_primary = 1
	doc.valid_from = today
	doc.valid_to = None
	doc.save()


@frappe.whitelist(methods=["POST"])
def save_instructor(payload: str | dict) -> dict:
	require_eduedge_access(feature_key="academics", action="save_instructor")
	data = _parse_payload(payload)
	name = str(data.get("name") or "").strip()
	if name:
		doc = frappe.get_doc("Instructor", name)
		doc.check_permission("write")
	else:
		_require_permission("create")
		doc = frappe.new_doc("Instructor")
		doc.naming_series = data.get("naming_series") or "EDU-INS-.YYYY.-"

	institution = str(data.get(INSTITUTION_FIELD) or "").strip()
	if not institution:
		frappe.throw(_("Home Institution is required for the Instructor profile."), frappe.ValidationError)
	allowed_institutions = {row["name"] for row in _allowed_institutions()}
	if institution not in allowed_institutions:
		frappe.throw(_("The selected Home Institution is not available to your user."), frappe.PermissionError)

	branch = str(data.get(INSTRUCTOR_PRIMARY_BRANCH_FIELD) or "").strip()
	if branch:
		branch_row = next((row for row in _allowed_branches() if row["name"] == branch), None)
		if not branch_row:
			frappe.throw(_("The selected Primary Branch is not available to your user."), frappe.PermissionError)
		if branch_row.get("institution") != institution:
			frappe.throw(_("Primary Branch must belong to the Instructor's Home Institution."), frappe.ValidationError)

	department = str(data.get("department") or "").strip()
	if department and frappe.get_meta("Department").has_field(INSTITUTION_FIELD):
		department_institution = frappe.db.get_value("Department", department, INSTITUTION_FIELD)
		if department_institution and department_institution != institution:
			frappe.throw(_("Department / School Section must belong to the Instructor's Home Institution."), frappe.ValidationError)

	employee = str(data.get("employee") or "").strip()
	if employee:
		if not frappe.has_permission("Employee", "read"):
			frappe.throw(_("You are not permitted to link Employee records."), frappe.PermissionError)
		company = frappe.db.get_value("EduEdge Institution", institution, "company")
		employee_row = frappe.db.get_value("Employee", employee, ["status", "company"], as_dict=True)
		if not employee_row or employee_row.status != "Active":
			frappe.throw(_("Select an active Employee."), frappe.ValidationError)
		if company and employee_row.company != company:
			frappe.throw(_("Linked Employee must belong to the Home Institution's Company."), frappe.ValidationError)

	for fieldname in INSTRUCTOR_FIELDS:
		if doc.meta.has_field(fieldname) and fieldname in data:
			doc.set(fieldname, data.get(fieldname))
	if doc.meta.has_field(INSTITUTION_FIELD):
		doc.set(INSTITUTION_FIELD, institution)
	if doc.meta.has_field(INSTRUCTOR_PRIMARY_BRANCH_FIELD):
		doc.set(INSTRUCTOR_PRIMARY_BRANCH_FIELD, branch or None)
	if not doc.instructor_name:
		frappe.throw(_("Instructor Name is required."), frappe.ValidationError)
	doc.save()
	if branch:
		_ensure_branch_eligibility(doc.name, branch)
	return _instructor_detail(doc.name)