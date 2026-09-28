from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from eduedge.education.offerings import assert_branch_access
from eduedge.education.report_card_issues import (
	ISSUE_DOCTYPE,
	inspect_report_card_issue_integrity,
)
from eduedge.services.branch_context import (
	get_allowed_school_branches,
	get_current_school_branch,
)

MAX_ARCHIVE_AUDIT_PAGE_LENGTH = 25
DEFAULT_ARCHIVE_AUDIT_PAGE_LENGTH = 10
ARCHIVE_AUDITOR_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
}


def _require_archive_auditor() -> None:
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	if not ARCHIVE_AUDITOR_ROLES.intersection(frappe.get_roles(user)):
		frappe.throw(_("You are not permitted to audit issued report-card archives."), frappe.PermissionError)
	if not frappe.has_permission(ISSUE_DOCTYPE, "read"):
		frappe.throw(_("You are not permitted to read issued report cards."), frappe.PermissionError)


def _resolve_branch(branch: str | None = None) -> str:
	resolved = str(branch or "").strip()
	if resolved:
		assert_branch_access(resolved)
		return resolved
	current = get_current_school_branch() or {}
	current_name = str(current.get("name") or "").strip()
	if current_name:
		assert_branch_access(current_name)
		return current_name
	return ""


@frappe.whitelist()
def get_report_card_archive_integrity(
	branch: str | None = None,
	publication: str | None = None,
	student: str | None = None,
	search: str | None = None,
	start: int | str | None = 0,
	page_length: int | str | None = DEFAULT_ARCHIVE_AUDIT_PAGE_LENGTH,
) -> dict:
	"""Verify immutable payload plus exact PDF bytes for one permission-aware page of Issues."""
	_require_archive_auditor()
	resolved_branch = _resolve_branch(branch)
	page_size = min(
		max(cint(page_length) or DEFAULT_ARCHIVE_AUDIT_PAGE_LENGTH, 1),
		MAX_ARCHIVE_AUDIT_PAGE_LENGTH,
	)
	offset = max(cint(start) or 0, 0)
	filters = {}
	if resolved_branch:
		filters["school_branch"] = resolved_branch
	resolved_publication = str(publication or "").strip()
	resolved_student = str(student or "").strip()
	needle = str(search or "").strip()
	if resolved_publication:
		filters["result_publication"] = resolved_publication
	if resolved_student:
		filters["student"] = resolved_student
	or_filters = None
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
			"pdf_sha256",
			"pdf_filename",
			"pdf_size_bytes",
		],
		order_by="issued_on desc, creation desc",
		limit_start=offset,
		limit_page_length=page_size + 1,
	)
	has_more = len(rows) > page_size
	rows = rows[:page_size]

	audited = []
	for row in rows:
		check = inspect_report_card_issue_integrity(row.name)
		audited.append(
			{
				**dict(row),
				"archive_status": check["status"],
				"archive_ok": bool(check["ok"]),
				"archive_legacy": bool(check["legacy"]),
				"archive_detail": check["detail"],
				"payload_status": check.get("payload_status") or "",
				"payload_ok": bool(check.get("payload_ok")),
				"payload_fingerprint": check.get("payload_fingerprint") or "",
				"pdf_status": check.get("pdf_status") or check.get("status") or "",
				"pdf_ok": bool(check.get("pdf_ok")),
				"pdf_fingerprint": check.get("pdf_fingerprint") or "",
				"expected_size_bytes": check.get("expected_size_bytes"),
				"actual_size_bytes": check.get("actual_size_bytes"),
			}
		)

	healthy = sum(1 for row in audited if row["archive_status"] == "Healthy")
	legacy = sum(1 for row in audited if row["archive_legacy"])
	attention = len(audited) - healthy - legacy
	return {
		"branch": resolved_branch,
		"filters": {
			"branch": resolved_branch,
			"publication": resolved_publication,
			"student": resolved_student,
			"search": needle,
		},
		"checked_on": str(now_datetime()),
		"checked_by": frappe.session.user,
		"allowed_branches": get_allowed_school_branches(),
		"rows": audited,
		"summary": {
			"checked": len(audited),
			"healthy": healthy,
			"needs_attention": attention,
			"legacy": legacy,
		},
		"start": offset,
		"page_length": page_size,
		"has_more": has_more,
		"scope_note": _("Integrity counts apply to the Issues checked on this page."),
	}
