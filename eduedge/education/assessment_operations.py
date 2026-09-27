from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.academic_operations import assert_instructor_assignment
from eduedge.education.curriculum_permissions import is_teacher_user
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.instructor_assignment_capabilities import require_instructor_assignment_capability
from eduedge.education.instructor_assignments import assert_schedule_instructor_assignment
from eduedge.education.offerings import assert_branch_access
from eduedge.education.result_engine import (
	SCORE_STATES,
	build_component_plan_maximum_blockers,
	build_missing_result_blockers,
	compose_cumulative_subject_results,
	compose_terminal_subject_results,
	get_result_periods,
)
from eduedge.education.result_attendance import (
	build_result_attendance_summary,
	get_official_attendance_blockers,
)
from eduedge.education.result_profile import get_result_profile_config
from eduedge.education.teaching_assignments import require_course_assignment

PUBLICATION_DOCTYPE = "EduEdge Result Publication"
PUBLICATION_LOG_DOCTYPE = "EduEdge Result Publication Log"
PUBLICATION_STATUSES = {
	"Draft",
	"Pending Approval",
	"Approved",
	"Rejected",
	"Published",
}

PROFILE_BACKED_PUBLICATION_REQUIRED = _(
	"New governed Result Publications require a Result Profile. "
	"Existing legacy Assessment Group publications remain available for read and history only."
)


def assert_profile_backed_publication(doc) -> None:
	if doc.get("result_profile"):
		return
	frappe.throw(PROFILE_BACKED_PUBLICATION_REQUIRED, frappe.ValidationError)


def before_validate_assessment_plan(doc, method=None) -> None:
	group = _get_student_group(doc.student_group)
	_assign_branch(doc, group.get(BRANCH_FIELD))
	_validate_branch(doc)
	_validate_linked_context(doc, group)
	_validate_assessment_plan_criteria_course(doc)
	if is_teacher_user():
		program_offering = group.get(OFFERING_FIELD) or _resolve_group_offering(group)
		assessment_date = doc.schedule_date or nowdate()
		require_course_assignment(
			doc.course,
			branch=doc.get(BRANCH_FIELD),
			program_offering=program_offering,
			student_group=doc.student_group,
			on_date=assessment_date,
		)
		require_instructor_assignment_capability(
			"can_create_assessment_plans",
			user=frappe.session.user,
			school_branch=doc.get(BRANCH_FIELD),
			program_offering=program_offering or "",
			student_group=doc.student_group,
			course=doc.course,
			on_date=assessment_date,
		)
	if doc.room:
		room_branch = frappe.db.get_value("Room", doc.room, BRANCH_FIELD)
		if room_branch != doc.get(BRANCH_FIELD):
			frappe.throw(
				_("Assessment room must belong to the selected School Branch / Campus."),
				frappe.ValidationError,
			)
	_validate_examiner_and_supervisor(doc)


def _validate_assessment_plan_criteria_course(doc) -> None:
	selected = [
		str(row.get("assessment_criteria") or "").strip()
		for row in (doc.get("assessment_criteria") or [])
		if str(row.get("assessment_criteria") or "").strip()
	]
	if not selected:
		return
	if len(selected) != len(set(selected)):
		frappe.throw(
			_("Assessment Criteria cannot be repeated within the same Assessment Plan."),
			frappe.ValidationError,
		)

	allowed = set(
		frappe.get_all(
			"Course Assessment Criteria",
			filters={"parent": doc.course, "parenttype": "Course"},
			pluck="assessment_criteria",
			limit_page_length=0,
		)
	)
	invalid = sorted(set(selected) - allowed)
	if invalid:
		frappe.throw(
			_(
				"Assessment Criteria {0} are not configured for Subject / Course {1}."
			).format(", ".join(invalid), doc.course),
			frappe.ValidationError,
		)


def _validate_examiner_and_supervisor(doc) -> None:
	reference_date = doc.schedule_date or nowdate()
	if doc.get("examiner"):
		try:
			assert_instructor_assignment(
				doc.examiner,
				doc.get(BRANCH_FIELD),
				reference_date=reference_date,
			)
			assert_schedule_instructor_assignment(
				frappe._dict(
					{
						"instructor": doc.examiner,
						"student_group": doc.student_group,
						"course": doc.course,
						"schedule_date": reference_date,
						BRANCH_FIELD: doc.get(BRANCH_FIELD),
					}
				)
			)
		except frappe.ValidationError:
			frappe.throw(
				_("Examiner {0} must have an effective Subject Instructor Assignment for this Class, Subject and assessment date.").format(doc.examiner),
				frappe.ValidationError,
			)

	if doc.get("supervisor"):
		try:
			# A Supervisor/Invigilator does not need to teach the assessed Subject. The
			# operational requirement here is valid Branch eligibility on the date.
			assert_instructor_assignment(
				doc.supervisor,
				doc.get(BRANCH_FIELD),
				reference_date=reference_date,
			)
		except frappe.ValidationError:
			frappe.throw(
				_("Supervisor {0} must have active Branch eligibility for the assessment date.").format(doc.supervisor),
				frappe.ValidationError,
			)


def before_validate_assessment_result(doc, method=None) -> None:
	if doc.is_new():
		_lock_assessment_plan_for_result(doc.assessment_plan)
	_assert_no_active_assessment_result_duplicate(doc)
	plan = _get_assessment_plan(doc.assessment_plan)
	if cint(plan.docstatus) != 1:
		frappe.throw(
			_("Assessment Results can only be created against a submitted Assessment Plan."),
			frappe.ValidationError,
		)
	_apply_assessment_result_plan_contract(doc, plan)
	score_state = str(doc.get("eduedge_score_state") or "Scored")
	if score_state not in SCORE_STATES:
		frappe.throw(
			_("Invalid Assessment Result score state: {0}.").format(score_state),
			frappe.ValidationError,
		)
	if score_state != "Scored" and any(
		abs(flt(row.get("score"))) > 1e-9 for row in (doc.get("details") or [])
	):
		frappe.throw(
			_(
				"Absent, Exempt and Not Offered Assessment Results must use zero criterion scores."
			),
			frappe.ValidationError,
		)
	student_branch = frappe.db.get_value("Student", doc.student, BRANCH_FIELD)
	plan_branch = plan.get(BRANCH_FIELD)
	resolved_branch = plan_branch or student_branch
	_assign_branch(doc, resolved_branch)
	_validate_branch(doc)
	if plan_branch and doc.get(BRANCH_FIELD) != plan_branch:
		frappe.throw(
			_("Assessment Result Branch must match the selected Assessment Plan Branch."),
			frappe.ValidationError,
		)
	if student_branch and doc.get(BRANCH_FIELD) != student_branch:
		frappe.throw(
			_("Assessment Result Branch must match the selected Student Branch."),
			frappe.ValidationError,
		)
	if plan.student_group and not frappe.db.exists(
		"Student Group Student",
		{"parent": plan.student_group, "student": doc.student, "active": 1},
	):
		frappe.throw(
			_("Student {0} is not an active member of Student Group {1}.").format(
				doc.student, plan.student_group
			),
			frappe.ValidationError,
		)
	if is_teacher_user():
		group = _get_student_group(plan.student_group)
		program_offering = group.get(OFFERING_FIELD) or _resolve_group_offering(group)
		# Mark entry is an operational permission evaluated at the time of entry, not
		# merely on the historic assessment date. Former Instructors therefore do not
		# retain mark-entry access after their exact responsibility has ended.
		require_instructor_assignment_capability(
			"can_enter_marks",
			user=frappe.session.user,
			school_branch=doc.get(BRANCH_FIELD),
			program_offering=program_offering or "",
			student_group=plan.student_group,
			course=plan.course,
			on_date=nowdate(),
		)


def _lock_assessment_plan_for_result(assessment_plan: str) -> None:
	"""Serialize new results per Plan so duplicate Student+Plan inserts cannot race."""
	rows = frappe.db.sql(
		"select name from `tabAssessment Plan` where name=%s for update",
		(assessment_plan,),
	)
	if not rows:
		frappe.throw(_("Assessment Plan does not exist."), frappe.DoesNotExistError)


def _assert_no_active_assessment_result_duplicate(doc) -> None:
	filters = {
		"assessment_plan": doc.assessment_plan,
		"student": doc.student,
		"docstatus": ["!=", 2],
	}
	if doc.name:
		filters["name"] = ["!=", doc.name]
	duplicate = frappe.db.exists(
		"Assessment Result",
		filters,
	)
	if duplicate:
		frappe.throw(
			_(
				"Assessment Result {0} already exists for this Student and Assessment Plan."
			).format(duplicate),
			frappe.DuplicateEntryError,
		)


def _apply_assessment_result_plan_contract(doc, plan) -> None:
	"""Make the submitted Assessment Plan authoritative for result scope and criteria."""
	for fieldname, value in (
		("student_group", plan.student_group),
		("program", plan.program),
		("course", plan.course),
		("academic_year", plan.academic_year),
		("academic_term", plan.academic_term),
		("assessment_group", plan.assessment_group),
		("grading_scale", plan.grading_scale),
	):
		doc.set(fieldname, value)
	doc.maximum_score = flt(plan.maximum_assessment_score)

	criteria_rows = frappe.get_all(
		"Assessment Plan Criteria",
		filters={"parent": plan.name, "parenttype": "Assessment Plan"},
		fields=["assessment_criteria", "maximum_score", "idx"],
		order_by="idx asc",
		page_length=0,
	)
	expected_names = [
		str(row.assessment_criteria or "").strip()
		for row in criteria_rows
		if str(row.assessment_criteria or "").strip()
	]
	if not expected_names:
		frappe.throw(
			_("Submitted Assessment Plan has no Assessment Criteria."),
			frappe.ValidationError,
		)
	if len(expected_names) != len(set(expected_names)):
		frappe.throw(
			_("Submitted Assessment Plan has duplicate Assessment Criteria."),
			frappe.ValidationError,
		)

	expected_maximum = {
		str(row.assessment_criteria): flt(row.maximum_score)
		for row in criteria_rows
		if row.assessment_criteria
	}
	configured_total = sum(expected_maximum.values())
	if abs(configured_total - flt(plan.maximum_assessment_score)) > 1e-9:
		frappe.throw(
			_("Submitted Assessment Plan criteria no longer match its Maximum Assessment Score."),
			frappe.ValidationError,
		)

	actual_rows = list(doc.get("details") or [])
	actual_names = [
		str(row.get("assessment_criteria") or "").strip()
		for row in actual_rows
	]
	if any(not name for name in actual_names):
		frappe.throw(
			_("Every Assessment Result detail row requires an Assessment Criterion."),
			frappe.ValidationError,
		)
	if len(actual_names) != len(set(actual_names)):
		frappe.throw(
			_("Assessment Result criteria cannot be repeated."),
			frappe.ValidationError,
		)

	missing = sorted(set(expected_names) - set(actual_names))
	extra = sorted(set(actual_names) - set(expected_names))
	if missing or extra:
		frappe.throw(
			_(
				"Assessment Result criteria must exactly match the submitted Assessment Plan. "
				"Missing: {0}. Unexpected: {1}."
			).format(", ".join(missing) or "-", ", ".join(extra) or "-"),
			frappe.ValidationError,
		)

	for row in actual_rows:
		criterion = str(row.assessment_criteria)
		maximum_score = expected_maximum[criterion]
		raw_score = row.get("score")
		if raw_score in (None, ""):
			frappe.throw(
				_("Assessment Criterion {0} requires an explicit score.").format(criterion),
				frappe.ValidationError,
			)
		score = flt(raw_score)
		if score < 0 or score > maximum_score:
			frappe.throw(
				_(
					"Score for Assessment Criterion {0} must be between 0 and {1}."
				).format(criterion, maximum_score),
				frappe.ValidationError,
			)
		row.maximum_score = maximum_score


def validate_publication_scope(doc) -> None:
	if doc.status not in PUBLICATION_STATUSES:
		frappe.throw(_("Invalid result publication status."), frappe.ValidationError)
	group = _get_student_group(doc.student_group)
	branch = group.get(BRANCH_FIELD)
	if branch != doc.school_branch:
		frappe.throw(
			_("Result Publication Branch must match the selected Student Group Branch."),
			frappe.ValidationError,
		)
	assert_branch_access(doc.school_branch)
	if group.academic_year != doc.academic_year:
		frappe.throw(
			_("Result Publication Academic Year must match the Student Group."),
			frappe.ValidationError,
		)
	if doc.academic_term and group.academic_term and doc.academic_term != group.academic_term:
		frappe.throw(
			_("Result Publication Academic Term must match the Student Group."),
			frappe.ValidationError,
		)
	if not doc.get("result_profile") and not doc.assessment_group:
		frappe.throw(
			_("Select either a Result Profile or an Assessment Group for result publication."),
			frappe.ValidationError,
		)
	if doc.academic_term:
		actual_year = frappe.db.get_value("Academic Term", doc.academic_term, "academic_year")
		if actual_year != doc.academic_year:
			frappe.throw(
				_("Academic Term {0} does not belong to Academic Year {1}.").format(
					doc.academic_term, doc.academic_year
				),
				frappe.ValidationError,
			)
	if doc.is_new():
		assert_profile_backed_publication(doc)
		return
	if doc.has_value_changed("status") and not getattr(
		frappe.flags, "in_eduedge_result_publication_transition", False
	):
		frappe.throw(
			_("Use the EduEdge Result Publication actions to change status."),
			frappe.ValidationError,
		)


def _get_publication_cohort_students(
	*,
	school_branch: str,
	student_group: str,
	plan_names: list[str],
) -> list:
	"""Preserve historically assessed students in the publication cohort.

	Student Group maintenance retains removed learners as inactive child rows.
	An inactive row remains in the result cohort only when a non-cancelled
	Assessment Result exists in the exact Branch and Assessment Plan scope.
	"""
	roster_rows = frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group, "parenttype": "Student Group"},
		fields=["student", "student_name", "group_roll_number", "active"],
		order_by="group_roll_number asc, student_name asc, idx asc",
		page_length=0,
	)
	historical_result_students: set[str] = set()
	if plan_names:
		historical_result_students = {
			student
			for student in frappe.get_all(
				"Assessment Result",
				filters={
					BRANCH_FIELD: school_branch,
					"assessment_plan": ["in", plan_names],
					"docstatus": ["!=", 2],
				},
				pluck="student",
				page_length=0,
			)
			if student
		}

	return [
		frappe._dict(
			{
				"student": row.student,
				"student_name": row.student_name,
				"group_roll_number": row.group_roll_number,
			}
		)
		for row in roster_rows
		if row.student and (cint(row.active) or row.student in historical_result_students)
	]


def build_duplicate_assessment_result_blockers(result_rows: list) -> list[dict]:
	"""Fail publication closed when legacy/import drift contains duplicate active results."""
	pairs: dict[tuple[str, str], list[str]] = defaultdict(list)
	for row in result_rows or []:
		plan_name = str(row.get("assessment_plan") or "")
		student = str(row.get("student") or "")
		name = str(row.get("name") or "")
		if plan_name and student:
			pairs[(plan_name, student)].append(name)

	return [
		{
			"code": "DUPLICATE_ASSESSMENT_RESULTS",
			"reason": _(
				"Multiple active Assessment Results exist for one Student and Assessment Plan."
			),
			"assessment_plan": plan_name,
			"student": student,
			"assessment_results": sorted(name for name in names if name),
		}
		for (plan_name, student), names in sorted(pairs.items())
		if len(names) > 1
	]


def get_publication_readiness(
	*,
	school_branch: str,
	student_group: str,
	academic_year: str,
	assessment_group: str | None = None,
	academic_term: str | None = None,
	result_profile: str | None = None,
	result_mode: str = "Terminal",
	profile_config_override: dict | None = None,
) -> dict:
	assert_branch_access(school_branch)
	group = _get_student_group(student_group)
	if group.get(BRANCH_FIELD) != school_branch:
		frappe.throw(_("Student Group belongs to another branch."), frappe.PermissionError)

	profile_config = (
		profile_config_override
		if profile_config_override is not None
		else (get_result_profile_config(result_profile) if result_profile else None)
	)
	profile_blockers: list[dict] = []
	assessment_groups = None
	periods: list[dict] = []
	if profile_config:
		assessment_groups = sorted(
			{
				leaf
				for source in profile_config.get("component_sources") or []
				for leaf in source.get("leaf_assessment_groups") or []
			}
		)
		if not assessment_groups:
			profile_blockers.append({"reason": "Result Profile has no resolved Assessment Groups."})
	if result_mode == "Annual":
		if not profile_config:
			profile_blockers.append(
				{"reason": "Annual Result Publication requires a Result Profile.", "code": "RESULT_PROFILE_REQUIRED"}
			)
		elif group.academic_term:
			profile_blockers.append(
				{
					"reason": "Annual results require a sessional Student Group/Class Arm. Legacy term-bound groups must be migrated or reviewed before annual publication.",
					"code": "TERM_BOUND_ANNUAL_COHORT",
				}
			)
		else:
			periods = get_result_periods(profile_config, academic_year)
			if not periods:
				profile_blockers.append(
					{"reason": "No Academic Calendar periods are enabled for result aggregation.", "code": "NO_RESULT_PERIODS"}
				)

	plan_filters: dict = {
		BRANCH_FIELD: school_branch,
		"student_group": student_group,
		"academic_year": academic_year,
		"docstatus": 1,
	}
	if profile_config:
		plan_filters["assessment_group"] = ["in", assessment_groups or ["__none__"]]
	else:
		if not assessment_group:
			profile_blockers.append(
				{"reason": "Select an Assessment Group or Result Profile.", "code": "RESULT_SCOPE_REQUIRED"}
			)
		plan_filters["assessment_group"] = assessment_group or "__none__"
	if result_mode == "Annual":
		plan_filters["academic_term"] = [
			"in",
			[row["academic_term"] for row in periods] or ["__none__"],
		]
	elif academic_term:
		plan_filters["academic_term"] = academic_term

	plans = frappe.get_all(
		"Assessment Plan",
		filters=plan_filters,
		fields=[
			"name",
			"assessment_name",
			"assessment_group",
			"course",
			"academic_term",
			"maximum_assessment_score",
		],
		order_by="schedule_date asc, course asc",
	)
	if profile_config:
		profile_blockers.extend(
			build_component_plan_maximum_blockers(profile_config, plans)
		)
		profile_blockers.extend(
			_build_required_course_plan_blockers(group, plans)
		)

	plan_names = [row.name for row in plans]
	students = _get_publication_cohort_students(
		school_branch=school_branch,
		student_group=student_group,
		plan_names=plan_names,
	)
	student_names = [row.student for row in students]
	if (
		profile_config
		and student_names
		and (profile_config.get("presentation") or {}).get("show_attendance")
	):
		_, attendance_meta = build_result_attendance_summary(
			school_branch=school_branch,
			student_group=student_group,
			academic_year=academic_year,
			academic_term=academic_term,
			result_mode=result_mode,
			students=student_names,
			periods=periods,
		)
		profile_blockers.extend(get_official_attendance_blockers(attendance_meta))
	results = []
	if plan_names and student_names:
		result_fields = [
			"name",
			"assessment_plan",
			"assessment_group",
			"student",
			"course",
			"academic_term",
			"docstatus",
			"maximum_score",
			"total_score",
			"grade",
			"grading_scale",
		]
		if frappe.get_meta("Assessment Result").has_field("eduedge_score_state"):
			result_fields.append("eduedge_score_state")
		results = frappe.get_all(
			"Assessment Result",
			filters={
				BRANCH_FIELD: school_branch,
				"assessment_plan": ["in", plan_names],
				"student": ["in", student_names],
				"docstatus": ["!=", 2],
			},
			fields=result_fields,
			page_length=0,
		)
	profile_blockers.extend(build_duplicate_assessment_result_blockers(results))
	result_pairs = {(row.assessment_plan, row.student) for row in results}
	expected = len(plans) * len(students)
	submitted = sum(1 for row in results if row.docstatus == 1)
	drafts = sum(1 for row in results if row.docstatus == 0)
	missing = max(expected - len(result_pairs), 0)

	composition_blockers: list[dict] = []
	unmapped_assessment_groups: set[str] = set()
	if profile_config:
		results_by_student: dict[str, list] = defaultdict(list)
		for row in results:
			if row.docstatus == 1:
				results_by_student[row.student].append(row)
		for student in student_names:
			if result_mode == "Annual":
				composed = compose_cumulative_subject_results(
					profile_config,
					results_by_student.get(student, []),
					periods,
				)
			else:
				composed = compose_terminal_subject_results(
					profile_config,
					results_by_student.get(student, []),
				)
			for blocker in composed.get("blockers") or []:
				composition_blockers.append({"student": student, **blocker})
			unmapped_assessment_groups.update(composed.get("unmapped_assessment_groups") or [])

	if profile_config:
		profile_blockers.extend(
			build_missing_result_blockers(
				profile_config,
				plans,
				results,
				student_names,
			)
		)
	all_blockers = profile_blockers + composition_blockers
	exclude_missing = bool(
		profile_config
		and profile_config.get("missing_result_policy") == "Exclude from Denominator"
	)
	ready = bool(
		plans
		and students
		and drafts == 0
		and (submitted == expected or exclude_missing)
		and (missing == 0 or exclude_missing)
		and not all_blockers
		and not unmapped_assessment_groups
	)
	return {
		"ready": ready,
		"school_branch": school_branch,
		"student_group": student_group,
		"academic_year": academic_year,
		"academic_term": academic_term,
		"assessment_group": assessment_group,
		"result_profile": result_profile,
		"result_mode": result_mode,
		"periods": periods,
		"expected_results": expected,
		"submitted_results": submitted,
		"draft_results": drafts,
		"missing_results": missing,
		"assessment_plan_count": len(plans),
		"student_count": len(students),
		"plans": plans,
		"students": students,
		"profile_blockers": all_blockers,
		"unmapped_assessment_groups": sorted(unmapped_assessment_groups),
	}


def _build_required_course_plan_blockers(group, plan_rows: list) -> list[dict]:
	"""Block official profile publication when a mandatory native Course has no plan.

	Course-based Student Groups are single-subject contexts. Program/class groups use
	the native Program Course.required flag so optional/elective subjects remain optional.
	"""
	expected: list[dict] = []
	if group.get("group_based_on") == "Course" and group.get("course"):
		expected = [{"course": group.course, "course_name": group.course}]
	elif group.get("program"):
		expected = frappe.get_all(
			"Program Course",
			filters={
				"parent": group.program,
				"parenttype": "Program",
				"required": 1,
			},
			fields=["course", "course_name"],
			order_by="idx asc",
			limit_page_length=0,
		)

	if not expected:
		return []

	planned_courses = {
		str(row.get("course") if hasattr(row, "get") else getattr(row, "course", "") or "")
		for row in (plan_rows or [])
	}
	return [
		{
			"code": "REQUIRED_PROGRAM_COURSE_MISSING",
			"reason": _(
				"Required subject {0} has no submitted Assessment Plan in this result scope."
			).format(row.get("course_name") or row.get("course")),
			"course": row.get("course"),
		}
		for row in expected
		if row.get("course") and row.get("course") not in planned_courses
	]


def append_publication_log(
	publication: str,
	*,
	action: str,
	from_status: str | None,
	to_status: str,
	remarks: str | None = None,
) -> str:
	log = frappe.get_doc(
		{
			"doctype": PUBLICATION_LOG_DOCTYPE,
			"result_publication": publication,
			"action": action,
			"from_status": from_status,
			"to_status": to_status,
			"acted_by": frappe.session.user,
			"acted_on": frappe.utils.now_datetime(),
			"remarks": remarks,
		}
	)
	log.insert(ignore_permissions=True)
	return log.name


def _assign_branch(doc, branch: str | None) -> None:
	if branch and not doc.get(BRANCH_FIELD):
		doc.set(BRANCH_FIELD, branch)


def _validate_branch(doc) -> None:
	branch = doc.get(BRANCH_FIELD)
	if not branch:
		frappe.throw(
			_("Select a School Branch / Campus before saving this record."),
			frappe.ValidationError,
		)
	assert_branch_access(branch)


def _validate_linked_context(doc, group) -> None:
	for fieldname in ("program", "course", "academic_year", "academic_term"):
		plan_value = doc.get(fieldname)
		group_value = group.get(fieldname)
		if plan_value and group_value and plan_value != group_value:
			frappe.throw(
				_("Assessment Plan {0} must match the selected Student Group.").format(fieldname),
				frappe.ValidationError,
			)
	if doc.schedule_date:
		date = getdate(doc.schedule_date)
		if group.academic_term:
			start_date, end_date = frappe.db.get_value(
				"Academic Term", group.academic_term, ["term_start_date", "term_end_date"]
			)
		else:
			start_date, end_date = frappe.db.get_value(
				"Academic Year", group.academic_year, ["year_start_date", "year_end_date"]
			)
		if start_date and end_date and not (getdate(start_date) <= date <= getdate(end_date)):
			frappe.throw(
				_("Assessment date must lie within the Student Group academic period."),
				frappe.ValidationError,
			)


def _resolve_group_offering(group) -> str | None:
	if group.get(OFFERING_FIELD):
		return group.get(OFFERING_FIELD)
	filters = {
		"program": group.program,
		"academic_year": group.academic_year,
		"school_branch": group.get(BRANCH_FIELD),
		"is_active": 1,
	}
	if group.academic_term:
		filters["academic_term"] = group.academic_term
	rows = frappe.get_all("EduEdge Program Offering", filters=filters, pluck="name", limit_page_length=2)
	return rows[0] if len(rows) == 1 else None


def _get_student_group(name: str):
	fields = ["name", "academic_year", "academic_term", "program", "course", "group_based_on", BRANCH_FIELD]
	if frappe.get_meta("Student Group").has_field(OFFERING_FIELD):
		fields.append(OFFERING_FIELD)
	row = frappe.db.get_value("Student Group", name, fields, as_dict=True)
	if not row:
		frappe.throw(_("Student Group does not exist."), frappe.DoesNotExistError)
	return row


def _get_assessment_plan(name: str):
	row = frappe.db.get_value(
		"Assessment Plan",
		name,
		[
			"name",
			"student_group",
			"program",
			"course",
			"schedule_date",
			"academic_year",
			"academic_term",
			"assessment_group",
			"grading_scale",
			"maximum_assessment_score",
			"docstatus",
			BRANCH_FIELD,
		],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Assessment Plan does not exist."), frappe.DoesNotExistError)
	return row
