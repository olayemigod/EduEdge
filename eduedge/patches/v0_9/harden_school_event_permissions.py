from __future__ import annotations

from eduedge.security.permission_policy import harden_sensitive_managed_permissions


def execute() -> None:
	"""Apply least-privilege cleanup after School Event enters the sensitive set.

	The shared hardening routine is idempotent and only removes delete/email/share
	from known EduEdge-managed non-platform roles. It does not add permissions or
	change custom roles outside the managed baseline.
	"""
	harden_sensitive_managed_permissions()
