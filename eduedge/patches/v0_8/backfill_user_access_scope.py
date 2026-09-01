from __future__ import annotations

import frappe


VALID_SCOPES = {"Company", "Institution", "Branch"}


def execute() -> None:
	if not frappe.db.exists("DocType", "EduEdge User Branch Access"):
		return
	meta = frappe.get_meta("EduEdge User Branch Access")
	if not meta.has_field("access_scope") or not meta.has_field("institution"):
		return

	rows = frappe.get_all(
		"EduEdge User Branch Access",
		fields=[
			"name",
			"access_scope",
			"hq_all_branch_access",
			"company",
			"institution",
			"school_branch",
		],
		limit_page_length=0,
	)
	for row in rows:
		scope = row.access_scope
		company = row.company
		institution = row.institution

		# Preserve legacy HQ records even when schema sync has already populated
		# the new Select field with its default Branch value.
		if row.hq_all_branch_access:
			scope = "Company"
		elif scope not in VALID_SCOPES:
			if institution and not row.school_branch:
				scope = "Institution"
			else:
				scope = "Branch"

		if scope == "Branch" and row.school_branch:
			branch = frappe.db.get_value(
				"EduEdge School Branch",
				row.school_branch,
				["company", "institution"],
				as_dict=True,
			)
			if branch:
				company = branch.company
				institution = branch.institution
		elif scope == "Institution" and institution:
			company = frappe.db.get_value("EduEdge Institution", institution, "company")

		values = {
			"access_scope": scope,
			"company": company,
			"institution": None if scope == "Company" else institution,
			"hq_all_branch_access": 1 if scope == "Company" else 0,
		}
		if scope != "Branch":
			values.update(
				{
					"school_branch": None,
					"branch_name": None,
					"is_default_branch": 0,
					"can_switch_branch": 1,
				}
			)
		frappe.db.set_value(
			"EduEdge User Branch Access",
			row.name,
			values,
			update_modified=False,
		)
