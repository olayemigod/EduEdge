from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

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
	# Frappe's query-builder-backed get_all rejects raw SQL aggregate strings.
	# Use the supported aggregate dictionary syntax and filter grouped totals
	# in Python before creating the unique index.
	rows = frappe.get_all(
		DOCTYPE,
		filters=[[identity_field, "is", "set"]],
		fields=[
			"exam_schedule",
			identity_field,
			{"COUNT": "name", "as": "total"},
		],
		group_by=f"exam_schedule, {identity_field}",
		limit_page_length=0,
	)
	duplicate = next((row for row in rows if cint(row.total) > 1), None)
	if duplicate:
		frappe.throw(
			_(
				"Duplicate CBT Candidate Assignments exist for Schedule {0} and candidate identity {1}. Resolve them before migration."
			).format(duplicate.exam_schedule, duplicate.get(identity_field)),
			frappe.ValidationError,
		)


def _index_exists(index_name: str) -> bool:
	rows = frappe.db.sql(
		f"show index from `{TABLE}` where Key_name = %s",
		(index_name,),
		as_dict=True,
	)
	return bool(rows)
