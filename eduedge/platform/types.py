from __future__ import annotations

from typing import NotRequired, TypedDict


class AccessDecision(TypedDict):
	allowed: bool
	enforcement_action: str
	primary_reason_code: str
	reason: NotRequired[str]
	warnings: NotRequired[list[str]]
	platform_mode: NotRequired[str]
	cached: NotRequired[bool]
	feature_key: NotRequired[str | None]
