from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.api import academic_operations_safe as safe
from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.instructor_scope import (
	is_limited_instructor_user,
	resolve_exact_instructor_for_user,
)
from eduedge.education.teaching_assignments import (
	CLASS_ARM_SCOPE,
	CLASS_SCOPE,
	COURSE_REQUIRED_TYPES,
)
from eduedge.services.academic_calendar import resolve_academic_defaults
from eduedge.services.instructor_branch_governance import eligibility_covers_period


@frappe.whitelist()
def get_operations_context(branch: str | None = None, date: str | None = None, student_group: str | None = None) -> dict:
	payload = safe.get_operations_context(branch=branch, date=date, student_group=student_group)
	calendar = payload.get("academic_calendar") or {}
	selected_branch = payload.get("selected_branch") or {}
	institution = selected_branch.get("institution")
	if institution and calendar.get("source") != "institution_calendar":
		payload["student_groups"] = []
		payload.setdefault("counts", {})["student_groups"] = 0
		payload.setdefault("filters", {})["student_group"] = None
		payload["academic_calendar"] = {
			**calendar,
			"ready": False,
			"blocking_issue": _("No enabled Institution Academic Calendar covers the selected date. Configure the Academic Session and its Terms before creating or selecting a Class Arm / Level."),
		}
	elif institution and not calendar.get("academic_term"):
		payload["student_groups"] = []
		payload.setdefault("counts", {})["student_groups"] = 0
		payload.setdefault("filters", {})["student_group"] = None
		payload["academic_calendar"] = {
			**calendar,
			"ready": False,
			"blocking_issue": _("The selected date is inside the Academic Session but outside every configured Term / Semester."),
		}
	else:
		payload["academic_calendar"] = {**calendar, "ready": bool(calendar.get("academic_year"))}
	_annotate_group_hierarchy(payload.get("student_groups") or [])
	return payload


def _annotate_group_hierarchy(groups: list[dict]) -> None:
	if not groups:
		return
	names = [row.get("name") for row in groups if row.get("name")]
	rows = frappe.get_all(
		"Student Group",
		filters={"name": ["in", names]},
		fields=["name", "student_group_name", "program", "course", "group_based_on", "academic_year", "academic_term", "batch", BRANCH_FIELD],
		page_length=len(names),
	)
	program_names = list({row.program for row in rows if row.program})
	programmes = {
		row.name: row
		for row in frappe.get_all("Program", filters={"name": ["in", program_names]}, fields=["name", "program_name", "department"], page_length=max(len(program_names), 1))
	} if program_names else {}
	by_name = {row.name: row for row in rows}
	for group in groups:
		row = by_name.get(group.get("name"))
		if not row:
			continue
		programme = programmes.get(row.program)
		group["program"] = row.program or ""
		group["program_name"] = (programme or {}).get("program_name") or row.program or ""
		group["department"] = (programme or {}).get("department") or ""
		group["course"] = row.course or ""
		group["group_based_on"] = row.group_based_on or ""
		group["academic_year"] = row.academic_year or ""
		group["academic_term"] = row.academic_term or ""
		group["batch"] = row.batch or ""
		group["hierarchy_label"] = " → ".join(value for value in (group["department"], group["program_name"], row.student_group_name or row.name) if value)


def _limited_schedule_student_group_rows(
	*,
	branch: str,
	reference_date,
	academic_year: str | None,
	academic_term: str | None,
	program: str | None,
	txt: str,
	start: int,
	page_len: int,
) -> list[dict]:
	"""Expose only classes the current limited Instructor can actually schedule.

	This deliberately does not relax the normal Student Group permission query.
	It only breaks the first-schedule bootstrap cycle on the Course Schedule Link
	selector by using exact teaching responsibility as the source of truth.
	"""
	exact_instructor = resolve_exact_instructor_for_user()
	if not exact_instructor:
		return []
	if not eligibility_covers_period(
		exact_instructor,
		branch,
		reference_date,
		reference_date,
	):
		return []

	params = {
		"branch": branch,
		"exact_instructor": exact_instructor,
		"reference_date": getdate(reference_date),
		"academic_year": academic_year or "",
		"academic_term": academic_term or "",
		"program": program or "",
		"txt": f"%{txt or ''}%",
		"start": int(start),
		"page_len": int(page_len),
		"class_scope": CLASS_SCOPE,
		"arm_scope": CLASS_ARM_SCOPE,
		"assignment_types": tuple(sorted(COURSE_REQUIRED_TYPES)),
	}
	conditions = [
		f"group_row.`{BRANCH_FIELD}` = %(branch)s",
		"group_row.disabled = 0",
	]
	if academic_year:
		conditions.append("group_row.academic_year = %(academic_year)s")
	if academic_term:
		conditions.append(
			"(coalesce(group_row.academic_term, '') = '' or group_row.academic_term = %(academic_term)s)"
		)
	if program:
		conditions.append("group_row.program = %(program)s")
	conditions.append(
		"""(
			group_row.name like %(txt)s
			or coalesce(group_row.student_group_name, '') like %(txt)s
			or coalesce(group_row.program, '') like %(txt)s
			or coalesce(group_row.course, '') like %(txt)s
		)"""
	)

	assignment_mode = (
		frappe.db.exists("DocType", "EduEdge Instructor Assignment")
		and frappe.db.exists(
			"EduEdge Instructor Assignment",
			{"school_branch": branch},
		)
	)
	if assignment_mode:
		if not frappe.get_meta("Student Group").has_field(OFFERING_FIELD):
			return []
		conditions.append(
			f"""
			exists (
				select 1
				from `tabEduEdge Instructor Assignment` assignment
				where assignment.instructor = %(exact_instructor)s
					and assignment.school_branch = %(branch)s
					and assignment.program_offering = group_row.`{OFFERING_FIELD}`
					and assignment.assignment_type in %(assignment_types)s
					and assignment.enabled = 1
					and (
						assignment.assignment_scope = %(class_scope)s
						or (
							assignment.assignment_scope = %(arm_scope)s
							and assignment.student_group = group_row.name
						)
					)
					and (
						assignment.valid_from is null
						or assignment.valid_from <= %(reference_date)s
					)
					and (
						assignment.valid_to is null
						or assignment.valid_to >= %(reference_date)s
					)
			)
			"""
		)

	return frappe.db.sql(
		f"""
		select
			group_row.name,
			group_row.student_group_name,
			group_row.program,
			group_row.course,
			group_row.academic_year,
			group_row.academic_term
		from `tabStudent Group` group_row
		where {" and ".join(conditions)}
		order by group_row.student_group_name asc
		limit %(start)s, %(page_len)s
		""",
		params,
		as_dict=True,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def student_group_query(doctype, txt, searchfield, start, page_len, filters):
	"""Return only Student Groups valid for the Branch and selected lesson date."""
	safe.base._require_academic_operator()
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	branch = safe.base._resolve_branch(filters.get(BRANCH_FIELD))
	reference_date = str(getdate(filters.get("reference_date") or nowdate()))
	calendar = resolve_academic_defaults(branch, reference_date)
	institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
	if institution and (calendar.get("source") != "institution_calendar" or not calendar.get("academic_year") or not calendar.get("academic_term")):
		return []
	group_filters: dict = {BRANCH_FIELD: branch, "disabled": 0}
	academic_year = filters.get("academic_year") or calendar.get("academic_year")
	academic_term = filters.get("academic_term") or calendar.get("academic_term")
	if academic_year:
		group_filters["academic_year"] = academic_year
	if filters.get("program"):
		group_filters["program"] = filters.get("program")
	if is_limited_instructor_user():
		rows = _limited_schedule_student_group_rows(
			branch=branch,
			reference_date=reference_date,
			academic_year=academic_year,
			academic_term=academic_term,
			program=filters.get("program"),
			txt=str(txt or ""),
			start=int(start),
			page_len=int(page_len),
		)
	else:
		rows = frappe.get_list(
			"Student Group",
			filters=group_filters,
			or_filters={"name": ["like", f"%{txt}%"], "student_group_name": ["like", f"%{txt}%"], "program": ["like", f"%{txt}%"], "course": ["like", f"%{txt}%"]},
			fields=["name", "student_group_name", "program", "course", "academic_year", "academic_term"],
			start=int(start),
			page_length=int(page_len),
			order_by="student_group_name asc",
		)
	if academic_term:
		rows = [row for row in rows if not row.academic_term or row.academic_term == academic_term]
	program_names = list({row.program for row in rows if row.program})
	programmes = {
		row.name: row
		for row in frappe.get_all("Program", filters={"name": ["in", program_names]}, fields=["name", "program_name", "department"], page_length=max(len(program_names), 1))
	} if program_names else {}
	return [
		[
			row.name,
			row.student_group_name,
			" → ".join(value for value in ((programmes.get(row.program) or {}).get("department"), (programmes.get(row.program) or {}).get("program_name") or row.program, row.course) if value),
			row.academic_term or row.academic_year or "",
		]
		for row in rows
	]


def _limited_schedule_course_names(
	*,
	branch: str,
	student_group: str,
	program: str,
	reference_date,
	program_course_names: list[str],
) -> list[str]:
	"""Return only Program subjects the limited Instructor may schedule for this class."""
	exact_instructor = resolve_exact_instructor_for_user()
	if not exact_instructor:
		return []
	if not eligibility_covers_period(
		exact_instructor,
		branch,
		reference_date,
		reference_date,
	):
		return []

	group = frappe.db.get_value(
		"Student Group",
		student_group,
		["name", BRANCH_FIELD, OFFERING_FIELD, "program", "disabled"],
		as_dict=True,
	)
	if (
		not group
		or group.disabled
		or group.get(BRANCH_FIELD) != branch
		or group.program != program
	):
		return []

	assignment_mode = (
		frappe.db.exists("DocType", "EduEdge Instructor Assignment")
		and frappe.db.exists(
			"EduEdge Instructor Assignment",
			{"school_branch": branch},
		)
	)
	if not assignment_mode:
		return program_course_names
	if not group.get(OFFERING_FIELD):
		return []

	rows = frappe.get_all(
		"EduEdge Instructor Assignment",
		filters={
			"instructor": exact_instructor,
			"school_branch": branch,
			"program_offering": group.get(OFFERING_FIELD),
			"course": ["in", program_course_names],
			"assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)],
			"enabled": 1,
		},
		fields=[
			"course",
			"assignment_scope",
			"student_group",
			"valid_from",
			"valid_to",
		],
		limit_page_length=0,
	)
	target_date = getdate(reference_date)
	allowed: list[str] = []
	for row in rows:
		scope = row.assignment_scope or CLASS_ARM_SCOPE
		if scope == CLASS_SCOPE:
			pass
		elif scope == CLASS_ARM_SCOPE and row.student_group == student_group:
			pass
		else:
			continue
		if row.valid_from and getdate(row.valid_from) > target_date:
			continue
		if row.valid_to and getdate(row.valid_to) < target_date:
			continue
		if row.course and row.course not in allowed:
			allowed.append(row.course)
	return allowed


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def course_query(doctype, txt, searchfield, start, page_len, filters):
	"""Return only Courses configured on the selected native Program."""
	safe.base._require_academic_operator()
	if not frappe.has_permission("Course", "read"):
		frappe.throw(_("You are not permitted to read Courses / Subjects."), frappe.PermissionError)
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	program = str(filters.get("program") or "").strip()
	branch = str(filters.get(BRANCH_FIELD) or "").strip()
	student_group = str(filters.get("student_group") or "").strip()
	reference_date = getdate(filters.get("reference_date") or nowdate())
	if not program or not branch:
		return []
	branch = safe.base._resolve_branch(branch)
	institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
	program_row = frappe.db.get_value("Program", program, ["department", INSTITUTION_FIELD], as_dict=True)
	if not program_row or program_row.get(INSTITUTION_FIELD) != institution:
		return []
	course_names = frappe.get_all(
		"Program Course",
		filters={"parent": program, "parenttype": "Program"},
		pluck="course",
		order_by="idx asc",
	)
	if not course_names:
		return []
	if is_limited_instructor_user():
		if not student_group:
			return []
		course_names = _limited_schedule_course_names(
			branch=branch,
			student_group=student_group,
			program=program,
			reference_date=reference_date,
			program_course_names=course_names,
		)
		if not course_names:
			return []
	course_filters = {"name": ["in", course_names]}
	course_meta = frappe.get_meta("Course")
	if course_meta.has_field(INSTITUTION_FIELD):
		course_filters[INSTITUTION_FIELD] = institution
	rows = frappe.get_list(
		"Course",
		filters=course_filters,
		or_filters={"name": ["like", f"%{txt}%"], "course_name": ["like", f"%{txt}%"], "course_code": ["like", f"%{txt}%"]},
		fields=["name", "course_name", "course_code"],
		start=int(start),
		page_length=int(page_len),
		order_by="course_name asc, name asc",
	)
	return [[row.name, row.course_name or row.name, row.course_code or "", program_row.department or ""] for row in rows]
