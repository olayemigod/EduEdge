from __future__ import annotations

import json
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils.pdf import get_pdf

from eduedge.education.report_card_issues import get_effective_issued_payload

ISSUE_DOCTYPE = "EduEdge Report Card Issue"


def _require_login() -> str:
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	return user


def _portal_students(user: str) -> list[dict]:
	students: dict[str, dict] = {}

	for row in frappe.get_all(
		"Student",
		filters={"user": user, "enabled": 1},
		fields=["name", "student_name", "image"],
	):
		students[row.name] = {
			"name": row.name,
			"student_name": row.student_name,
			"image": row.image,
			"relationship": "Student",
		}

	guardians = frappe.get_all(
		"Guardian",
		filters={"user": user},
		fields=["name", "guardian_name"],
	)
	guardian_names = [row.name for row in guardians]
	guardian_label = {row.name: row.guardian_name for row in guardians}
	if guardian_names:
		relations = frappe.get_all(
			"Student Guardian",
			filters={
				"guardian": ["in", guardian_names],
				"parenttype": "Student",
				"parentfield": "guardians",
			},
			fields=["parent as student", "guardian", "relation"],
			page_length=0,
		)
		student_names = sorted({row.student for row in relations if row.student})
		student_rows = {
			row.name: row
			for row in frappe.get_all(
				"Student",
				filters={"name": ["in", student_names], "enabled": 1},
				fields=["name", "student_name", "image"],
			)
		}
		for relation in relations:
			student = student_rows.get(relation.student)
			if not student:
				continue
			students.setdefault(
				student.name,
				{
					"name": student.name,
					"student_name": student.student_name,
					"image": student.image,
					"relationship": relation.relation
					or guardian_label.get(relation.guardian)
					or "Guardian",
				},
			)

	return sorted(students.values(), key=lambda row: (row.get("student_name") or "").casefold())


def _assert_portal_student(user: str, student: str) -> dict:
	for row in _portal_students(user):
		if row["name"] == student:
			return row
	frappe.throw(
		_("You are not linked to this Student."),
		frappe.PermissionError,
	)


def _latest_effective_issues(student_names: list[str]) -> list[dict]:
	if not student_names:
		return []
	rows = frappe.get_all(
		ISSUE_DOCTYPE,
		filters={"student": ["in", student_names]},
		fields=[
			"name",
			"result_publication",
			"publication_version",
			"report_card_review",
			"issue_version",
			"student",
			"student_name",
			"school_branch",
			"student_group",
			"academic_year",
			"academic_term",
			"result_mode",
			"result_profile",
			"issued_on",
			"payload_hash",
		],
		order_by="student asc, result_publication asc, issue_version desc, creation desc",
		page_length=0,
	)
	latest: dict[tuple[str, str], dict] = {}
	for row in rows:
		key = (row.student, row.result_publication)
		if key in latest:
			continue
		payload = get_effective_issued_payload(row.result_publication, row.student)
		if not payload:
			continue
		latest[key] = {
			**dict(row),
			"summary": _portal_summary(payload),
		}
	return sorted(
		latest.values(),
		key=lambda row: (
			row.get("student_name") or "",
			row.get("academic_year") or "",
			row.get("issued_on") or "",
		),
		reverse=True,
	)


def _portal_summary(payload: dict) -> dict:
	summary = payload.get("summary") or {}
	publication = payload.get("publication") or {}
	institution = payload.get("institution") or {}
	branding = payload.get("branding") or {}
	return {
		"result_mode": summary.get("result_mode") or publication.get("result_mode") or "Terminal",
		"academic_term_label": summary.get("academic_term_label") or publication.get("academic_term"),
		"average_percent": summary.get("average_percent"),
		"overall_grade": summary.get("overall_grade"),
		"overall_remark": summary.get("overall_remark"),
		"attendance_percent": summary.get("attendance_percent"),
		"course_count": summary.get("course_count"),
		"publication_version": summary.get("publication_version") or publication.get("publication_version") or 1,
		"institution_name": branding.get("official_name")
		or institution.get("official_name")
		or institution.get("institution_name"),
		"branch_name": (payload.get("branch") or {}).get("branch_name"),
	}


@frappe.whitelist()
def get_my_results_context() -> dict:
	user = _require_login()
	students = _portal_students(user)
	issues = _latest_effective_issues([row["name"] for row in students])
	by_student: dict[str, list] = defaultdict(list)
	for issue in issues:
		by_student[issue["student"]].append(issue)
	for student in students:
		student["results"] = by_student.get(student["name"], [])
	return {
		"user": {
			"name": user,
			"full_name": frappe.utils.get_fullname(user),
		},
		"students": students,
		"result_count": len(issues),
	}


@frappe.whitelist()
def get_my_result(publication: str, student: str) -> dict:
	user = _require_login()
	_assert_portal_student(user, student)
	payload = get_effective_issued_payload(publication, student)
	if not payload:
		frappe.throw(
			_("This result is not currently available as an approved issued report card."),
			frappe.PermissionError,
		)
	return payload


@frappe.whitelist()
def download_my_result(publication: str, student: str) -> None:
	user = _require_login()
	_assert_portal_student(user, student)
	payload = get_effective_issued_payload(publication, student)
	if not payload:
		frappe.throw(
			_("This result is not currently available as an approved issued report card."),
			frappe.PermissionError,
		)

	settings = frappe.get_single("EduEdge Settings")
	branding = payload.get("branding") or {}
	letter_head_name = branding.get("report_card_letter_head") or settings.report_card_letter_head
	letterhead = (
		frappe.db.get_value("Letter Head", letter_head_name, "content")
		if letter_head_name
		else None
	)
	html = frappe.render_template(
		"eduedge/templates/report_card.html",
		{
			**payload,
			"letterhead": letterhead,
			"show_marks": bool(settings.report_card_show_marks),
		},
	)
	final_html = frappe.render_template(
		"frappe/www/printview.html",
		{"body": html, "title": _("Student Report Card")},
	)
	issue = payload.get("issue_record") or payload.get("issue") or {}
	issue_version = issue.get("issue_version") or 1
	frappe.response.filename = f"Report Card {student} v{issue_version}.pdf"
	frappe.response.filecontent = get_pdf(final_html)
	frappe.response.type = "pdf"
