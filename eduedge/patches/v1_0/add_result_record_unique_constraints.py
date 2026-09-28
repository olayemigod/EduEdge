from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint


CONSTRAINTS = (
	(
		"EduEdge Published Result Snapshot",
		["result_publication", "student"],
		"uniq_eduedge_snapshot_publication_student",
	),
	(
		"EduEdge Report Card Issue",
		["result_publication", "student", "issue_version"],
		"uniq_eduedge_issue_publication_student_version",
	),
	(
		"EduEdge Report Card Review",
		["result_publication", "student"],
		"uniq_eduedge_review_publication_student",
	),
)


def execute() -> None:
	for doctype, fields, constraint_name in CONSTRAINTS:
		if not frappe.db.exists("DocType", doctype):
			continue
		_assert_no_duplicates(doctype, fields)
		if not _constraint_exists(doctype, constraint_name):
			frappe.db.add_unique(doctype, fields, constraint_name=constraint_name)


def _assert_no_duplicates(doctype: str, fields: list[str]) -> None:
	rows = frappe.get_all(
		doctype,
		fields=[
			*fields,
			{"COUNT": "name", "as": "total"},
		],
		group_by=", ".join(fields),
		limit_page_length=0,
	)
	duplicate = next((row for row in rows if cint(row.total) > 1), None)
	if not duplicate:
		return
	identity = ", ".join(f"{field}={duplicate.get(field)}" for field in fields)
	frappe.throw(
		_(
			"Duplicate {0} records exist for {1}. Resolve the duplicate records before migration."
		).format(doctype, identity),
		frappe.ValidationError,
	)

def _constraint_exists(doctype: str, constraint_name: str) -> bool:
	table = f"tab{doctype}"
	rows = frappe.db.sql(
		f"show index from `{table}` where Key_name = %s",
		(constraint_name,),
		as_dict=True,
	)
	return bool(rows)
