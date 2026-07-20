from __future__ import annotations

from typing import Any

import frappe

from eduedge.platform.client import get_platform_client
from eduedge.platform.config import PlatformConfig, get_platform_config
from eduedge.platform.exceptions import EduEdgePlatformError
from eduedge.product_identity import DISPLAY_LABEL, PRODUCT_CODE

DEFAULT_PRODUCT_LOGO = "/assets/eduedge/images/eduedge-mark.svg"
CACHE_PREFIX = "eduedge:platform-runtime"
STALE_CACHE_SECONDS = 86400


def _fresh_cache_key(config: PlatformConfig) -> str:
	return f"{CACHE_PREFIX}:fresh:{config.tenant_key or 'standalone'}:{config.product}"


def _stale_cache_key(config: PlatformConfig) -> str:
	return f"{CACHE_PREFIX}:stale:{config.tenant_key or 'standalone'}:{config.product}"


def _default_context(config: PlatformConfig) -> dict:
	return {
		"tenant_key": config.tenant_key or None,
		"product_code": PRODUCT_CODE,
		"product_name": DISPLAY_LABEL,
		"product_logo": DEFAULT_PRODUCT_LOGO,
		"product_identity_source": "bundled",
		"platform_mode": config.mode,
	}


def _as_dict(value: Any) -> dict:
	return value if isinstance(value, dict) else {}


def _normalize_runtime_context(payload: dict | None, config: PlatformConfig) -> dict:
	payload = _as_dict(payload)
	product = _as_dict(payload.get("product"))
	branding = _as_dict(payload.get("product_branding") or payload.get("branding") or product.get("branding"))
	product_code = str(
		product.get("code")
		or payload.get("product_code")
		or payload.get("product_app")
		or config.product
		or PRODUCT_CODE
	).strip()
	product_name = str(
		branding.get("name")
		or branding.get("display_name")
		or product.get("display_name")
		or product.get("name")
		or payload.get("product_name")
		or DISPLAY_LABEL
	).strip()
	product_logo = str(
		branding.get("logo")
		or branding.get("logo_url")
		or product.get("logo")
		or payload.get("product_logo")
		or DEFAULT_PRODUCT_LOGO
	).strip()
	return {
		**payload,
		"tenant_key": payload.get("tenant_key") or config.tenant_key or None,
		"product_code": product_code or PRODUCT_CODE,
		"product_name": product_name or DISPLAY_LABEL,
		"product_logo": product_logo or DEFAULT_PRODUCT_LOGO,
		"product_identity_source": "coreedge" if config.remote_enabled else "bundled",
		"platform_mode": config.mode,
	}


def refresh_cached_runtime_context(*, user: str | None = None, raise_on_error: bool = False) -> dict:
	"""Fetch CoreEdge runtime context and cache its product identity.

	This function is safe for scheduler and migration use. Browser boot data never
	receives CoreEdge credentials, and a remote outage cannot remove the packaged
	EduEdge identity fallback.
	"""
	config = get_platform_config()
	if not config.remote_enabled or not config.runtime_context_path:
		return _default_context(config)
	try:
		context = get_platform_client(config).get_runtime_context(user=user)
		normalized = _normalize_runtime_context(context, config)
		cache = frappe.cache()
		cache.set_value(
			_fresh_cache_key(config),
			normalized,
			expires_in_sec=config.access_cache_seconds,
		)
		cache.set_value(
			_stale_cache_key(config),
			normalized,
			expires_in_sec=STALE_CACHE_SECONDS,
		)
		return normalized
	except EduEdgePlatformError:
		if raise_on_error:
			raise
	except Exception:
		if raise_on_error:
			raise
	return _default_context(config)


def get_cached_runtime_context(*, user: str | None = None) -> dict:
	"""Return CoreEdge-managed product identity with safe cached fallback."""
	config = get_platform_config()
	if not config.remote_enabled:
		return _default_context(config)
	cache = frappe.cache()
	fresh = cache.get_value(_fresh_cache_key(config))
	if isinstance(fresh, dict):
		return _normalize_runtime_context(fresh, config)
	stale = cache.get_value(_stale_cache_key(config))
	if isinstance(stale, dict):
		try:
			frappe.enqueue(
				"eduedge.platform.runtime_context.refresh_cached_runtime_context",
				queue="short",
				user=user,
				enqueue_after_commit=True,
			)
		except Exception:
			pass
		return _normalize_runtime_context(stale, config)
	return refresh_cached_runtime_context(user=user)


def get_product_identity() -> dict:
	context = get_cached_runtime_context(user=frappe.session.user)
	return {
		"product_code": context.get("product_code") or PRODUCT_CODE,
		"product_name": context.get("product_name") or DISPLAY_LABEL,
		"product_logo": context.get("product_logo") or DEFAULT_PRODUCT_LOGO,
		"source": context.get("product_identity_source") or "bundled",
	}
