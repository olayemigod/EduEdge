from __future__ import annotations

import frappe

from eduedge.access_control import user_has_role_permission
from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.instructor_scope import (
	instructor_owns_schedule,
	is_limited_instructor_user,
	resolve_exact_instructor_for_user,
)
from eduedge.education.teaching_assignments import (
	CLASS_ARM_SCOPE,
	CLASS_RESPONSIBILITY_TYPES,
	CLASS_SCOPE,
	COURSE_REQUIRED_TYPES,
	has_class_responsibility_assignment,
)
from eduedge.services.branch_context import (
	get_allowed_school_branches,
	is_branch_access_enforced,
)

BRANCH_AWARE_DOCTYPES = (
	"Student Admission",
	"Student Applicant",
	"Student",
	"Guardian",
	"Program Enrollment",
	"Student Group",
	"Room",
	"Course Schedule",
	"Student Attendance",
	"Assessment Plan",
	"Assessment Result",
	"EduEdge Result Publication",
	"EduEdge Published Result Snapshot",
	"EduEdge Report Card Review",
	"EduEdge Report Card Issue",
	"EduEdge Program Offering",
	"EduEdge Instructor Branch Assignment",
)
BRANCH_SCOPE_BYPASS_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
}


def school_branch_query(user: str | None = None) -> str:
	if not is_branch_access_enforced():
		return ""
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user):
		return ""
	allowed = _allowed_branch_names(resolved_user)
	if not allowed:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	return f"`tabEduEdge School Branch`.name in ({values})"


def student_admission_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	if is_limited_instructor_user(resolved_user):
		return "1=0"
	return _branch_condition("Student Admission", resolved_user)


def student_applicant_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	if is_limited_instructor_user(resolved_user):
		return "1=0"
	return _branch_condition("Student Applicant", resolved_user)


def student_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	branch_condition = _branch_condition("Student", resolved_user)
	return _and_conditions(branch_condition, _owned_student_condition("`tabStudent`.name", resolved_user))


def program_enrollment_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	branch_condition = _branch_condition("Program Enrollment", resolved_user)
	return _and_conditions(
		branch_condition,
		_owned_student_condition("`tabProgram Enrollment`.student", resolved_user),
	)


def student_group_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	branch_condition = _branch_condition("Student Group", resolved_user)
	if not is_limited_instructor_user(resolved_user):
		return branch_condition
	ownership = _schedule_assignment_condition("schedule", resolved_user)
	if ownership == "1=0":
		return "1=0"
	ownership_condition = f"""
		exists (
			select 1
			from `tabCourse Schedule` schedule
			where schedule.student_group = `tabStudent Group`.name
				and ({ownership})
		)
	"""
	return _and_conditions(branch_condition, ownership_condition)


def room_query(user: str | None = None) -> str:
	return _branch_condition("Room", user)


def course_schedule_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	branch_condition = _branch_condition("Course Schedule", resolved_user)
	if not is_limited_instructor_user(resolved_user):
		return branch_condition
	return _and_conditions(
		branch_condition,
		_schedule_assignment_condition("`tabCourse Schedule`", resolved_user),
	)


def student_attendance_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	branch_condition = _branch_condition("Student Attendance", resolved_user)
	if not is_limited_instructor_user(resolved_user):
		return branch_condition
	ownership = _schedule_assignment_condition("schedule", resolved_user)
	if ownership == "1=0":
		return "1=0"
	ownership_condition = f"""
		exists (
			select 1
			from `tabCourse Schedule` schedule
			where schedule.name = `tabStudent Attendance`.course_schedule
				and ({ownership})
		)
	"""
	return _and_conditions(branch_condition, ownership_condition)


def assessment_plan_query(user: str | None = None) -> str:
	return _branch_condition("Assessment Plan", user)


def assessment_result_query(user: str | None = None) -> str:
	return _branch_condition("Assessment Result", user)


def result_publication_query(user: str | None = None) -> str:
	return _governed_result_query("EduEdge Result Publication", user)


def published_result_snapshot_query(user: str | None = None) -> str:
	return _class_responsibility_result_query("EduEdge Published Result Snapshot", user)


def result_publication_log_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user):
		return ""
	allowed = _allowed_branch_names(resolved_user)
	if not allowed:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	instructor_condition = ""
	if is_limited_instructor_user(resolved_user):
		ownership = _owned_student_group_condition("publication.student_group", resolved_user)
		if ownership == "1=0":
			return "1=0"
		instructor_condition = f"""
				and ({ownership})
		"""
	return f"""
		exists (
			select 1
			from `tabEduEdge Result Publication` publication
			where publication.name = `tabEduEdge Result Publication Log`.result_publication
				and publication.school_branch in ({values})
				{instructor_condition}
		)
	"""


def report_card_review_query(user: str | None = None) -> str:
	return _class_responsibility_result_query("EduEdge Report Card Review", user)


def report_card_issue_query(user: str | None = None) -> str:
	return _class_responsibility_result_query("EduEdge Report Card Issue", user)


def program_offering_query(user: str | None = None) -> str:
	return _branch_condition("EduEdge Program Offering", user, fieldname="school_branch")


def instructor_assignment_query(user: str | None = None) -> str:
	return _branch_condition(
		"EduEdge Instructor Branch Assignment",
		user,
		fieldname="school_branch",
	)


def guardian_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user) or not _branch_field_exists("Student"):
		return ""
	allowed = _allowed_branch_names(resolved_user)
	if not allowed:
		return "1=0"
	branch_values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	teacher_condition = ""
	if is_limited_instructor_user(resolved_user):
		ownership = _owned_student_condition("student.name", resolved_user)
		if ownership == "1=0":
			return "1=0"
		teacher_condition = f"""
			and ({ownership})
		"""
	return f"""
		exists (
			select 1
			from `tabGuardian Student` guardian_student
			inner join `tabStudent` student on student.name = guardian_student.student
			where guardian_student.parent = `tabGuardian`.name
				and guardian_student.parenttype = 'Guardian'
				and student.`{BRANCH_FIELD}` in ({branch_values})
				{teacher_condition}
		)
	"""


def has_education_branch_permission(doc, user=None, permission_type=None) -> bool:
	"""Allow Role Permission Manager decisions unless branch isolation denies the record."""
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user):
		return True
	allowed = _allowed_branch_names(resolved_user)
	if not doc:
		return True

	if doc.doctype == "Guardian":
		if doc.is_new():
			return True
		student_names = [row.student for row in (doc.get("students") or []) if row.student]
		if not student_names:
			return False
		branches = set(
			frappe.get_all(
				"Student",
				filters={"name": ["in", student_names]},
				pluck=BRANCH_FIELD,
			)
		)
		return bool(branches.intersection(allowed))

	if not _branch_field_exists(doc.doctype):
		return True
	branch = doc.get(BRANCH_FIELD)
	return branch in allowed


def has_student_admission_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	return not is_limited_instructor_user(resolved_user) and has_education_branch_permission(
		doc, resolved_user, permission_type
	)


def has_student_applicant_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	return not is_limited_instructor_user(resolved_user) and has_education_branch_permission(
		doc, resolved_user, permission_type
	)


def has_student_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	if not has_education_branch_permission(doc, resolved_user, permission_type):
		return False
	if not is_limited_instructor_user(resolved_user):
		return True
	return bool(doc and _student_is_owned(doc.name, resolved_user))


def has_program_enrollment_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	if not has_education_branch_permission(doc, resolved_user, permission_type):
		return False
	if not is_limited_instructor_user(resolved_user):
		return True
	return bool(doc and _student_is_owned(doc.get("student"), resolved_user))


def has_guardian_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	if not has_education_branch_permission(doc, resolved_user, permission_type):
		return False
	if not is_limited_instructor_user(resolved_user):
		return True
	if not doc or doc.is_new():
		return False
	return any(
		_student_is_owned(row.student, resolved_user)
		for row in (doc.get("students") or [])
		if row.student
	)


def has_student_group_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	if not has_education_branch_permission(doc, resolved_user, permission_type):
		return False
	if not is_limited_instructor_user(resolved_user):
		return True
	if not doc or doc.is_new():
		return False
	ownership = _schedule_assignment_condition("schedule", resolved_user)
	if ownership == "1=0":
		return False
	return bool(
		frappe.db.sql(
			f"""
			select schedule.name
			from `tabCourse Schedule` schedule
			where schedule.student_group = %s
				and ({ownership})
			limit 1
			""",
			(doc.name,),
		)
	)


def has_course_schedule_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	if not has_education_branch_permission(doc, resolved_user, permission_type):
		return False
	return instructor_owns_schedule(doc, resolved_user)


def has_student_attendance_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	if not has_education_branch_permission(doc, resolved_user, permission_type):
		return False
	if not is_limited_instructor_user(resolved_user):
		return True
	course_schedule = doc.get("course_schedule") if doc else None
	if not course_schedule:
		return False
	schedule = frappe.db.get_value(
		"Course Schedule",
		course_schedule,
		["name", "instructor"],
		as_dict=True,
	)
	return instructor_owns_schedule(schedule, resolved_user)


def has_school_branch_record_permission(doc, user=None, permission_type=None) -> bool:
	if not is_branch_access_enforced():
		return True
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user):
		return True
	if not doc:
		return True
	allowed = _allowed_branch_names(resolved_user)
	name = doc if isinstance(doc, str) else doc.name
	return name in allowed


def has_school_branch_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user):
		return True
	if not doc:
		return True
	allowed = _allowed_branch_names(resolved_user)
	return doc.get("school_branch") in allowed


def has_result_publication_permission(doc, user=None, permission_type=None) -> bool:
	return _has_governed_result_permission(doc, user, permission_type)


def has_published_result_snapshot_permission(doc, user=None, permission_type=None) -> bool:
	return _has_class_responsibility_result_permission(doc, user, permission_type)


def has_report_card_review_permission(doc, user=None, permission_type=None) -> bool:
	return _has_class_responsibility_result_permission(doc, user, permission_type)


def has_report_card_issue_permission(doc, user=None, permission_type=None) -> bool:
	return _has_class_responsibility_result_permission(doc, user, permission_type)


def has_result_publication_log_permission(doc, user=None, permission_type=None) -> bool:
	if not doc:
		return True
	publication = frappe.db.get_value(
		"EduEdge Result Publication",
		doc.get("result_publication"),
		["school_branch", "student_group"],
		as_dict=True,
	)
	if not publication:
		return False
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user):
		return True
	allowed = _allowed_branch_names(resolved_user)
	if publication.school_branch not in allowed:
		return False
	return _has_instructor_student_group_scope(publication.student_group, resolved_user)


def _has_class_responsibility_result_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	if not has_school_branch_permission(doc, resolved_user, permission_type):
		return False
	if not is_limited_instructor_user(resolved_user):
		return True
	if not doc:
		return False

	student_group = doc.get("student_group")
	academic_year = doc.get("academic_year")
	academic_term = doc.get("academic_term")
	if doc.get("result_publication") and (not student_group or not academic_year):
		publication = frappe.db.get_value(
			"EduEdge Result Publication",
			doc.get("result_publication"),
			["student_group", "academic_year", "academic_term"],
			as_dict=True,
		)
		if publication:
			student_group = student_group or publication.student_group
			academic_year = academic_year or publication.academic_year
			academic_term = academic_term or publication.academic_term
	return has_class_responsibility_assignment(
		student_group,
		user=resolved_user,
		academic_term=academic_term,
		academic_year=academic_year,
	)


def _class_responsibility_result_query(doctype: str, user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	branch_condition = _branch_condition(doctype, resolved_user, fieldname="school_branch")
	if not is_limited_instructor_user(resolved_user):
		return branch_condition
	if (
		not frappe.db.exists("DocType", "EduEdge Instructor Assignment")
		or not frappe.get_meta("Student Group").has_field(OFFERING_FIELD)
	):
		return "1=0"

	instructor_values = _instructor_sql_values(resolved_user)
	if not instructor_values:
		return "1=0"
	types = ", ".join(frappe.db.escape(value) for value in sorted(CLASS_RESPONSIBILITY_TYPES))
	table = f"`tab{doctype}`"
	reference_date = (
		f"coalesce("
		f"(select term_end_date from `tabAcademic Term` term where term.name = {table}.academic_term), "
		f"(select year_end_date from `tabAcademic Year` year where year.name = {table}.academic_year), "
		f"current_date)"
	)
	responsibility = f"""
		exists (
			select 1
			from `tabEduEdge Instructor Assignment` assignment
			inner join `tabStudent Group` student_group
				on student_group.name = {table}.student_group
			where assignment.instructor in ({instructor_values})
				and assignment.enabled = 1
				and assignment.school_branch = {table}.school_branch
				and assignment.program_offering = student_group.`{OFFERING_FIELD}`
				and assignment.assignment_type in ({types})
				and coalesce(assignment.course, '') = ''
				and (
					assignment.assignment_scope = {frappe.db.escape(CLASS_SCOPE)}
					or (
						assignment.assignment_scope = {frappe.db.escape(CLASS_ARM_SCOPE)}
						and assignment.student_group = {table}.student_group
					)
				)
				and (assignment.valid_from is null or assignment.valid_from <= {reference_date})
				and (assignment.valid_to is null or assignment.valid_to >= {reference_date})
		)
	"""
	return _and_conditions(branch_condition, responsibility)


def _governed_result_query(doctype: str, user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	branch_condition = _branch_condition(doctype, resolved_user, fieldname="school_branch")
	return _and_conditions(
		branch_condition,
		_owned_student_group_condition(f"`tab{doctype}`.`student_group`", resolved_user),
	)


def _has_governed_result_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	if not has_school_branch_permission(doc, resolved_user, permission_type):
		return False
	if not is_limited_instructor_user(resolved_user):
		return True
	if not doc:
		return True
	student_group = doc.get("student_group")
	if not student_group and doc.get("result_publication"):
		student_group = frappe.db.get_value(
			"EduEdge Result Publication",
			doc.get("result_publication"),
			"student_group",
		)
	return _has_instructor_student_group_scope(student_group, resolved_user)


def _has_instructor_student_group_scope(student_group: str | None, user: str) -> bool:
	if not is_limited_instructor_user(user):
		return True
	if not student_group:
		return False
	ownership = _schedule_assignment_condition("schedule", user)
	if ownership == "1=0":
		return False
	return bool(
		frappe.db.sql(
			f"""
			select schedule.name
			from `tabCourse Schedule` schedule
			where schedule.student_group = %s
				and ({ownership})
			limit 1
			""",
			(student_group,),
		)
	)


def _owned_student_group_condition(group_expression: str, user: str) -> str:
	if not is_limited_instructor_user(user):
		return ""
	ownership = _schedule_assignment_condition("schedule", user)
	if ownership == "1=0":
		return "1=0"
	return f"""
		exists (
			select 1
			from `tabCourse Schedule` schedule
			where schedule.student_group = {group_expression}
				and ({ownership})
		)
	"""


def _owned_student_condition(student_expression: str, user: str) -> str:
	if not is_limited_instructor_user(user):
		return ""
	ownership = _schedule_assignment_condition("schedule", user)
	if ownership == "1=0":
		return "1=0"
	return f"""
		exists (
			select 1
			from `tabStudent Group Student` group_student
			inner join `tabCourse Schedule` schedule on schedule.student_group = group_student.parent
			where group_student.parenttype = 'Student Group'
				and group_student.active = 1
				and group_student.student = {student_expression}
				and ({ownership})
		)
	"""


def _student_is_owned(student: str | None, user: str) -> bool:
	if not student:
		return False
	ownership = _schedule_assignment_condition("schedule", user)
	if ownership == "1=0":
		return False
	return bool(
		frappe.db.sql(
			f"""
			select schedule.name
			from `tabStudent Group Student` group_student
			inner join `tabCourse Schedule` schedule on schedule.student_group = group_student.parent
			where group_student.parenttype = 'Student Group'
				and group_student.active = 1
				and group_student.student = %s
				and ({ownership})
			limit 1
			""",
			(student,),
		)
	)


def _schedule_assignment_condition(schedule_alias: str, user: str) -> str:
	"""Mirror document-level schedule ownership inside list permission SQL.

	Branches that have not adopted Academic Instructor Assignments keep the legacy
	Instructor-owned schedule behavior. Once any academic assignment exists in a
	Branch, a limited Instructor sees only schedules backed by an effective exact
	Subject responsibility and a covering Branch Eligibility period.
	"""
	values = _instructor_sql_values(user)
	if not values:
		return "1=0"

	instructor_identity = f"{schedule_alias}.instructor in ({values})"
	if (
		not frappe.db.exists("DocType", "EduEdge Instructor Assignment")
		or not frappe.db.exists("DocType", "EduEdge Instructor Branch Assignment")
		or not frappe.get_meta("Student Group").has_field(OFFERING_FIELD)
	):
		return instructor_identity

	assignment_types = ", ".join(
		frappe.db.escape(value) for value in sorted(COURSE_REQUIRED_TYPES)
	)
	class_scope = frappe.db.escape(CLASS_SCOPE)
	arm_scope = frappe.db.escape(CLASS_ARM_SCOPE)
	branch_field = f"{schedule_alias}.`{BRANCH_FIELD}`"
	return _and_conditions(
		instructor_identity,
		f"""
		(
			not exists (
				select 1
				from `tabEduEdge Instructor Assignment` branch_assignment
				where branch_assignment.school_branch = {branch_field}
			)
			or exists (
				select 1
				from `tabEduEdge Instructor Assignment` assignment
				inner join `tabStudent Group` student_group
					on student_group.name = {schedule_alias}.student_group
				where assignment.instructor = {schedule_alias}.instructor
					and assignment.instructor in ({values})
					and assignment.school_branch = {branch_field}
					and assignment.program_offering = student_group.`{OFFERING_FIELD}`
					and assignment.course = {schedule_alias}.course
					and assignment.assignment_type in ({assignment_types})
					and assignment.enabled = 1
					and (
						assignment.assignment_scope = {class_scope}
						or (
							assignment.assignment_scope = {arm_scope}
							and assignment.student_group = {schedule_alias}.student_group
						)
					)
					and (
						assignment.valid_from is null
						or assignment.valid_from <= {schedule_alias}.schedule_date
					)
					and (
						assignment.valid_to is null
						or assignment.valid_to >= {schedule_alias}.schedule_date
					)
					and exists (
						select 1
						from `tabEduEdge Instructor Branch Assignment` eligibility
						where eligibility.instructor = assignment.instructor
							and eligibility.school_branch = assignment.school_branch
							and eligibility.enabled = 1
							and (
								eligibility.valid_from is null
								or eligibility.valid_from <= {schedule_alias}.schedule_date
							)
							and (
								eligibility.valid_to is null
								or eligibility.valid_to >= {schedule_alias}.schedule_date
							)
					)
			)
		)
		""",
	)


def _instructor_sql_values(user: str) -> str:
	"""Return one exact Instructor identity for permission SQL, or fail closed."""
	instructor = resolve_exact_instructor_for_user(user)
	return frappe.db.escape(instructor) if instructor else ""


def _branch_condition(
	doctype: str,
	user: str | None,
	*,
	fieldname: str = BRANCH_FIELD,
) -> str:
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user) or not _branch_field_exists(doctype, fieldname):
		return ""
	allowed = _allowed_branch_names(resolved_user)
	if not allowed:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	return f"`tab{doctype}`.`{fieldname}` in ({values})"


def _and_conditions(*conditions: str) -> str:
	parts = [condition.strip() for condition in conditions if condition and condition.strip()]
	if not parts:
		return ""
	return " and ".join(f"({condition})" for condition in parts)


def _allowed_branch_names(user: str) -> set[str]:
	"""Return an explicit branch set for restricted users.

	An empty set means no permitted branches and must fail closed. Only the role
	bypass in _should_apply_branch_scope represents unrestricted access.
	"""
	if not frappe.db.count("EduEdge School Branch", {"enabled": 1}):
		return set()
	return {row["name"] for row in get_allowed_school_branches(user=user) if row.get("name")}


def _should_apply_branch_scope(user: str) -> bool:
	if not user or user in {"Guest", "Administrator"}:
		return False
	roles = set(frappe.get_roles(user))
	if roles.intersection(BRANCH_SCOPE_BYPASS_ROLES):
		return False
	return any(
		user_has_role_permission(doctype, permission_type, user)
		for doctype in BRANCH_AWARE_DOCTYPES
		for permission_type in ("read", "create", "write", "report")
	)


def _branch_field_exists(doctype: str, fieldname: str = BRANCH_FIELD) -> bool:
	try:
		return bool(frappe.get_meta(doctype).has_field(fieldname))
	except frappe.DoesNotExistError:
		return False
