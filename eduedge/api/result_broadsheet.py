from __future__ import annotations

import csv
import io
import json

import frappe
from frappe import _

from eduedge.education.offerings import assert_branch_access, get_context_branch
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

BROADSHEET_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
	"Academics User",
}


def _require_access() -> None:
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	if not BROADSHEET_ROLES.intersection(frappe.get_roles(frappe.session.user)):
		frappe.throw(_("You are not permitted to view Result Broadsheets."), frappe.PermissionError)


def _resolve_branch(branch: str | None) -> str:
	resolved = branch or (get_current_school_branch() or {}).get("name") or get_context_branch()
	if not resolved:
		frappe.throw(_("Select a School Branch / Campus."), frappe.ValidationError)
	assert_branch_access(resolved)
	return resolved


def _publication_options(branch: str) -> dict:
	rows = frappe.get_all(
		"EduEdge Result Publication",
		filters={"school_branch": branch, "status": "Published"},
		fields=["name", "student_group", "academic_year", "academic_term", "result_mode", "publication_version", "published_on"],
		order_by="published_on desc, publication_version desc",
		page_length=0,
	)
	return {
		"academic_years": sorted({row.academic_year for row in rows if row.academic_year}, reverse=True),
		"academic_terms": sorted({row.academic_term for row in rows if row.academic_term}),
		"student_groups": sorted({row.student_group for row in rows if row.student_group}),
		"result_modes": sorted({row.result_mode or "Terminal" for row in rows}),
	}


def _matching_publications(
	branch: str,
	*,
	academic_year: str,
	student_group: str,
	result_mode: str,
	academic_term: str | None,
) -> list[dict]:
	filters = {
		"school_branch": branch,
		"status": "Published",
		"academic_year": academic_year,
		"student_group": student_group,
		"result_mode": result_mode,
	}
	if result_mode == "Annual":
		filters["academic_term"] = ["is", "not set"]
	elif academic_term:
		filters["academic_term"] = academic_term
	else:
		frappe.throw(_("Select an Academic Term for a Terminal broadsheet."), frappe.ValidationError)

	rows = frappe.get_all(
		"EduEdge Result Publication",
		filters=filters,
		fields=[
			"name",
			"title",
			"school_branch",
			"student_group",
			"academic_year",
			"academic_term",
			"assessment_group",
			"result_mode",
			"result_profile",
			"publication_version",
			"published_on",
		],
		order_by="publication_version desc, published_on desc, creation desc",
		page_length=0,
	)
	latest: dict[tuple[str, str], dict] = {}
	for row in rows:
		key = (row.result_profile or "", row.assessment_group or "")
		if key not in latest:
			latest[key] = dict(row)
	return list(latest.values())


def _snapshot_payloads(publication: str) -> list[dict]:
	rows = frappe.get_all(
		"EduEdge Published Result Snapshot",
		filters={"result_publication": publication},
		fields=["student", "student_name", "payload_json"],
		order_by="student_name asc, student asc",
		page_length=0,
	)
	payloads = []
	for row in rows:
		try:
			payload = json.loads(row.payload_json or "{}")
		except (TypeError, ValueError):
			continue
		payloads.append(payload)
	return payloads


def _subject_value(subject: dict, result_mode: str):
	if not subject.get("eligible", True):
		return None
	fieldname = "annual_percentage" if result_mode == "Annual" else "percentage"
	value = subject.get(fieldname)
	return value if value is not None else None


def _build_broadsheet(publication: dict) -> dict:
	payloads = _snapshot_payloads(publication["name"])
	subject_map = {}
	for payload in payloads:
		for subject in (payload.get("result") or {}).get("subjects") or []:
			course = subject.get("course")
			if not course:
				continue
			subject_map.setdefault(
				course,
				{
					"course": course,
					"course_name": subject.get("course_name") or course,
				},
			)
	subjects = sorted(subject_map.values(), key=lambda row: (row["course_name"].casefold(), row["course"]))

	rows = []
	for payload in payloads:
		student = payload.get("student") or {}
		result = payload.get("result") or {}
		summary = result.get("summary") or {}
		attendance = payload.get("attendance") or {}
		by_course = {row.get("course"): row for row in result.get("subjects") or [] if row.get("course")}
		scores = {
			subject["course"]: _subject_value(by_course.get(subject["course"]) or {}, publication["result_mode"])
			for subject in subjects
		}
		rows.append(
			{
				"student": student.get("name"),
				"student_name": student.get("student_name") or student.get("name"),
				"roll_number": student.get("group_roll_number"),
				"scores": scores,
				"overall_percentage": summary.get("overall_percentage"),
				"overall_grade": summary.get("overall_grade") or "",
				"overall_remark": summary.get("overall_remark") or "",
				"attendance_percentage": attendance.get("attendance_percentage"),
			}
		)

	return {
		"publication": publication,
		"subjects": subjects,
		"rows": rows,
		"student_count": len(rows),
		"subject_count": len(subjects),
		"note": _("Broadsheet values come from immutable published snapshots. Position/rank is not inferred unless an Institution ranking policy is explicitly configured."),
	}


@frappe.whitelist()
def get_broadsheet_context(
	school_branch: str | None = None,
	academic_year: str | None = None,
	academic_term: str | None = None,
	student_group: str | None = None,
	result_mode: str | None = None,
	publication: str | None = None,
) -> dict:
	_require_access()
	branch = _resolve_branch(school_branch)
	options = _publication_options(branch)
	mode = result_mode or "Terminal"
	if mode not in {"Terminal", "Annual"}:
		frappe.throw(_("Invalid Result Mode."), frappe.ValidationError)

	response = {
		"filters": {
			"school_branch": branch,
			"academic_year": academic_year or "",
			"academic_term": "" if mode == "Annual" else (academic_term or ""),
			"student_group": student_group or "",
			"result_mode": mode,
		},
		"allowed_branches": get_allowed_school_branches(),
		"options": options,
		"publication": None,
		"publication_choices": [],
		"subjects": [],
		"rows": [],
		"student_count": 0,
		"subject_count": 0,
		"note": "",
	}
	if not academic_year or not student_group:
		return response

	choices = _matching_publications(
		branch,
		academic_year=academic_year,
		student_group=student_group,
		result_mode=mode,
		academic_term=academic_term,
	)
	response["publication_choices"] = choices
	selected = None
	if publication:
		selected = next((row for row in choices if row["name"] == publication), None)
		if not selected:
			frappe.throw(_("Selected Result Publication is outside this broadsheet scope."), frappe.PermissionError)
	elif len(choices) == 1:
		selected = choices[0]
	if not selected:
		if len(choices) > 1:
			response["note"] = _("More than one published Result Profile exists for this class and period. Select the exact Published Result before opening the broadsheet.")
		return response
	response.update(_build_broadsheet(selected))
	return response


@frappe.whitelist()
def download_broadsheet_csv(publication: str) -> None:
	_require_access()
	publication_row = frappe.db.get_value(
		"EduEdge Result Publication",
		publication,
		[
			"name",
			"school_branch",
			"student_group",
			"academic_year",
			"academic_term",
			"result_mode",
			"result_profile",
			"publication_version",
			"published_on",
			"status",
		],
		as_dict=True,
	)
	if not publication_row or publication_row.status != "Published":
		frappe.throw(_("Select a Published Result Publication."), frappe.ValidationError)
	assert_branch_access(publication_row.school_branch)

	data = _build_broadsheet(dict(publication_row))
	buffer = io.StringIO()
	writer = csv.writer(buffer)
	header = ["Roll No", "Student ID", "Student Name"]
	header.extend(subject["course_name"] for subject in data["subjects"])
	header.extend(["Overall %", "Grade", "Remark", "Attendance %"])
	writer.writerow(header)

	for row in data["rows"]:
		values = [row.get("roll_number") or "", row.get("student") or "", row.get("student_name") or ""]
		values.extend(
			"" if row["scores"].get(subject["course"]) is None else row["scores"].get(subject["course"])
			for subject in data["subjects"]
		)
		values.extend([
			row.get("overall_percentage") if row.get("overall_percentage") is not None else "",
			row.get("overall_grade") or "",
			row.get("overall_remark") or "",
			row.get("attendance_percentage") if row.get("attendance_percentage") is not None else "",
		])
		writer.writerow(values)

	frappe.response.filename = f"Result Broadsheet {publication}.csv"
	frappe.response.filecontent = buffer.getvalue().encode("utf-8-sig")
	frappe.response.type = "binary"
