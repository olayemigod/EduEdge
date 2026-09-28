from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.education.offerings import assert_branch_access
from eduedge.education.report_card_issues import (
	ISSUE_DOCTYPE,
	inspect_report_card_pdf_archive,
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
	start: int | str | None = 0,
	page_length: int | str | None = DEFAULT_ARCHIVE_AUDIT_PAGE_LENGTH,
) -> dict:
	"""Verify exact PDF bytes for one permission-aware page of immutable Issues."""
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

	rows = frappe.get_list(
		ISSUE_DOCTYPE,
		filters=filters,
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
		check = inspect_report_card_pdf_archive(row.name)
		audited.append(
			{
				**dict(row),
				"archive_status": check["status"],
				"archive_ok": bool(check["ok"]),
				"archive_legacy": bool(check["legacy"]),
				"archive_detail": check["detail"],
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
