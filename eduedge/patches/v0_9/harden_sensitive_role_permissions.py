from eduedge.security.permission_policy import harden_sensitive_managed_permissions


def execute() -> None:
	harden_sensitive_managed_permissions()
