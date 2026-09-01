from __future__ import annotations

import frappe

from eduedge.access_control import build_access_manifest


PRODUCT_DESCRIPTOR = {
	"key": "eduedge",
	"product_key": "eduedge",
	"label": "EduEdge",
	"product": "EduEdge",
	"icon": "graduation",
	"home_route": "/app/eduedge-home",
	"route_patterns": [
		"/app/eduedge*",
		"/app/query-report/EduEdge*",
	],
	"order": 30,
}


def get_product_availability() -> dict | None:
	"""Return EduEdge only when the current Desk user can use an EduEdge route.

	Installation discovers this provider but never grants visibility. The existing
	permission-aware EduEdge access manifest remains authoritative for the user.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		return None
	manifest = build_access_manifest(user)
	if not manifest.get("can_access_eduedge"):
		return None
	return dict(PRODUCT_DESCRIPTOR)
