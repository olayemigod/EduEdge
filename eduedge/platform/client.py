from __future__ import annotations

from eduedge.platform.config import PlatformConfig, get_platform_config
from eduedge.platform.local_client import LocalPlatformClient
from eduedge.platform.remote_client import RemoteCoreEdgeClient


def get_platform_client(
	config: PlatformConfig | None = None,
	*,
	transport=None,
):
	resolved = config or get_platform_config()
	if resolved.remote_enabled:
		return RemoteCoreEdgeClient(resolved, transport=transport)
	return LocalPlatformClient(resolved)
