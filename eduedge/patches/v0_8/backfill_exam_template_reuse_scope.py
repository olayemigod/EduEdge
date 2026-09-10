from __future__ import annotations

import frappe

from eduedge.eduedge.doctype.eduedge_cbt_exam_template.eduedge_cbt_exam_template import (
	MODE_BLUEPRINT,
	MODE_FIXED,
	PUBLIC_EXAM,
	REUSE_BRANCH,
	REUSE_UNIVERSAL,
	SUBJECT_ANY,
	SUBJECT_SPECIFIC,
)

TEMPLATE_DOCTYPE = "EduEdge CBT Exam Template"


def execute() -> None:
	if not frappe.db.exists("DocType", TEMPLATE_DOCTYPE):
		return

	rows = frappe.get_all(
		TEMPLATE_DOCTYPE,
		fields=[
			"name",
			"exam_scope",
			"school_branch",
			"course",
			"template_reuse_scope",
			"company",
			"institution",
			"template_mode",
			"subject_applicability",
			"exam_purpose",
		],
	)
	for row in rows:
		values: dict[str, object] = {}
		if not row.exam_purpose:
			values["exam_purpose"] = "Other"
		if not row.subject_applicability:
			values["subject_applicability"] = SUBJECT_SPECIFIC if row.course else SUBJECT_ANY
		if not row.template_mode:
			values["template_mode"] = MODE_FIXED if row.course else MODE_BLUEPRINT

		if row.exam_scope == PUBLIC_EXAM:
			if row.template_reuse_scope != REUSE_UNIVERSAL:
				values["template_reuse_scope"] = REUSE_UNIVERSAL
			values["company"] = None
			values["institution"] = None
			values["school_branch"] = None
		elif row.school_branch:
			branch = frappe.db.get_value(
				"EduEdge School Branch",
				row.school_branch,
				["company", "institution"],
				as_dict=True,
			)
			values["template_reuse_scope"] = REUSE_BRANCH
			if branch:
				values["company"] = branch.company
				values["institution"] = branch.institution

		if values:
			frappe.db.set_value(TEMPLATE_DOCTYPE, row.name, values, update_modified=False)
