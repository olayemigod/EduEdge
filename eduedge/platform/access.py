from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

import frappe
from frappe import _

from eduedge.platform.client import get_platform_client
from eduedge.platform.config import get_platform_config
from eduedge.platform.exceptions import EduEdgePlatformError
from eduedge.product_identity import normalize_feature_key


def _cache_key(
	*,
	user: str,
	tenant_key: str,
	feature_key: str | None,
	action: str | None,
) -> str:
	payload = json.dumps(
		{
			"user": user,
			"tenant_key": tenant_key,
			"product": "EduEdge",
			"feature_key": normalize_feature_key(feature_key),
			"action": action or "",
		},
		sort_keys=True,
	)
	return f"eduedge:platform-access:{hashlib.sha256(payload.encode()).hexdigest()}"


def get_eduedge_access_decision(
	*,
	user: str | None = None,
	tenant_key: str | None = None,
	feature_key: str | None = None,
	action: str | None = None,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
) -> dict:
	config = get_platform_config()
	resolved_user = user or frappe.session.user
	resolved_tenant = tenant_key or config.tenant_key
	client = get_platform_client(config)
	if not config.remote_enabled:
		return client.get_access_decision(
			user=resolved_user,
			tenant_key=resolved_tenant,
			feature_key=feature_key,
			action=action,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)

	cache_key = _cache_key(
		user=resolved_user,
		tenant_key=resolved_tenant,
		feature_key=feature_key,
		action=action,
	)
	try:
		decision = client.get_access_decision(
			user=resolved_user,
			tenant_key=resolved_tenant,
			feature_key=feature_key,
			action=action,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)
		frappe.cache().set_value(cache_key, decision, expires_in_sec=config.access_cache_seconds)
		return decision
	except EduEdgePlatformError as exc:
		cached = frappe.cache().get_value(cache_key)
		if isinstance(cached, dict):
			return {**cached, "cached": True, "warnings": [str(exc)]}
		if config.fail_closed or config.required:
			return {
				"allowed": False,
				"enforcement_action": "Block",
				"primary_reason_code": str(exc),
				"reason": _("EduEdge platform access could not be verified."),
				"platform_mode": "remote",
				"feature_key": normalize_feature_key(feature_key),
			}
		return {
			"allowed": True,
			"enforcement_action": "Warn",
			"primary_reason_code": str(exc),
			"reason": _("Platform access could not be verified; local operation is continuing."),
			"warnings": [str(exc)],
			"platform_mode": "remote",
			"feature_key": normalize_feature_key(feature_key),
		}


def has_eduedge_access(**kwargs) -> bool:
	return bool(get_eduedge_access_decision(**kwargs).get("allowed"))


def require_eduedge_access(**kwargs) -> dict:
	decision = get_eduedge_access_decision(**kwargs)
	if not decision.get("allowed"):
		frappe.throw(
			decision.get("reason") or _("EduEdge access is currently blocked."),
			frappe.PermissionError,
			title=_("Platform Access Required"),
		)
	return decision


def guard_eduedge_action(
	feature_key: str,
	*,
	action: str | None = None,
) -> Callable:
	def decorator(function: Callable) -> Callable:
		def wrapped(*args, **kwargs):
			require_eduedge_access(
				feature_key=feature_key,
				action=action or function.__name__,
			)
			return function(*args, **kwargs)

		wrapped.__name__ = function.__name__
		wrapped.__doc__ = function.__doc__
		return wrapped

	return decorator
