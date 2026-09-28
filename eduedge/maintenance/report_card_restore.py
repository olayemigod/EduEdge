from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.education.report_card_issues import (
	ISSUE_DOCTYPE,
	inspect_report_card_issue_integrity,
)

DEFAULT_BATCH_SIZE = 25
MAX_BATCH_SIZE = 100
DEFAULT_MAX_PROBLEM_ROWS = 100
MAX_PROBLEM_ROWS = 500


def verify_report_card_restore_integrity(
	batch_size: int | str | None = DEFAULT_BATCH_SIZE,
	max_problem_rows: int | str | None = DEFAULT_MAX_PROBLEM_ROWS,
) -> dict:
	"""Verify every issued Report Card after backup/restore without mutating records.

	This maintenance entrypoint intentionally scans the whole site in bounded batches.
	It is designed for bench execute after restoring the database and private files.
	"""
	page_size = min(max(cint(batch_size) or DEFAULT_BATCH_SIZE, 1), MAX_BATCH_SIZE)
	problem_limit = min(
		max(cint(max_problem_rows) or DEFAULT_MAX_PROBLEM_ROWS, 1),
		MAX_PROBLEM_ROWS,
	)

	total = healthy = legacy = problems = 0
	problem_rows = []
	offset = 0

	while True:
		rows = frappe.get_all(
			ISSUE_DOCTYPE,
			fields=["name"],
			order_by="creation asc, name asc",
			limit_start=offset,
			limit_page_length=page_size,
		)
		if not rows:
			break

		for row in rows:
			total += 1
			check = inspect_report_card_issue_integrity(row.name)
			if check.get("legacy"):
				legacy += 1
			elif check.get("ok"):
				healthy += 1
			else:
				problems += 1
				if len(problem_rows) < problem_limit:
					problem_rows.append(
						{
							"issue": row.name,
							"status": check.get("status") or "Unknown",
							"detail": check.get("detail") or "",
							"payload_status": check.get("payload_status") or "",
							"payload_fingerprint": check.get("payload_fingerprint") or "",
							"pdf_status": check.get("pdf_status") or "",
							"pdf_fingerprint": check.get("pdf_fingerprint") or "",
							"expected_size_bytes": check.get("expected_size_bytes"),
							"actual_size_bytes": check.get("actual_size_bytes"),
						}
					)

		if len(rows) < page_size:
			break
		offset += page_size

	return {
		"status": "PASS" if problems == 0 else "FAIL",
		"total_issues": total,
		"healthy": healthy,
		"legacy": legacy,
		"problems": problems,
		"problem_rows": problem_rows,
		"problem_rows_truncated": problems > len(problem_rows),
		"batch_size": page_size,
		"message": (
			_("Issued Report Card restore verification passed.")
			if problems == 0
			else _("Issued Report Card restore verification found integrity problems.")
		),
	}


def assert_report_card_restore_integrity(
	batch_size: int | str | None = DEFAULT_BATCH_SIZE,
	max_problem_rows: int | str | None = DEFAULT_MAX_PROBLEM_ROWS,
) -> dict:
	"""Fail the restore/upgrade gate when any issued Report Card fails integrity."""
	result = verify_report_card_restore_integrity(
		batch_size=batch_size,
		max_problem_rows=max_problem_rows,
	)
	if result["problems"]:
		preview = "; ".join(
			f'{row["issue"]}: {row["status"]}'
			for row in result["problem_rows"][:10]
		)
		if result["problem_rows_truncated"]:
			preview = f"{preview}; ..."
		frappe.throw(
			_(
				"Issued Report Card restore verification failed for {0} Issue(s). {1}"
			).format(result["problems"], preview or _("Review the integrity audit.")),
			frappe.ValidationError,
		)
	return result
