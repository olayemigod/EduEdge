from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate

from eduedge.api.academic_operations import (
	_require_academic_operator,
	instructor_query as legacy_branch_instructor_query,
	student_group_query as legacy_student_group_query,
)
from eduedge.api.fuzzy_search import CANDIDATE_LIMIT, query_anchors, rank_link_rows
from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.instructor_assignments import _group_offering
from eduedge.education.instructor_scope import (
	is_limited_instructor_user,
	resolve_exact_instructor_for_user,
)
from eduedge.education.offerings import assert_branch_access
from eduedge.education.teaching_assignments import (
	CLASS_ARM_SCOPE,
	CLASS_SCOPE,
	COURSE_REQUIRED_TYPES,
)
from eduedge.services.instructor_branch_governance import eligibility_covers_period

ASSIGNMENT_DOCTYPE = "EduEdge Instructor Assignment"


def _eligible_instructor_rows(params: dict, query: str) -> list[dict]:
	identity_clause = (
		"\n\t\t\tand instructor.name = %(exact_instructor)s"
		if params.get("exact_instructor")
		else ""
	)
	base_sql = f"""
		select distinct instructor.name, instructor.instructor_name, instructor.department
		from `tabEduEdge Instructor Assignment` assignment
		inner join `tabInstructor` instructor on instructor.name = assignment.instructor
		where assignment.school_branch = %(branch)s
			and assignment.program_offering = %(program_offering)s
			and assignment.course = %(course)s
			and assignment.assignment_type in %(assignment_types)s
			and assignment.enabled = 1
			and instructor.status = 'Active'{identity_clause}
			and (assignment.valid_from is null or assignment.valid_from <= %(reference_date)s)
			and (assignment.valid_to is null or assignment.valid_to >= %(reference_date)s)
			and exists (
				select 1
				from `tabEduEdge Instructor Branch Assignment` eligibility
				where eligibility.instructor = assignment.instructor
					and eligibility.school_branch = assignment.school_branch
					and eligibility.enabled = 1
					and (eligibility.valid_from is null or eligibility.valid_from <= %(reference_date)s)
					and (eligibility.valid_to is null or eligibility.valid_to >= %(reference_date)s)
			)
			and (
				assignment.assignment_scope = %(class_scope)s
				or (
					assignment.assignment_scope = %(arm_scope)s
					and assignment.student_group = %(student_group)s
				)
			)
	"""
	search_text = str(query or "").strip()
	if not search_text:
		return frappe.db.sql(
			f"{base_sql} order by instructor.instructor_name asc limit %(candidate_limit)s",
			params,
			as_dict=True,
		)

	rows: list[dict] = []
	seen: set[str] = set()
	for index, anchor in enumerate(query_anchors(search_text)):
		remaining = CANDIDATE_LIMIT - len(rows)
		if remaining <= 0:
			break
		anchor_params = {
			**params,
			"candidate_limit": remaining,
			f"search_anchor_{index}": f"%{anchor}%",
		}
		matches = frappe.db.sql(
			f"""
			{base_sql}
			and (
				instructor.name like %(search_anchor_{index})s
				or coalesce(instructor.instructor_name, '') like %(search_anchor_{index})s
				or coalesce(instructor.department, '') like %(search_anchor_{index})s
			)
			order by instructor.instructor_name asc
			limit %(candidate_limit)s
			""",
			anchor_params,
			as_dict=True,
		)
		for row in matches:
			if not row.name or row.name in seen:
				continue
			seen.add(row.name)
			rows.append(row)
			if len(rows) >= CANDIDATE_LIMIT:
				break
	return rows


def _limited_legacy_instructor_query(
	exact_instructor: str,
	branch: str,
	reference_date,
	txt: str,
	start: int,
	page_len: int,
) -> list[list[str]]:
	"""Return only the current limited User's eligible Instructor in legacy Branch mode."""
	if int(start) > 0 or int(page_len) <= 0:
		return []
	if not eligibility_covers_period(
		exact_instructor,
		branch,
		reference_date,
		reference_date,
	):
		return []
	row = frappe.db.get_value(
		"Instructor",
		exact_instructor,
		["name", "instructor_name", "department", "status"],
		as_dict=True,
	)
	if not row or row.status != "Active":
		return []
	search_text = str(txt or "").strip().lower()
	if search_text:
		haystack = " ".join(
			str(value or "").lower()
			for value in (row.name, row.instructor_name, row.department)
		)
		if search_text not in haystack:
			return []
	return [[row.name, row.instructor_name or row.name, row.department or ""]]


def _limited_course_schedule_group_rows(
	exact_instructor: str,
	branch: str,
	reference_date,
	txt: str,
	start: int,
	page_len: int,
	*,
	program: str = "",
	academic_year: str = "",
	exact_mode: bool,
) -> list[dict]:
	"""Return only class options the limited Instructor may schedule on the date."""
	if int(page_len) <= 0:
		return []
	params = {
		"branch": branch,
		"instructor": exact_instructor,
		"reference_date": reference_date,
		"assignment_types": tuple(sorted(COURSE_REQUIRED_TYPES)),
		"class_scope": CLASS_SCOPE,
		"arm_scope": CLASS_ARM_SCOPE,
		"txt": f"%{str(txt or '').strip()}%",
		"start": int(start),
		"page_len": int(page_len),
		"program": str(program or "").strip(),
		"academic_year": str(academic_year or "").strip(),
	}
	conditions = [
		f"student_group.\`{BRANCH_FIELD}\` = %(branch)s",
		"student_group.disabled = 0",
	]
	if params["program"]:
		conditions.append("student_group.program = %(program)s")
	if params["academic_year"]:
		conditions.append("student_group.academic_year = %(academic_year)s")
	conditions.append(
		"""(
			student_group.name like %(txt)s
			or coalesce(student_group.student_group_name, '') like %(txt)s
			or coalesce(student_group.program, '') like %(txt)s
			or coalesce(student_group.course, '') like %(txt)s
		)"""
	)

	if exact_mode:
		if not frappe.get_meta("Student Group").has_field(OFFERING_FIELD):
			return []
		from_sql = f"""
			from \`tabStudent Group\` student_group
			inner join \`tabEduEdge Instructor Assignment\` assignment
				on assignment.program_offering = student_group.\`{OFFERING_FIELD}\`
		"""
		conditions.extend(
			[
				"assignment.school_branch = %(branch)s",
				"assignment.instructor = %(instructor)s",
				"assignment.assignment_type in %(assignment_types)s",
				"assignment.enabled = 1",
				"(assignment.valid_from is null or assignment.valid_from <= %(reference_date)s)",
				"(assignment.valid_to is null or assignment.valid_to >= %(reference_date)s)",
				"""(
					assignment.assignment_scope = %(class_scope)s
					or (
						assignment.assignment_scope = %(arm_scope)s
						and assignment.student_group = student_group.name
					)
				)""",
				"""exists (
					select 1
					from \`tabEduEdge Instructor Branch Assignment\` eligibility
					where eligibility.instructor = assignment.instructor
						and eligibility.school_branch = assignment.school_branch
						and eligibility.enabled = 1
						and (eligibility.valid_from is null or eligibility.valid_from <= %(reference_date)s)
						and (eligibility.valid_to is null or eligibility.valid_to >= %(reference_date)s)
				)""",
			]
		)
	else:
		if not eligibility_covers_period(
			exact_instructor,
			branch,
			reference_date,
			reference_date,
		):
			return []
		from_sql = "from \`tabStudent Group\` student_group"

	return frappe.db.sql(
		f"""
		select distinct
			student_group.name,
			student_group.student_group_name,
			student_group.program,
			student_group.course
		{from_sql}
		where {" and ".join(conditions)}
		order by student_group.student_group_name asc, student_group.name asc
		limit %(start)s, %(page_len)s
		""",
		params,
		as_dict=True,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def course_schedule_student_group_query(doctype, txt, searchfield, start, page_len, filters):
	"""Return classes valid for Course Schedule authoring without requiring a prior schedule."""
	_require_academic_operator()
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	branch = str(filters.get(BRANCH_FIELD) or filters.get("school_branch") or "").strip()
	reference_date = filters.get("reference_date")
	if not branch or not reference_date:
		return []
	assert_branch_access(branch)
	if not is_limited_instructor_user():
		return legacy_student_group_query(doctype, txt, searchfield, start, page_len, filters)

	exact_instructor = resolve_exact_instructor_for_user()
	if not exact_instructor:
		return []
	target_date = getdate(reference_date)
	exact_mode = bool(
		frappe.db.exists("DocType", ASSIGNMENT_DOCTYPE)
		and frappe.db.exists(ASSIGNMENT_DOCTYPE, {"school_branch": branch})
	)
	rows = _limited_course_schedule_group_rows(
		exact_instructor,
		branch,
		target_date,
		str(txt or ""),
		int(start),
		int(page_len),
		program=str(filters.get("program") or ""),
		academic_year=str(filters.get("academic_year") or ""),
		exact_mode=exact_mode,
	)
	return [
		[
			row.name,
			row.student_group_name or row.name,
			" → ".join(value for value in (row.program, row.course) if value),
		]
		for row in rows
	]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def course_schedule_instructor_query(doctype, txt, searchfield, start, page_len, filters):
	"""Return only Instructors who can teach the selected scheduled Subject context."""
	_require_academic_operator()
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	branch = str(filters.get(BRANCH_FIELD) or filters.get("school_branch") or "").strip()
	student_group = str(filters.get("student_group") or "").strip()
	course = str(filters.get("course") or "").strip()
	reference_date = filters.get("reference_date")
	if not branch or not student_group or not course or not reference_date:
		return []
	assert_branch_access(branch)
	target_date = getdate(reference_date)
	limited_instructor = is_limited_instructor_user()
	exact_instructor = (
		resolve_exact_instructor_for_user()
		if limited_instructor
		else ""
	)
	if limited_instructor and not exact_instructor:
		return []

	group_fields = ["name", BRANCH_FIELD, "disabled"]
	if frappe.get_meta("Student Group").has_field(OFFERING_FIELD):
		group_fields.append(OFFERING_FIELD)
	group = frappe.db.get_value("Student Group", student_group, group_fields, as_dict=True)
	if not group or group.disabled:
		return []
	if group.get(BRANCH_FIELD) != branch:
		frappe.throw(_("Class Arm / Student Group belongs to another Branch."), frappe.ValidationError)

	# Preserve legacy installations until a Branch starts using Academic Instructor
	# Assignments. Backend schedule validation uses the same migration-safe boundary.
	if not frappe.db.exists("DocType", ASSIGNMENT_DOCTYPE) or not frappe.db.exists(
		ASSIGNMENT_DOCTYPE, {"school_branch": branch}
	):
		if limited_instructor:
			return _limited_legacy_instructor_query(
				exact_instructor,
				branch,
				target_date,
				str(txt or ""),
				int(start),
				int(page_len),
			)
		return legacy_branch_instructor_query(doctype, txt, searchfield, start, page_len, filters)

	program_offering = group.get(OFFERING_FIELD) or _group_offering(student_group)
	if not program_offering:
		return []
	rows = _eligible_instructor_rows(
		{
			"branch": branch,
			"exact_instructor": exact_instructor or None,
			"program_offering": program_offering,
			"course": course,
			"assignment_types": tuple(sorted(COURSE_REQUIRED_TYPES)),
			"reference_date": target_date,
			"class_scope": CLASS_SCOPE,
			"arm_scope": CLASS_ARM_SCOPE,
			"student_group": student_group,
			"candidate_limit": CANDIDATE_LIMIT,
		},
		str(txt or ""),
	)
	candidates = [
		{
			"value": row.name,
			"label": row.instructor_name or row.name,
			"description": row.department or "",
		}
		for row in rows
	]
	ranked = rank_link_rows(
		candidates,
		str(txt or ""),
		start=int(start),
		page_length=int(page_len),
	)
	return [[row["value"], row["label"], row.get("description") or ""] for row in ranked]
