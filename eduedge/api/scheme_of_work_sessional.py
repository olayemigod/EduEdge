from __future__ import annotations

import frappe
from frappe import _

from eduedge.api import scheme_of_work as base
from eduedge.platform.access import require_eduedge_access

EDITABLE_FIELDS = (*base.EDITABLE_FIELDS, "academic_term")


@frappe.whitelist(methods=["POST"])
def save_scheme(payload) -> dict:
	"""Save a Scheme whose Offering/Class Arm is sessional but whose curriculum period is a Term.

	Existing draft authorization is performed before caller-controlled context is applied.
	The DocType controller resolves the selected Term through the Institution Academic
	Calendar and derives immutable period dates server-side.
	"""
	require_eduedge_access(feature_key="academics", action="save_scheme_of_work")
	data = base._parse_payload(payload)
	name = str(data.get("name") or "").strip()
	if name:
		doc = frappe.get_doc(base.SCHEME_DOCTYPE, name)
		if doc.status != "Draft":
			frappe.throw(
				_("Approved Schemes of Work are immutable. Create a new version instead."),
				frappe.ValidationError,
			)
		# Authorise the original record before accepting caller-controlled academic
		# context, preserving the horizontal-authorization protection.
		base._context_authorized(doc, write=True)
	else:
		doc = frappe.new_doc(base.SCHEME_DOCTYPE)
		doc.version_no = 1

	for fieldname in EDITABLE_FIELDS:
		if fieldname in data:
			doc.set(fieldname, data.get(fieldname))
	if "items" in data:
		doc.set("items", [])
		for item in data.get("items") or []:
			doc.append("items", {fieldname: item.get(fieldname) for fieldname in base.ITEM_FIELDS})

	# Validate once before governed authorization so Branch, Offering, Term and
	# calendar-derived period dates are canonical before assignment checks run.
	doc.run_method("validate")
	base._context_authorized(doc, write=True)
	if doc.is_new():
		doc.insert(ignore_permissions=not base._is_manager())
	else:
		doc.save(ignore_permissions=not base._is_manager())
	return base._serialize(doc)
