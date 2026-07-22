import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SEEDER_PATH = ROOT / "eduedge" / "testing" / "qa_users.py"


class TestQAUserSeederContract(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.source = SEEDER_PATH.read_text()
		cls.tree = ast.parse(cls.source)

	def test_seeder_is_development_only_and_not_whitelisted(self):
		self.assertIn('frappe.conf.get("developer_mode")', self.source)
		self.assertIn('frappe.conf.get("allow_tests")', self.source)
		self.assertIn("frappe.PermissionError", self.source)
		self.assertNotIn("@frappe.whitelist", self.source)

	def test_seeder_uses_frappe_documents_not_raw_sql(self):
		self.assertIn('"doctype": "User"', self.source)
		self.assertIn('frappe.new_doc(BRANCH_ACCESS_DOCTYPE)', self.source)
		self.assertIn('frappe.get_doc(BRANCH_ACCESS_DOCTYPE, name)', self.source)
		self.assertNotIn("frappe.db.sql", self.source)
		self.assertNotIn("INSERT INTO", self.source.upper())

	def test_subject_coordinator_permissions_are_exact_and_non_reviewer(self):
		self.assertIn('CUSTOM_ROLE = "Subject Coordinator"', self.source)
		self.assertIn(
			'desired_rights = {"read", "create", "write", "report", "print"}',
			self.source,
		)
		self.assertIn('int(permission_type in desired_rights)', self.source)
		self.assertIn('"delete"', self.source)
		self.assertIn('"import"', self.source)
		self.assertIn('"share"', self.source)

	def test_expected_qa_roles_and_users_are_present(self):
		for role in (
			"School Administrator",
			"Academic Administrator",
			"Teacher",
			"CBT Invigilator",
			"Registrar",
			"Bursar",
			"Subject Coordinator",
		):
			self.assertIn(role, self.source)
		for email in (
			"qa.school.admin@example.com",
			"qa.academic.admin@example.com",
			"qa.teacher@example.com",
			"qa.invigilator@example.com",
			"qa.registrar@example.com",
			"qa.bursar@example.com",
			"qa.subject.coordinator@example.com",
		):
			self.assertIn(email, self.source)

	def test_branch_selection_is_safe_and_assignments_are_idempotent(self):
		self.assertIn("More than one enabled EduEdge School Branch exists", self.source)
		self.assertIn('frappe.db.exists(BRANCH_ACCESS_DOCTYPE, filters)', self.source)
		self.assertIn("is_default_branch = 1", self.source)
		self.assertIn("can_switch_branch = 0", self.source)
		self.assertIn("frappe.db.commit()", self.source)


if __name__ == "__main__":
	unittest.main()
