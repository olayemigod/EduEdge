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

	@classmethod
	def assignment(cls, name):
		for node in cls.tree.body:
			if not isinstance(node, ast.Assign):
				continue
			if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
				return ast.literal_eval(node.value)
		raise AssertionError(f"Assignment {name} was not found")

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

	def test_subject_coordinator_question_permissions_are_exact_and_non_reviewer(self):
		self.assertEqual(self.assignment("CUSTOM_ROLE"), "Subject Coordinator")
		self.assertEqual(
			self.assignment("QUESTION_RIGHTS"),
			{"read", "create", "write", "report", "print"},
		)
		self.assertIn('_set_exact_role_permissions(QUESTION_DOCTYPE, QUESTION_RIGHTS, role=CUSTOM_ROLE)', self.source)
		for permission_type in ("delete", "import", "share"):
			self.assertIn(permission_type, self.assignment("MANAGED_PERMISSION_TYPES"))
			self.assertNotIn(permission_type, self.assignment("QUESTION_RIGHTS"))

	def test_subject_coordinator_gets_only_read_on_question_link_dependencies(self):
		self.assertEqual(self.assignment("QUESTION_SUPPORT_DOCTYPES"), ("Course", "Topic"))
		self.assertIn("for doctype in QUESTION_SUPPORT_DOCTYPES", self.source)
		self.assertIn('_set_exact_role_permissions(doctype, {"read"}, role=CUSTOM_ROLE)', self.source)
		self.assertNotIn("EduEdge School Branch", self.assignment("QUESTION_SUPPORT_DOCTYPES"))

	def test_curriculum_viewer_is_explicitly_read_only(self):
		self.assertEqual(self.assignment("CURRICULUM_VIEWER_ROLE"), "QA Curriculum Viewer")
		rights = self.assignment("CURRICULUM_VIEWER_RIGHTS")
		for doctype in (
			"Program",
			"Course",
			"Department",
			"EduEdge Institution",
			"EduEdge Program Offering",
			"EduEdge School Branch",
		):
			self.assertEqual(rights[doctype], {"read"})
		self.assertIn("_ensure_curriculum_viewer_role()", self.source)
		self.assertIn("role=CURRICULUM_VIEWER_ROLE", self.source)

	def test_expected_qa_roles_and_users_are_present(self):
		for role in (
			"School Administrator",
			"Academic Administrator",
			"Teacher",
			"CBT Invigilator",
			"Registrar",
			"Bursar",
			"Subject Coordinator",
			"QA Curriculum Viewer",
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
			"qa.curriculum.viewer@example.com",
		):
			self.assertIn(email, self.source)

	def test_browser_phase_coordination_is_returned_by_seed_and_readiness(self):
		phases = self.assignment("BROWSER_QA_PHASES")
		self.assertGreaterEqual(len(phases), 8)
		self.assertTrue(any(row["user"] == "qa.curriculum.viewer@example.com" for row in phases))
		self.assertTrue(any(row["user"] == "qa.academic.admin@example.com" for row in phases))
		self.assertIn('"browser_qa_phases": list(BROWSER_QA_PHASES)', self.source)
		self.assertIn("def readiness(", self.source)

	def test_branch_selection_is_safe_and_assignments_are_idempotent(self):
		self.assertIn("More than one enabled EduEdge School Branch exists", self.source)
		self.assertIn('frappe.db.exists(BRANCH_ACCESS_DOCTYPE, filters)', self.source)
		self.assertIn("is_default_branch = 1", self.source)
		self.assertIn("can_switch_branch = 0", self.source)
		self.assertIn("frappe.db.commit()", self.source)


if __name__ == "__main__":
	unittest.main()
