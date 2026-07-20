from __future__ import annotations

import frappe

from eduedge.platform.access import get_eduedge_access_decision
from eduedge.platform.client import get_platform_client
from eduedge.platform.config import get_platform_config
from eduedge.platform.runtime_context import get_product_identity, refresh_cached_runtime_context


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw("Authentication required.", frappe.PermissionError)


@frappe.whitelist()
def get_platform_status() -> dict:
	_require_login()
	config = get_platform_config()
	client = get_platform_client(config)
	return {
		"configuration": config.sanitized(),
		"health": client.get_health(),
		"product_identity": get_product_identity(),
	}


@frappe.whitelist()
def refresh_platform_runtime_context() -> dict:
	_require_login()
	frappe.only_for(("System Manager", "EduEdge Administrator"))
	context = refresh_cached_runtime_context(user=frappe.session.user, raise_on_error=True)
	return {
		"tenant_key": context.get("tenant_key"),
		"product_code": context.get("product_code"),
		"product_name": context.get("product_name"),
		"product_logo": context.get("product_logo"),
		"product_identity_source": context.get("product_identity_source"),
		"platform_mode": context.get("platform_mode"),
	}


@frappe.whitelist()
def get_my_access_decision(
	feature_key: str | None = None,
	action: str | None = None,
) -> dict:
	_require_login()
	return get_eduedge_access_decision(
		user=frappe.session.user,
		feature_key=feature_key,
		action=action,
	)
