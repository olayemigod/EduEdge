from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlparse

SUPPORTED_MODES = {"standalone", "remote"}
LEGACY_REMOTE_MODES = {"shared_hosted", "white_label"}
LOCAL_DEVELOPMENT_HOSTS = {"localhost", "127.0.0.1", "::1"}

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off", ""}


def parse_bool(value: Any, default: bool = False) -> bool:
	if value is None:
		return default
	if isinstance(value, bool):
		return value
	if isinstance(value, int):
		return value != 0
	text = str(value).strip().lower()
	if text in _TRUE_VALUES:
		return True
	if text in _FALSE_VALUES:
		return False
	return default


def parse_positive_int(value: Any, default: int, *, minimum: int = 1, maximum: int = 3600) -> int:
	try:
		parsed = int(value)
	except (TypeError, ValueError):
		return default
	return parsed if minimum <= parsed <= maximum else default


def normalize_mode(value: Any, default: str = "remote") -> str:
	text = str(value or "").strip().lower()
	if not text:
		return default if default in SUPPORTED_MODES else "remote"
	if text in LEGACY_REMOTE_MODES:
		return "remote"
	if text not in SUPPORTED_MODES:
		return "remote"
	return text


def _candidate_host(value: Any) -> str:
	text = str(value or "").strip()
	if not text:
		return ""
	parsed = urlparse(text if "://" in text else f"//{text}")
	return (parsed.hostname or text.split("/", 1)[0].split(":", 1)[0]).lower()


def is_local_development(values: Mapping[str, Any] | None = None) -> bool:
	values = values or {}
	if parse_bool(values.get("developer_mode"), default=False):
		return True
	for key in ("site_name", "coreedge_site_identifier", "host_name"):
		host = _candidate_host(values.get(key))
		if host in LOCAL_DEVELOPMENT_HOSTS or host.endswith(".local") or host.endswith(".localhost"):
			return True
	return False


def is_secure_remote_url(value: str) -> bool:
	"""Require HTTPS except for explicit local development hosts."""
	if not value:
		return False
	parsed = urlparse(value)
	host = (parsed.hostname or "").lower()
	if parsed.scheme == "https":
		return bool(host)
	if parsed.scheme != "http":
		return False
	return host in LOCAL_DEVELOPMENT_HOSTS or host.endswith(".local")


@dataclass(frozen=True, slots=True)
class PlatformConfig:
	mode: str = "remote"
	product: str = "EduEdge"
	required: bool = True
	base_url: str = ""
	tenant_key: str = ""
	site_identifier: str = ""
	client_id: str = ""
	client_secret: str = ""
	fail_closed: bool = True
	local_development: bool = False
	timeout_seconds: int = 8
	access_cache_seconds: int = 300
	health_path: str = ""
	runtime_context_path: str = ""
	access_decision_path: str = ""
	feature_access_decision_path: str = ""

	@classmethod
	def from_mapping(cls, values: Mapping[str, Any] | None = None) -> "PlatformConfig":
		values = values or {}
		local_development = is_local_development(values)
		default_mode = "standalone" if local_development else "remote"
		mode = normalize_mode(values.get("edge_platform_mode"), default=default_mode)
		default_required = mode == "remote"
		required = parse_bool(values.get("coreedge_required"), default=default_required)
		fail_closed = parse_bool(
			values.get("coreedge_fail_closed"),
			default=required or mode == "remote",
		)
		return cls(
			mode=mode,
			product=str(values.get("edge_platform_product") or "EduEdge").strip() or "EduEdge",
			required=required,
			base_url=str(values.get("coreedge_base_url") or "").strip().rstrip("/"),
			tenant_key=str(values.get("coreedge_tenant_key") or "").strip(),
			site_identifier=str(
				values.get("coreedge_site_identifier")
				or values.get("site_name")
				or values.get("host_name")
				or ""
			).strip(),
			client_id=str(values.get("coreedge_client_id") or "").strip(),
			client_secret=str(values.get("coreedge_client_secret") or "").strip(),
			fail_closed=fail_closed,
			local_development=local_development,
			timeout_seconds=parse_positive_int(values.get("coreedge_timeout_seconds"), 8, maximum=120),
			access_cache_seconds=parse_positive_int(
				values.get("coreedge_access_cache_seconds"),
				300,
				maximum=3600,
			),
			health_path=str(values.get("coreedge_health_path") or "").strip(),
			runtime_context_path=str(values.get("coreedge_runtime_context_path") or "").strip(),
			access_decision_path=str(values.get("coreedge_access_decision_path") or "").strip(),
			feature_access_decision_path=str(
				values.get("coreedge_feature_access_decision_path") or ""
			).strip(),
		)

	@property
	def remote_enabled(self) -> bool:
		return self.mode == "remote"

	@property
	def secure_transport(self) -> bool:
		return is_secure_remote_url(self.base_url)

	def readiness(self) -> dict:
		blockers: list[str] = []
		warnings: list[str] = []
		if self.required and not self.remote_enabled:
			blockers.append("CoreEdge is required but the site is configured in standalone mode.")
		if self.mode == "standalone" and not self.local_development:
			warnings.append("Standalone platform mode is enabled outside local development.")
		if self.remote_enabled:
			if not self.base_url:
				blockers.append("CoreEdge base URL is not configured.")
			elif not self.secure_transport:
				blockers.append("CoreEdge base URL must use HTTPS outside local development.")
			if not self.tenant_key:
				blockers.append("CoreEdge tenant key is not configured.")
			if not self.site_identifier:
				blockers.append("CoreEdge product-site identifier is not configured.")
			if not self.client_id or not self.client_secret:
				blockers.append("CoreEdge client credentials are incomplete.")
			if not self.runtime_context_path:
				message = "CoreEdge runtime-context contract path is not configured."
				(blockers if self.required else warnings).append(message)
			if not self.access_decision_path:
				message = "CoreEdge remote runtime-access contract path is not configured."
				(blockers if self.required else warnings).append(message)
			if not self.feature_access_decision_path:
				warnings.append("CoreEdge feature-access contract path is not configured.")
			if not self.health_path:
				warnings.append("CoreEdge health contract path is not configured.")
		return {
			"ready": not blockers,
			"blockers": blockers,
			"warnings": warnings,
		}

	def sanitized(self) -> dict:
		return {
			"mode": self.mode,
			"product": self.product,
			"required": self.required,
			"local_development": self.local_development,
			"base_url_configured": bool(self.base_url),
			"secure_transport": self.secure_transport,
			"tenant_key_configured": bool(self.tenant_key),
			"site_identifier_configured": bool(self.site_identifier),
			"client_id_configured": bool(self.client_id),
			"client_secret_configured": bool(self.client_secret),
			"fail_closed": self.fail_closed,
			"timeout_seconds": self.timeout_seconds,
			"access_cache_seconds": self.access_cache_seconds,
			"runtime_context_configured": bool(self.runtime_context_path),
			"runtime_access_contract_configured": bool(self.access_decision_path),
			"feature_access_contract_configured": bool(self.feature_access_decision_path),
			**self.readiness(),
		}


def get_platform_config() -> PlatformConfig:
	import frappe

	values = dict(frappe.conf)
	values.setdefault("site_name", getattr(frappe.local, "site", ""))
	return PlatformConfig.from_mapping(values)
