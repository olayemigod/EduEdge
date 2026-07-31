from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


def test_new_sites_use_least_privilege_permission_policy():
	install = (APP / "install.py").read_text()
	policy = (APP / "security" / "permission_policy.py").read_text()

	assert "apply_safe_default_permission_baseline" in install
	assert "apply_default_permission_baseline()" not in install
	for expected in (
		'HIGH_RISK_DEFAULT_RIGHTS = ("delete", "email", "share")',
		"SENSITIVE_DOCTYPES",
		"MANAGED_NON_PLATFORM_ROLES",
		"def harden_sensitive_managed_permissions",
		'frappe.db.set_value("Custom DocPerm"',
		"This function never adds permissions.",
	):
		assert expected in policy


def test_existing_sites_receive_bounded_permission_cleanup_patch():
	patches = (APP / "patches.txt").read_text()
	patch = (APP / "patches" / "v0_9" / "harden_sensitive_role_permissions.py").read_text()

	assert "eduedge.patches.v0_9.harden_sensitive_role_permissions" in patches
	assert "harden_sensitive_managed_permissions" in patch
	assert "apply_default_permission_baseline" not in patch


def test_after_migrate_does_not_regrant_role_permissions():
	install = (APP / "install.py").read_text()
	after_migrate = install.split("def after_migrate()", 1)[1].split("def ensure_roles()", 1)[0]
	assert "apply_safe_default_permission_baseline" not in after_migrate
	assert "apply_default_permission_baseline" not in after_migrate
