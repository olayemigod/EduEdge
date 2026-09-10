from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from eduedge.platform.config import PlatformConfig
from eduedge.platform.exceptions import (
	RemoteAuthenticationFailed,
	RemoteContractNotConfigured,
	RemotePlatformUnavailable,
	RemoteResponseInvalid,
)
from eduedge.product_identity import resolve_product_identity

Transport = Callable[[str, dict, dict, int], dict]


class RemoteCoreEdgeClient:
	def __init__(self, config: PlatformConfig, transport: Transport | None = None):
		self.config = config
		self.transport = transport or self._http_transport

	def get_health(self) -> dict:
		if not self.config.health_path:
			return {
				"available": False,
				"platform_mode": "remote",
				"primary_reason_code": "REMOTE_CONTRACT_NOT_CONFIGURED",
			}
		return self._request(self.config.health_path, {"site_identifier": self.config.site_identifier})

	def get_runtime_context(self, user: str | None = None) -> dict:
		if not self.config.runtime_context_path:
			raise RemoteContractNotConfigured("REMOTE_CONTRACT_NOT_CONFIGURED")
		return self._request(
			self.config.runtime_context_path,
			{
				"user": user,
				"tenant_key": self.config.tenant_key,
				"site_identifier": self.config.site_identifier,
			},
		)

	def get_access_decision(
		self,
		*,
		user: str | None = None,
		tenant_key: str | None = None,
		feature_key: str | None = None,
		action: str | None = None,
		reference_doctype: str | None = None,
		reference_name: str | None = None,
	) -> dict:
		if not self.config.access_decision_path:
			raise RemoteContractNotConfigured("REMOTE_CONTRACT_NOT_CONFIGURED")
		identity, payload = self._build_access_payload(
			user=user,
			tenant_key=tenant_key,
			feature_key=feature_key,
			action=action,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)
		response = self._request(self.config.access_decision_path, payload)
		return self._normalize_access_decision(response, feature_key=identity["feature_key"])

	def get_feature_access_decision(
		self,
		*,
		user: str | None = None,
		tenant_key: str | None = None,
		feature_key: str | None = None,
		action: str | None = None,
		reference_doctype: str | None = None,
		reference_name: str | None = None,
	) -> dict:
		if not self.config.feature_access_decision_path:
			raise RemoteContractNotConfigured("REMOTE_FEATURE_CONTRACT_NOT_CONFIGURED")
		identity, payload = self._build_access_payload(
			user=user,
			tenant_key=tenant_key,
			feature_key=feature_key,
			action=action,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)
		response = self._request(self.config.feature_access_decision_path, payload)
		return self._normalize_access_decision(response, feature_key=identity["feature_key"])

	def _build_access_payload(
		self,
		*,
		user: str | None,
		tenant_key: str | None,
		feature_key: str | None,
		action: str | None,
		reference_doctype: str | None,
		reference_name: str | None,
	) -> tuple[dict, dict]:
		identity = resolve_product_identity(
			tenant_key=tenant_key or self.config.tenant_key,
			feature_key=feature_key,
		)
		return identity, {
			"site_identifier": self.config.site_identifier,
			"user": user,
			"tenant_key": tenant_key or self.config.tenant_key,
			"product_code": identity["product_code"],
			"product_family": identity["product_family"],
			"distribution": identity["distribution"],
			"feature_key": identity["feature_key"],
			"action": action,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
		}

	def _request(self, path: str, payload: dict) -> dict:
		if not self.config.base_url:
			raise RemoteContractNotConfigured("REMOTE_CONTRACT_NOT_CONFIGURED")
		if not self.config.secure_transport:
			raise RemoteContractNotConfigured("INSECURE_REMOTE_TRANSPORT")
		url = f"{self.config.base_url}/{path.lstrip('/')}"
		headers = {
			"Accept": "application/json",
			"Content-Type": "application/json",
			"X-CoreEdge-Tenant": self.config.tenant_key,
			"X-CoreEdge-Client": self.config.client_id,
			"Authorization": f"token {self.config.client_id}:{self.config.client_secret}",
		}
		try:
			response = self.transport(url, payload, headers, self.config.timeout_seconds)
		except RemoteAuthenticationFailed:
			raise
		except RemotePlatformUnavailable:
			raise
		except Exception as exc:
			raise RemotePlatformUnavailable("REMOTE_PLATFORM_UNAVAILABLE") from exc
		if not isinstance(response, dict):
			raise RemoteResponseInvalid("REMOTE_RESPONSE_INVALID")
		return response.get("message") if isinstance(response.get("message"), dict) else response

	@staticmethod
	def _normalize_access_decision(response: dict, *, feature_key: str | None) -> dict:
		decision = response.get("access") if isinstance(response.get("access"), dict) else response
		allowed = decision.get("allowed")
		action = decision.get("enforcement_action")
		reason_code = decision.get("primary_reason_code")
		if not isinstance(allowed, bool) or action not in {"Allow", "Warn", "Block"} or not reason_code:
			raise RemoteResponseInvalid("REMOTE_RESPONSE_INVALID")
		return {
			"allowed": allowed,
			"enforcement_action": action,
			"primary_reason_code": str(reason_code),
			"reason": str(decision.get("reason") or ""),
			"warnings": list(decision.get("warnings") or []),
			"platform_mode": "remote",
			"feature_key": feature_key,
		}

	@staticmethod
	def _http_transport(url: str, payload: dict, headers: dict, timeout: int) -> dict:
		request = urllib.request.Request(
			url,
			data=json.dumps(payload).encode("utf-8"),
			headers=headers,
			method="POST",
		)
		try:
			with urllib.request.urlopen(request, timeout=timeout) as response:
				body = response.read().decode("utf-8")
		except urllib.error.HTTPError as exc:
			if exc.code in {401, 403}:
				raise RemoteAuthenticationFailed("REMOTE_AUTHENTICATION_FAILED") from exc
			raise RemotePlatformUnavailable("REMOTE_PLATFORM_UNAVAILABLE") from exc
		except (urllib.error.URLError, TimeoutError) as exc:
			raise RemotePlatformUnavailable("REMOTE_PLATFORM_UNAVAILABLE") from exc
		try:
			parsed: Any = json.loads(body)
		except json.JSONDecodeError as exc:
			raise RemoteResponseInvalid("REMOTE_RESPONSE_INVALID") from exc
		if not isinstance(parsed, dict):
			raise RemoteResponseInvalid("REMOTE_RESPONSE_INVALID")
		return parsed
