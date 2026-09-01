from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cstr

from eduedge.api.question_batch import (
	QUESTION_DOCTYPE,
	_build_question_doc,
	_decode_upload,
	_duplicate_codes,
	_normalise_common,
	_parse_payload,
	_parse_upload,
	_require_import_permission,
)


@frappe.whitelist()
def import_question_upload(file_name: str, file_content: str, common) -> dict:
	"""Re-parse and revalidate the original upload before creating Draft questions."""
	_require_import_permission()
	common_values = _normalise_common(_parse_payload(common))
	rows = _parse_upload(file_name, _decode_upload(file_content))
	within_batch, existing = _duplicate_codes(rows)
	if within_batch:
		frappe.throw(
			_("Duplicate Question Codes in this file: {0}").format(", ".join(sorted(within_batch))),
			frappe.ValidationError,
		)
	if existing:
		frappe.throw(
			_("These Question Codes already exist: {0}").format(", ".join(sorted(existing))),
			frappe.ValidationError,
		)

	docs = []
	for position, row in enumerate(rows, start=1):
		row_number = row.get("_row_number") or position + 1
		try:
			doc = _build_question_doc(common_values, row, upload=True)
			doc.run_method("validate")
		except frappe.PermissionError:
			raise
		except Exception as exc:
			frappe.throw(
				_("Upload row {0}: {1}").format(row_number, cstr(exc)),
				frappe.ValidationError,
			)
		docs.append(doc)

	created = []
	for doc in docs:
		doc.insert()
		created.append(doc.name)
	frappe.msgprint(
		_("{0} Draft question(s) imported successfully.").format(len(created)),
		alert=True,
		indicator="green",
	)
	return {
		"created": created,
		"count": len(created),
		"status": "Draft",
		"doctype": QUESTION_DOCTYPE,
	}
