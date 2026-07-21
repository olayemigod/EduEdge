from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from functools import wraps

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
	decision_type: str = "runtime",
) -> str:
	payload = json.dumps(
		{
			"user": user,
			"tenant_key": tenant_key,
			"product": "EduEdge",
			"feature_key": normalize_feature_key(feature_key),
			"action": action or "",
			"decision_type": decision_type,
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
	"""Evaluate normal EduEdge product/runtime access.

	This contract remains separate from optional action-level service grants so a
	missing public-exam capability cannot block ordinary school operations.
	"""
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
		decision_type="runtime",
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


def get_eduedge_capability_decision(
	*,
	user: str | None = None,
	tenant_key: str | None = None,
	feature_key: str | None = None,
	action: str | None = None,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
) -> dict:
	"""Evaluate an optional CoreEdge service capability.

	Capabilities always fail closed after the bounded cached decision expires,
	even when ordinary product-runtime access is configured to warn/fail open.
	"""
	config = get_platform_config()
	resolved_user = user or frappe.session.user
	resolved_tenant = tenant_key or config.tenant_key
	if not config.remote_enabled:
		return {
			"allowed": False,
			"enforcement_action": "Block",
			"primary_reason_code": "REMOTE_FEATURE_ACCESS_NOT_CONFIGURED",
			"reason": _("CoreEdge feature access is not configured for this site."),
			"platform_mode": config.mode,
			"feature_key": normalize_feature_key(feature_key),
		}

	client = get_platform_client(config)
	cache_key = _cache_key(
		user=resolved_user,
		tenant_key=resolved_tenant,
		feature_key=feature_key,
		action=action,
		decision_type="capability",
	)
	try:
		decision = client.get_feature_access_decision(
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
		return {
			"allowed": False,
			"enforcement_action": "Block",
			"primary_reason_code": str(exc),
			"reason": _("CoreEdge feature access could not be verified."),
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
		@wraps(function)
		def wrapped(*args, **kwargs):
			# Frappe includes the RPC method name as `cmd` in request arguments.
			# Remove the transport-only value before calling the business function.
			kwargs.pop("cmd", None)
			require_eduedge_access(
				feature_key=feature_key,
				action=action or function.__name__,
			)
			return function(*args, **kwargs)

		return wrapped

	return decorator
