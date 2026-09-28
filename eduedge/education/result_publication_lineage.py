from __future__ import annotations

import frappe
from frappe import _

PUBLICATION_DOCTYPE = "EduEdge Result Publication"

PUBLICATION_LINEAGE_FIELDS = [
	"name",
	"title",
	"school_branch",
	"student_group",
	"academic_year",
	"academic_term",
	"assessment_group",
	"result_profile",
	"result_mode",
	"publication_version",
	"supersedes_publication",
	"status",
	"report_card_ready",
	"published_on",
]
PUBLICATION_LINEAGE_SCOPE_FIELDS = (
	"school_branch",
	"student_group",
	"academic_year",
	"academic_term",
	"assessment_group",
	"result_profile",
	"result_mode",
)


def get_published_publication_lineage(publication: str) -> list:
	"""Resolve one exact Published Result Publication revision chain.

	Lineage is defined only by supersedes_publication. Matching scope fields alone never
	create lineage. Corrupt or ambiguous chains fail closed.
	"""

	def load_published(name: str):
		row = frappe.db.get_value(
			PUBLICATION_DOCTYPE,
			name,
			PUBLICATION_LINEAGE_FIELDS,
			as_dict=True,
		)
		if not row or row.status != "Published" or not row.report_card_ready:
			frappe.throw(
				_("Result Publication lineage contains a non-published or unavailable revision."),
				frappe.ValidationError,
			)
		return row

	selected = load_published(publication)

	def validate_scope(row) -> None:
		for fieldname in PUBLICATION_LINEAGE_SCOPE_FIELDS:
			if (row.get(fieldname) or "") != (selected.get(fieldname) or ""):
				frappe.throw(
					_("Result Publication lineage scope is inconsistent."),
					frappe.ValidationError,
				)

	current = selected
	visited = set()
	while current.supersedes_publication:
		if current.name in visited:
			frappe.throw(_("Result Publication lineage contains a cycle."), frappe.ValidationError)
		visited.add(current.name)
		parent = load_published(current.supersedes_publication)
		validate_scope(parent)
		if int(current.publication_version or 1) != int(parent.publication_version or 1) + 1:
			frappe.throw(_("Result Publication lineage version sequence is invalid."), frappe.ValidationError)
		current = parent

	lineage = []
	visited = set()
	while current:
		if current.name in visited:
			frappe.throw(_("Result Publication lineage contains a cycle."), frappe.ValidationError)
		visited.add(current.name)
		validate_scope(current)
		lineage.append(current)
		children = frappe.get_all(
			PUBLICATION_DOCTYPE,
			filters={
				"supersedes_publication": current.name,
				"status": "Published",
				"report_card_ready": 1,
			},
			fields=PUBLICATION_LINEAGE_FIELDS,
			order_by="publication_version asc, published_on asc",
			page_length=2,
		)
		if len(children) > 1:
			frappe.throw(_("Result Publication lineage has multiple published successors."), frappe.ValidationError)
		if not children:
			break
		child = children[0]
		validate_scope(child)
		if int(child.publication_version or 1) != int(current.publication_version or 1) + 1:
			frappe.throw(_("Result Publication lineage version sequence is invalid."), frappe.ValidationError)
		current = child

	if selected.name not in {row.name for row in lineage}:
		frappe.throw(_("Selected Result Publication is outside its resolved lineage."), frappe.ValidationError)
	return lineage
