from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.education.offerings import assert_branch_access
from eduedge.education.report_card_issues import (
	ISSUE_DOCTYPE,
	get_archived_report_card_pdf,
)
from eduedge.services.branch_context import get_allowed_school_branches

DEFAULT_PAGE_LENGTH = 20
MAX_PAGE_LENGTH = 50


def _require_archive_audit_access() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	if not frappe.has_permission(ISSUE_DOCTYPE, "read"):
		frappe.throw(
			_("You are not permitted to audit issued Report Card archives."),
			frappe.PermissionError,
		)


def _archive_status(row) -> tuple[str, str]:
	values = (
		str(row.get("pdf_sha256") or "").strip(),
		str(row.get("pdf_filename") or "").strip(),
		int(row.get("pdf_size_bytes") or 0),
	)
	if not any(values):
		return (
			"Legacy",
			_("This Issue predates immutable PDF archival and remains payload-verifiable only."),
		)
	if not all(values):
		return (
			"Incomplete",
			_("Archive metadata is incomplete. Treat this Issue as an integrity problem."),
		)
	try:
		get_archived_report_card_pdf(row.name)
	except Exception:
		return (
			"Problem",
			_("The archived PDF is missing, unreadable, or failed its ownership, size, or SHA-256 integrity checks."),
		)
	return (
		"Healthy",
		_("The private archived PDF exists and matches its immutable size and SHA-256 metadata."),
	)


@frappe.whitelist()
def get_report_card_archive_integrity(
	branch: str | None = None,
	publication: str | None = None,
	student: str | None = None,
	search: str | None = None,
	start: int | str | None = 0,
	page_length: int | str | None = DEFAULT_PAGE_LENGTH,
) -> dict:
	"""Audit only the visible page of immutable Report Card Issue PDF artifacts."""
	_require_archive_audit_access()

	resolved_branch = str(branch or "").strip()
	if resolved_branch:
		assert_branch_access(resolved_branch)

	offset = max(cint(start), 0)
	limit = min(max(cint(page_length) or DEFAULT_PAGE_LENGTH, 1), MAX_PAGE_LENGTH)
	filters = {}
	if resolved_branch:
		filters["school_branch"] = resolved_branch
	if publication:
		filters["result_publication"] = str(publication).strip()
	if student:
		filters["student"] = str(student).strip()

	or_filters = None
	needle = str(search or "").strip()
	if needle:
		like = f"%{needle}%"
		or_filters = [
			["name", "like", like],
			["student", "like", like],
			["student_name", "like", like],
			["result_publication", "like", like],
		]

	rows = frappe.get_list(
		ISSUE_DOCTYPE,
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name",
			"result_publication",
			"publication_version",
			"issue_version",
			"student",
			"student_name",
			"school_branch",
			"student_group",
			"issued_on",
			"payload_hash",
			"pdf_sha256",
			"pdf_filename",
			"pdf_size_bytes",
		],
		order_by="issued_on desc, name desc",
		limit_start=offset,
		limit_page_length=limit + 1,
	)
	has_more = len(rows) > limit
	visible = rows[:limit]

	summary = {"healthy": 0, "legacy": 0, "problems": 0}
	output = []
	for row in visible:
		status, detail = _archive_status(row)
		if status == "Healthy":
			summary["healthy"] += 1
		elif status == "Legacy":
			summary["legacy"] += 1
		else:
			summary["problems"] += 1
		output.append(
			{
				"name": row.name,
				"result_publication": row.result_publication,
				"publication_version": int(row.publication_version or 1),
				"issue_version": int(row.issue_version or 1),
				"student": row.student,
				"student_name": row.student_name or row.student,
				"school_branch": row.school_branch,
				"student_group": row.student_group,
				"issued_on": row.issued_on,
				"fingerprint": str(row.payload_hash or "")[:16].upper(),
				"archive_status": status,
				"archive_detail": detail,
			}
		)

	return {
		"rows": output,
		"summary": summary,
		"filters": {
			"branch": resolved_branch,
			"publication": str(publication or "").strip(),
			"student": str(student or "").strip(),
			"search": needle,
		},
		"allowed_branches": [
			{
				"value": row.get("name"),
				"label": row.get("branch_name") or row.get("name"),
			}
			for row in get_allowed_school_branches()
			if row.get("name")
		],
		"start": offset,
		"page_length": limit,
		"has_more": has_more,
	}
