from __future__ import annotations

import frappe

from eduedge.api import modal_records as base
from eduedge.platform.access import require_eduedge_access

RESOURCE_FEATURES = {
	"school_branch": "school_branch",
	"program_offering": "academics",
	"user_branch_access": "school_branch",
	"instructor_branch_assignment": "academics",
}


def _feature_key(resource: str) -> str:
	return RESOURCE_FEATURES.get(str(resource or "").strip(), "foundation")


@frappe.whitelist()
def save_modal_record(
	resource: str,
	values: str | dict,
	name: str | None = None,
	context: str | dict | None = None,
) -> dict:
	config = base._resource(resource)
	require_eduedge_access(
		feature_key=_feature_key(resource),
		action="update_quick_record" if name else "create_quick_record",
		reference_doctype=config.get("doctype"),
		reference_name=name,
	)
	return base.save_modal_record(
		resource=resource,
		values=values,
		name=name,
		context=context,
	)
