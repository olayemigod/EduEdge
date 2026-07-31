from __future__ import annotations

import unittest

from eduedge.permissions_baseline import PLATFORM_MANAGERS
from eduedge.security.permission_audit import get_safe_default_permission_matrix
from eduedge.security.permission_policy import HIGH_RISK_DEFAULT_RIGHTS


class TestPermissionAuditPolicy(unittest.TestCase):
	def test_sensitive_school_roles_do_not_expect_high_risk_rights(self):
		matrix = get_safe_default_permission_matrix()
		high_risk = set(HIGH_RISK_DEFAULT_RIGHTS)
		cases = (
			("Student", "School Administrator"),
			("Student Applicant", "Admission Officer"),
			("Program Enrollment", "Registrar"),
			("Assessment Result", "Academic Administrator"),
			("EduEdge CBT Question", "Education Manager"),
		)
		for doctype, role in cases:
			with self.subTest(doctype=doctype, role=role):
				rights = matrix[doctype][role]
				self.assertTrue({"read", "create", "write"}.issubset(rights))
				self.assertFalse(rights.intersection(high_risk))

	def test_platform_managers_keep_explicit_authority(self):
		matrix = get_safe_default_permission_matrix()
		for role in PLATFORM_MANAGERS:
			with self.subTest(role=role):
				rights = matrix["Student"][role]
				self.assertTrue(set(HIGH_RISK_DEFAULT_RIGHTS).issubset(rights))

	def test_non_sensitive_setup_masters_keep_management_rights(self):
		matrix = get_safe_default_permission_matrix()
		rights = matrix["Program"]["School Administrator"]
		self.assertTrue(set(HIGH_RISK_DEFAULT_RIGHTS).issubset(rights))


if __name__ == "__main__":
	unittest.main()
