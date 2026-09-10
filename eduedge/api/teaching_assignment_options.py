from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate

from eduedge.api.academic_operations import (
	_require_academic_operator,
	instructor_query as legacy_branch_instructor_query,
)
from eduedge.api.fuzzy_search import CANDIDATE_LIMIT, query_anchors, rank_link_rows
from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.instructor_assignments import _group_offering
from eduedge.education.offerings import assert_branch_access
from eduedge.education.teaching_assignments import (
	CLASS_ARM_SCOPE,
	CLASS_SCOPE,
	COURSE_REQUIRED_TYPES,
)

ASSIGNMENT_DOCTYPE = "EduEdge Instructor Assignment"


def _eligible_instructor_rows(params: dict, query: str) -> list[dict]:
	base_sql = """
		select distinct instructor.name, instructor.instructor_name, instructor.department
		from `tabEduEdge Instructor Assignment` assignment
		inner join `tabInstructor` instructor on instructor.name = assignment.instructor
		where assignment.school_branch = %(branch)s
			and assignment.program_offering = %(program_offering)s
			and assignment.course = %(course)s
			and assignment.assignment_type in %(assignment_types)s
			and assignment.enabled = 1
			and instructor.status = 'Active'
			and (assignment.valid_from is null or assignment.valid_from <= %(reference_date)s)
			and (assignment.valid_to is null or assignment.valid_to >= %(reference_date)s)
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
		return legacy_branch_instructor_query(doctype, txt, searchfield, start, page_len, filters)

	program_offering = group.get(OFFERING_FIELD) or _group_offering(student_group)
	if not program_offering:
		return []
	rows = _eligible_instructor_rows(
		{
			"branch": branch,
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
