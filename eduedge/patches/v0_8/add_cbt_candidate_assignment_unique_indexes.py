from __future__ import annotations

import frappe
from frappe import _

DOCTYPE = "EduEdge CBT Candidate Assignment"
TABLE = "tabEduEdge CBT Candidate Assignment"
INDEXES = (
	("uniq_cbt_schedule_student", ["exam_schedule", "student"], "student"),
	(
		"uniq_cbt_schedule_public_candidate",
		["exam_schedule", "public_candidate_reference"],
		"public_candidate_reference",
	),
)


def execute() -> None:
	if not frappe.db.exists("DocType", DOCTYPE):
		return
	for index_name, fields, identity_field in INDEXES:
		_assert_no_duplicates(identity_field)
		if not _index_exists(index_name):
			frappe.db.add_unique(DOCTYPE, fields, constraint_name=index_name)


def _assert_no_duplicates(identity_field: str) -> None:
	rows = frappe.get_all(
		DOCTYPE,
		filters=[[identity_field, "is", "set"]],
		fields=["exam_schedule", identity_field, "count(name) as total"],
		group_by=f"exam_schedule, {identity_field}",
		having="count(name) > 1",
		limit_page_length=1,
	)
	if rows:
		row = rows[0]
		frappe.throw(
			_(
				"Duplicate CBT Candidate Assignments exist for Schedule {0} and candidate identity {1}. Resolve them before migration."
			).format(row.exam_schedule, row.get(identity_field)),
			frappe.ValidationError,
		)


def _index_exists(index_name: str) -> bool:
	rows = frappe.db.sql(
		f"show index from `{TABLE}` where Key_name = %s",
		(index_name,),
		as_dict=True,
	)
	return bool(rows)
