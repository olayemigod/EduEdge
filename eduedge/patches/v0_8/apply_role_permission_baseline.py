from __future__ import annotations

from eduedge.permissions_baseline import (
	apply_default_permission_baseline,
	ensure_eduedge_page_role_baseline,
)


def execute() -> None:
	apply_default_permission_baseline()
	ensure_eduedge_page_role_baseline()
