from __future__ import annotations

from eduedge.platform.config import PlatformConfig
from eduedge.product_identity import normalize_feature_key, resolve_product_identity


class LocalPlatformClient:
	def __init__(self, config: PlatformConfig):
		self.config = config

	def get_health(self) -> dict:
		return {
			"available": True,
			"platform_mode": "standalone",
			"primary_reason_code": "PLATFORM_DISABLED",
		}

	def get_runtime_context(self, user: str | None = None) -> dict:
		identity = resolve_product_identity(tenant_key=self.config.tenant_key or None)
		return {
			"user": user,
			"tenant_key": self.config.tenant_key or None,
			"product_app": identity["product_app"],
			"active_product_app": identity["active_product_app"],
			"product_family": identity["product_family"],
			"distribution": identity["distribution"],
			"platform_mode": "standalone",
			"warnings": [],
			"blockers": [],
		}

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
		return {
			"allowed": True,
			"enforcement_action": "Allow",
			"primary_reason_code": "PLATFORM_DISABLED",
			"platform_mode": "standalone",
			"feature_key": normalize_feature_key(feature_key),
		}
