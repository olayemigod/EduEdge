from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
AUDIT_SOURCE = (ROOT / "security" / "permission_audit.py").read_text(encoding="utf-8")
POLICY_SOURCE = (ROOT / "security" / "permission_policy.py").read_text(encoding="utf-8")
BASELINE_SOURCE = (ROOT / "permissions_baseline.py").read_text(encoding="utf-8")


class TestPermissionAuditPolicy(unittest.TestCase):
	def test_sources_compile_without_loading_frappe(self):
		compile(AUDIT_SOURCE, "permission_audit.py", "exec")
		compile(POLICY_SOURCE, "permission_policy.py", "exec")

	def test_audit_uses_hardened_matrix(self):
		self.assertIn("def get_safe_default_permission_matrix", AUDIT_SOURCE)
		self.assertIn("rights.difference_update(HIGH_RISK_DEFAULT_RIGHTS)", AUDIT_SOURCE)
		self.assertIn("matrix = get_safe_default_permission_matrix()", AUDIT_SOURCE)
		self.assertIn('"audit_policy": "least_privilege_v1"', AUDIT_SOURCE)

	def test_sensitive_school_rights_are_audited_as_unsafe(self):
		self.assertIn("MANAGED_NON_PLATFORM_ROLES", AUDIT_SOURCE)
		self.assertIn("SENSITIVE_DOCTYPES", AUDIT_SOURCE)
		self.assertIn("rights.intersection(high_risk)", AUDIT_SOURCE)
		self.assertIn("unsafe_rights", AUDIT_SOURCE)
		for right in ("delete", "email", "share"):
			self.assertIn(f'"{right}"', POLICY_SOURCE)

	def test_platform_authority_remains_explicit(self):
		self.assertIn("PLATFORM_MANAGERS", AUDIT_SOURCE)
		self.assertIn('"platform_managers": list(PLATFORM_MANAGERS)', AUDIT_SOURCE)
		self.assertIn('"EduEdge Super Administrator"', BASELINE_SOURCE)


if __name__ == "__main__":
	unittest.main()
