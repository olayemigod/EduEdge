from __future__ import annotations

import json
from collections import Counter, defaultdict
from statistics import mean

import frappe
from frappe import _
from frappe.utils import flt

from eduedge.education.offerings import assert_branch_access, get_context_branch
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

INTELLIGENCE_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
	"Academics User",
}


def _require_intelligence_access() -> None:
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	if not INTELLIGENCE_ROLES.intersection(frappe.get_roles(frappe.session.user)):
		frappe.throw(_("You are not permitted to view Result Intelligence."), frappe.PermissionError)


def _resolve_branch(school_branch: str | None) -> str:
	branch = school_branch or (get_current_school_branch() or {}).get("name") or get_context_branch()
	if not branch:
		frappe.throw(_("Select a School Branch / Campus."), frappe.ValidationError)
	assert_branch_access(branch)
	return branch


def _latest_publications(
	branch: str,
	*,
	academic_year: str | None,
	academic_term: str | None,
	student_group: str | None,
	result_mode: str | None,
) -> list[dict]:
	filters: dict = {"school_branch": branch, "status": "Published"}
	if academic_year:
		filters["academic_year"] = academic_year
	if academic_term:
		filters["academic_term"] = academic_term
	if student_group:
		filters["student_group"] = student_group
	if result_mode:
		filters["result_mode"] = result_mode

	rows = frappe.get_all(
		"EduEdge Result Publication",
		filters=filters,
		fields=[
			"name",
			"student_group",
			"academic_year",
			"academic_term",
			"assessment_group",
			"result_profile",
			"result_mode",
			"publication_version",
			"published_on",
		],
		order_by="published_on asc, publication_version asc",
		page_length=0,
	)
	latest: dict[tuple, dict] = {}
	for row in rows:
		key = (
			row.student_group,
			row.academic_year,
			row.academic_term or "",
			row.result_profile or "",
			row.assessment_group or "",
			row.result_mode or "Terminal",
		)
		existing = latest.get(key)
		if not existing or int(row.publication_version or 1) >= int(existing.publication_version or 1):
			latest[key] = dict(row)
	return sorted(
		latest.values(),
		key=lambda row: (str(row.get("published_on") or ""), row.get("name") or ""),
	)


def _snapshot_payloads(publications: list[dict]) -> list[dict]:
	names = [row["name"] for row in publications]
	if not names:
		return []
	rows = frappe.get_all(
		"EduEdge Published Result Snapshot",
		filters={"result_publication": ["in", names]},
		fields=["result_publication", "student", "student_name", "payload_json"],
		page_length=0,
	)
	publication_by_name = {row["name"]: row for row in publications}
	output = []
	for row in rows:
		try:
			payload = json.loads(row.payload_json or "{}")
		except (TypeError, ValueError):
			continue
		payload["_publication_meta"] = publication_by_name.get(row.result_publication) or {}
		output.append(payload)
	return output


def _overall_percentage(payload: dict) -> float | None:
	value = ((payload.get("result") or {}).get("summary") or {}).get("overall_percentage")
	return flt(value) if value is not None else None


def _attendance_percentage(payload: dict) -> float | None:
	value = (payload.get("attendance") or {}).get("attendance_percentage")
	return flt(value) if value is not None else None


def _subject_percentage(subject: dict, mode: str) -> float | None:
	if not subject.get("eligible", True):
		return None
	fieldname = "annual_percentage" if mode == "Annual" else "percentage"
	value = subject.get(fieldname)
	return flt(value) if value is not None else None


def _period_label(payload: dict) -> str:
	publication = payload.get("publication") or {}
	meta = payload.get("_publication_meta") or {}
	mode = publication.get("result_mode") or meta.get("result_mode") or "Terminal"
	if mode == "Annual":
		return _("Annual")
	return (
		publication.get("academic_term_label")
		or publication.get("academic_term")
		or meta.get("academic_term")
		or _("Terminal")
	)


def _summary(payloads: list[dict]) -> dict:
	overall = [value for value in (_overall_percentage(row) for row in payloads) if value is not None]
	attendance = [value for value in (_attendance_percentage(row) for row in payloads) if value is not None]
	student_names = {
		(payload.get("student") or {}).get("name")
		for payload in payloads
		if (payload.get("student") or {}).get("name")
	}
	publications = {
		(payload.get("publication") or {}).get("name")
		for payload in payloads
		if (payload.get("publication") or {}).get("name")
	}
	cohort_average = mean(overall) if overall else 0.0
	return {
		"students": len(student_names),
		"publications": len(publications),
		"result_records": len(payloads),
		"overall_average": round(cohort_average, 2),
		"overall_highest": round(max(overall), 2) if overall else 0.0,
		"overall_lowest": round(min(overall), 2) if overall else 0.0,
		"attendance_average": round(mean(attendance), 2) if attendance else 0.0,
		"below_cohort_average": sum(1 for value in overall if value < cohort_average),
	}


def _subject_rows(payloads: list[dict]) -> list[dict]:
	values: dict[str, list[float]] = defaultdict(list)
	labels: dict[str, str] = {}
	for payload in payloads:
		mode = ((payload.get("publication") or {}).get("result_mode") or "Terminal")
		for subject in (payload.get("result") or {}).get("subjects") or []:
			course = subject.get("course")
			if not course:
				continue
			value = _subject_percentage(subject, mode)
			if value is None:
				continue
			labels[course] = subject.get("course_name") or course
			values[course].append(value)

	rows = []
	for course, scores in values.items():
		rows.append(
			{
				"course": course,
				"course_name": labels.get(course) or course,
				"students": len(scores),
				"average": round(mean(scores), 2),
				"highest": round(max(scores), 2),
				"lowest": round(min(scores), 2),
				"spread": round(max(scores) - min(scores), 2),
			}
		)
	return sorted(rows, key=lambda row: (row["average"], row["course_name"].casefold()))


def _student_rows(payloads: list[dict], cohort_average: float) -> list[dict]:
	rows = []
	for payload in payloads:
		student = payload.get("student") or {}
		publication = payload.get("publication") or {}
		result_summary = (payload.get("result") or {}).get("summary") or {}
		average = flt(result_summary.get("overall_percentage"))
		rows.append(
			{
				"student": student.get("name"),
				"student_name": student.get("student_name") or student.get("name"),
				"student_group": publication.get("student_group"),
				"academic_year": publication.get("academic_year"),
				"academic_term": publication.get("academic_term"),
				"period_label": _period_label(payload),
				"result_mode": publication.get("result_mode") or "Terminal",
				"average": round(average, 2),
				"grade": result_summary.get("overall_grade") or "",
				"attendance": round(flt((payload.get("attendance") or {}).get("attendance_percentage")), 2),
				"publication": publication.get("name"),
				"publication_version": int(publication.get("publication_version") or 1),
				"comparison": "Below cohort average" if average < cohort_average else "At / above cohort average",
			}
		)
	return sorted(rows, key=lambda row: (row["average"], (row["student_name"] or "").casefold()))


def _grade_distribution(payloads: list[dict]) -> list[dict]:
	counts = Counter(
		((payload.get("result") or {}).get("summary") or {}).get("overall_grade") or _("Ungraded")
		for payload in payloads
	)
	return [{"grade": grade, "count": count} for grade, count in sorted(counts.items())]


def _publication_trend(publications: list[dict], payloads: list[dict]) -> list[dict]:
	by_publication: dict[str, list[float]] = defaultdict(list)
	labels: dict[str, str] = {}
	for payload in payloads:
		publication = payload.get("publication") or {}
		name = publication.get("name")
		value = _overall_percentage(payload)
		if name and value is not None:
			by_publication[name].append(value)
			labels[name] = _period_label(payload)

	rows = []
	for publication in publications:
		values = by_publication.get(publication["name"]) or []
		if not values:
			continue
		rows.append(
			{
				"publication": publication["name"],
				"student_group": publication["student_group"],
				"academic_year": publication["academic_year"],
				"academic_term": publication.get("academic_term"),
				"result_mode": publication.get("result_mode") or "Terminal",
				"label": labels.get(publication["name"]) or publication.get("academic_term") or _("Annual"),
				"average": round(mean(values), 2),
				"highest": round(max(values), 2),
				"lowest": round(min(values), 2),
				"students": len(values),
				"published_on": publication.get("published_on"),
			}
		)
	return rows


def _options(branch: str) -> dict:
	publications = frappe.get_all(
		"EduEdge Result Publication",
		filters={"school_branch": branch, "status": "Published"},
		fields=["academic_year", "academic_term", "student_group", "result_mode"],
		page_length=0,
	)
	return {
		"academic_years": sorted({row.academic_year for row in publications if row.academic_year}, reverse=True),
		"academic_terms": sorted({row.academic_term for row in publications if row.academic_term}),
		"student_groups": sorted({row.student_group for row in publications if row.student_group}),
		"result_modes": sorted({row.result_mode or "Terminal" for row in publications}),
	}


@frappe.whitelist()
def get_result_intelligence(
	school_branch: str | None = None,
	academic_year: str | None = None,
	academic_term: str | None = None,
	student_group: str | None = None,
	result_mode: str | None = None,
) -> dict:
	_require_intelligence_access()
	branch = _resolve_branch(school_branch)
	if result_mode and result_mode not in {"Terminal", "Annual"}:
		frappe.throw(_("Invalid Result Mode."), frappe.ValidationError)

	publications = _latest_publications(
		branch,
		academic_year=academic_year,
		academic_term=academic_term,
		student_group=student_group,
		result_mode=result_mode,
	)
	payloads = _snapshot_payloads(publications)
	summary = _summary(payloads)
	subjects = _subject_rows(payloads)
	students = _student_rows(payloads, summary["overall_average"])

	current_branch = get_current_school_branch()
	return {
		"filters": {
			"school_branch": branch,
			"academic_year": academic_year or "",
			"academic_term": academic_term or "",
			"student_group": student_group or "",
			"result_mode": result_mode or "",
		},
		"allowed_branches": get_allowed_school_branches(),
		"current_branch": current_branch,
		"options": _options(branch),
		"summary": summary,
		"subject_performance": subjects,
		"student_performance": students,
		"weak_subjects": subjects[:5],
		"grade_distribution": _grade_distribution(payloads),
		"publication_trend": _publication_trend(publications, payloads),
		"notes": {
			"pass_rate": _("Pass rate is intentionally not inferred. Configure an explicit academic pass policy before introducing pass/fail analytics."),
			"source": _("All figures come from immutable Published Result Snapshots, not live draft marks."),
		},
	}
