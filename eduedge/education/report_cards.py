from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt, getdate

from education.education.api import get_grade
from education.education.report.course_wise_assessment_report.course_wise_assessment_report import (
	get_child_assessment_groups,
)

from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access

PUBLICATION_DOCTYPE = "EduEdge Result Publication"
REVIEW_DOCTYPE = "EduEdge Report Card Review"
REVIEW_STATUSES = {"Draft", "Recommended", "Approved"}
PROGRESSION_RECOMMENDATIONS = {
	"Pending Review",
	"Promote",
	"Repeat",
	"Graduate",
	"Transfer",
	"Not Applicable",
}
OPERATIONAL_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
	"Academics User",
	"Instructor",
	"Teacher",
}
APPROVER_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
}


def get_published_publication(name: str):
	publication = frappe.db.get_value(
		PUBLICATION_DOCTYPE,
		name,
		[
			"name",
			"title",
			"school_branch",
			"student_group",
			"academic_year",
			"academic_term",
			"assessment_group",
			"status",
			"report_card_ready",
			"published_on",
		],
		as_dict=True,
	)
	if not publication:
		frappe.throw(_("Result Publication does not exist."), frappe.DoesNotExistError)
	if publication.status != "Published" or not publication.report_card_ready:
		frappe.throw(
			_("Report cards are available only after results are approved and published."),
			frappe.ValidationError,
		)
	return publication


def validate_report_card_review(doc) -> None:
	publication = get_published_publication(doc.result_publication)
	expected = {
		"school_branch": publication.school_branch,
		"student_group": publication.student_group,
		"academic_year": publication.academic_year,
		"academic_term": publication.academic_term,
		"assessment_group": publication.assessment_group,
	}
	for fieldname, value in expected.items():
		if doc.get(fieldname) and doc.get(fieldname) != value:
			frappe.throw(
				_("Report Card Review {0} must match the published result scope.").format(fieldname),
				frappe.ValidationError,
			)
		doc.set(fieldname, value)

	assert_branch_access(publication.school_branch)
	if not frappe.db.exists(
		"Student Group Student",
		{"parent": publication.student_group, "student": doc.student, "active": 1},
	):
		frappe.throw(
			_("Student {0} is not an active member of Student Group {1}.").format(
				doc.student, publication.student_group
			),
			frappe.ValidationError,
		)

	if doc.progression_status not in REVIEW_STATUSES:
		frappe.throw(_("Invalid progression review status."), frappe.ValidationError)
	if doc.progression_recommendation not in PROGRESSION_RECOMMENDATIONS:
		frappe.throw(_("Invalid progression recommendation."), frappe.ValidationError)

	roles = set(frappe.get_roles(frappe.session.user))
	if (
		(doc.is_new() or doc.has_value_changed("principal_comment"))
		and (doc.principal_comment or "").strip()
		and not APPROVER_ROLES.intersection(roles)
	):
		frappe.throw(
			_("Only an authorized academic approver can set the principal comment."),
			frappe.PermissionError,
		)

	if doc.is_new():
		return

	for fieldname in (
		"result_publication",
		"school_branch",
		"student_group",
		"student",
		"academic_year",
		"academic_term",
		"assessment_group",
	):
		if doc.has_value_changed(fieldname):
			frappe.throw(
				_("Report Card Review scope cannot be changed after creation."),
				frappe.ValidationError,
			)

	if doc.has_value_changed("progression_status") and not getattr(
		frappe.flags, "in_eduedge_report_card_transition", False
	):
		frappe.throw(
			_("Use the EduEdge Report Card actions to change progression status."),
			frappe.ValidationError,
		)


def assert_report_card_access(publication, student: str, *, write: bool = False) -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)

	student_doc = frappe.get_doc("Student", student)
	roles = set(frappe.get_roles(frappe.session.user))
	if roles.intersection(OPERATIONAL_ROLES):
		assert_branch_access(publication.school_branch)
		if write and not roles.intersection(OPERATIONAL_ROLES):
			frappe.throw(_("You are not permitted to update report cards."), frappe.PermissionError)
	else:
		student_doc.check_permission("read")
		if write:
			frappe.throw(_("Published report cards are read-only."), frappe.PermissionError)

	if not frappe.db.exists(
		"Student Group Student",
		{"parent": publication.student_group, "student": student, "active": 1},
	):
		frappe.throw(_("Student is outside the published class scope."), frappe.PermissionError)


def get_publication_student_summaries(publication_name: str) -> list[dict]:
	publication = get_published_publication(publication_name)
	assert_branch_access(publication.school_branch)

	students = frappe.get_all(
		"Student Group Student",
		filters={"parent": publication.student_group, "active": 1},
		fields=["student", "student_name", "group_roll_number"],
		order_by="group_roll_number asc, student_name asc",
	)
	student_names = [row.student for row in students]
	if not student_names:
		return []

	result_rows = _get_result_rows(publication, student_names)
	attendance_rows = _get_attendance_rows(publication, student_names)
	reviews = frappe.get_all(
		REVIEW_DOCTYPE,
		filters={"result_publication": publication.name, "student": ["in", student_names]},
		fields=[
			"name",
			"student",
			"class_teacher_comment",
			"principal_comment",
			"progression_recommendation",
			"progression_status",
			"average_percent",
			"overall_grade",
			"attendance_percent",
			"recommended_by",
			"recommended_on",
			"approved_by",
			"approved_on",
			"last_review_note",
		],
		page_length=0,
	)
	review_by_student = {row.student: row for row in reviews}

	results_by_student: dict[str, list] = defaultdict(list)
	for row in result_rows:
		results_by_student[row.student].append(row)
	attendance_by_student = _summarize_attendance(attendance_rows)

	summaries = []
	for student in students:
		summary = _build_summary(
			publication,
			student.student,
			student.student_name,
			results_by_student.get(student.student, []),
			attendance_by_student.get(student.student, {}),
		)
		review = review_by_student.get(student.student)
		if review:
			summary["review"] = dict(review)
		else:
			summary["review"] = None
		summary["group_roll_number"] = student.group_roll_number
		summaries.append(summary)
	return summaries


def get_student_report_card_payload(publication_name: str, student: str) -> dict:
	publication = get_published_publication(publication_name)
	assert_report_card_access(publication, student)
	student_row = frappe.db.get_value(
		"Student",
		student,
		["name", "student_name", "image", "program"],
		as_dict=True,
	)
	if not student_row:
		frappe.throw(_("Student does not exist."), frappe.DoesNotExistError)

	result_rows = _get_result_rows(publication, [student])
	attendance_rows = _get_attendance_rows(publication, [student])
	attendance = _summarize_attendance(attendance_rows).get(student, {})
	summary = _build_summary(
		publication,
		student,
		student_row.student_name,
		result_rows,
		attendance,
	)
	review = frappe.db.get_value(
		REVIEW_DOCTYPE,
		{"result_publication": publication.name, "student": student},
		[
			"name",
			"class_teacher_comment",
			"principal_comment",
			"progression_recommendation",
			"progression_status",
			"recommended_by",
			"recommended_on",
			"approved_by",
			"approved_on",
			"last_review_note",
		],
		as_dict=True,
	)
	branch = frappe.db.get_value(
		"EduEdge School Branch",
		publication.school_branch,
		["name", "branch_name", "branch_code", "company", "address"],
		as_dict=True,
	)
	company = None
	if branch and branch.company:
		company = frappe.db.get_value(
			"Company",
			branch.company,
			["name", "company_name", "company_logo"],
			as_dict=True,
		)
	address = None
	if branch and branch.address:
		address = frappe.db.get_value(
			"Address",
			branch.address,
			[
				"address_line1",
				"address_line2",
				"city",
				"state",
				"country",
				"pincode",
				"phone",
				"email_id",
			],
			as_dict=True,
		)

	return {
		"publication": dict(publication),
		"student": dict(student_row),
		"branch": dict(branch) if branch else {},
		"company": dict(company) if company else {},
		"address": dict(address) if address else {},
		"summary": summary,
		"review": dict(review) if review else {},
	}


def refresh_review_metrics(doc) -> dict:
	publication = get_published_publication(doc.result_publication)
	payload = get_student_report_card_payload(publication.name, doc.student)
	summary = payload["summary"]
	for fieldname in (
		"course_count",
		"total_score",
		"maximum_score",
		"average_percent",
		"overall_grade",
		"attendance_present",
		"attendance_absent",
		"attendance_leave",
		"attendance_total",
		"attendance_percent",
	):
		doc.set(fieldname, summary.get(fieldname))
	return summary


def _get_result_rows(publication, students: list[str]) -> list:
	assessment_groups = get_child_assessment_groups(publication.assessment_group)
	filters: dict = {
		BRANCH_FIELD: publication.school_branch,
		"student_group": publication.student_group,
		"academic_year": publication.academic_year,
		"assessment_group": ["in", assessment_groups],
		"student": ["in", students],
		"docstatus": 1,
	}
	if publication.academic_term:
		filters["academic_term"] = publication.academic_term
	return frappe.get_all(
		"Assessment Result",
		filters=filters,
		fields=[
			"name",
			"student",
			"student_name",
			"course",
			"assessment_group",
			"maximum_score",
			"total_score",
			"grade",
			"grading_scale",
		],
		order_by="student asc, course asc, assessment_group asc",
		page_length=0,
	)


def _get_attendance_rows(publication, students: list[str]) -> list:
	from_date, to_date = _get_period_dates(publication)
	if not from_date or not to_date:
		return []
	return frappe.get_all(
		"Student Attendance",
		filters={
			BRANCH_FIELD: publication.school_branch,
			"student": ["in", students],
			"docstatus": 1,
			"date": ["between", [from_date, to_date]],
		},
		fields=["student", "status"],
		page_length=0,
	)


def _get_period_dates(publication) -> tuple:
	if publication.academic_term:
		return frappe.db.get_value(
			"Academic Term",
			publication.academic_term,
			["term_start_date", "term_end_date"],
		)
	return frappe.db.get_value(
		"Academic Year",
		publication.academic_year,
		["year_start_date", "year_end_date"],
	)


def _summarize_attendance(rows: list) -> dict[str, dict]:
	output: dict[str, dict] = defaultdict(lambda: {"Present": 0, "Absent": 0, "Leave": 0})
	for row in rows:
		status = row.status or ""
		if status not in output[row.student]:
			output[row.student][status] = 0
		output[row.student][status] += 1
	return output


def _build_summary(publication, student: str, student_name: str, results: list, attendance: dict) -> dict:
	courses: dict[str, dict] = {}
	total_score = 0.0
	maximum_score = 0.0
	grading_scales = set()

	for row in results:
		course = row.course or _("Unspecified Course")
		course_row = courses.setdefault(
			course,
			{
				"course": course,
				"course_name": frappe.db.get_value("Course", course, "course_name") or course,
				"total_score": 0.0,
				"maximum_score": 0.0,
				"assessment_count": 0,
				"grade": "",
			},
		)
		course_row["total_score"] += flt(row.total_score)
		course_row["maximum_score"] += flt(row.maximum_score)
		course_row["assessment_count"] += 1
		total_score += flt(row.total_score)
		maximum_score += flt(row.maximum_score)
		if row.grading_scale:
			grading_scales.add(row.grading_scale)

	for course_row in courses.values():
		course_row["average_percent"] = (
			flt(course_row["total_score"]) / flt(course_row["maximum_score"]) * 100
			if flt(course_row["maximum_score"])
			else 0
		)
		if len(grading_scales) == 1:
			course_row["grade"] = get_grade(
				next(iter(grading_scales)), course_row["average_percent"]
			)

	average_percent = total_score / maximum_score * 100 if maximum_score else 0
	overall_grade = (
		get_grade(next(iter(grading_scales)), average_percent)
		if len(grading_scales) == 1 and maximum_score
		else ""
	)
	present = int(attendance.get("Present", 0))
	absent = int(attendance.get("Absent", 0))
	leave = int(attendance.get("Leave", 0))
	attendance_total = sum(int(value or 0) for value in attendance.values())
	attendance_percent = present / attendance_total * 100 if attendance_total else 0
	settings = frappe.get_single("EduEdge Settings")
	pass_average = flt(settings.promotion_pass_average or 0)
	suggested = "Promote" if maximum_score and average_percent >= pass_average else "Repeat"
	if not maximum_score:
		suggested = "Pending Review"

	return {
		"student": student,
		"student_name": student_name,
		"result_publication": publication.name,
		"student_group": publication.student_group,
		"academic_year": publication.academic_year,
		"academic_term": publication.academic_term,
		"assessment_group": publication.assessment_group,
		"course_count": len(courses),
		"courses": sorted(courses.values(), key=lambda row: row["course_name"]),
		"total_score": total_score,
		"maximum_score": maximum_score,
		"average_percent": average_percent,
		"overall_grade": overall_grade,
		"attendance_present": present,
		"attendance_absent": absent,
		"attendance_leave": leave,
		"attendance_total": attendance_total,
		"attendance_percent": attendance_percent,
		"suggested_progression": suggested,
	}
