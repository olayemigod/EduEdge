from __future__ import annotations

import frappe

from eduedge.education import institution_types as registry

SCHOOL_TERM_OVERRIDES = {
	"PRIMARY": {
		"class_session": ("Period", "Periods"),
	},
	"SECONDARY": {
		"class_session": ("Period", "Periods"),
	},
}


def apply_institution_type_defaults() -> None:
	"""Apply approved EduEdge terminology defaults after the protected registry seed."""
	for code, terms in SCHOOL_TERM_OVERRIDES.items():
		definition = registry.INSTITUTION_TYPE_SEEDS.get(code)
		if definition:
			definition["terms"].update(terms)

	# Re-run the idempotent registry writer with the approved in-memory defaults.
	registry.ensure_institution_types()
	frappe.clear_cache(doctype="EduEdge Institution Type")
