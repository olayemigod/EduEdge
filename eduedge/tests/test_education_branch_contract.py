from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class TestEducationBranchContract(unittest.TestCase):
	def test_custom_fields_target_operational_records_not_guardian(self):
		text = (ROOT / "eduedge" / "education" / "custom_fields.py").read_text()
		self.assertIn('"Student Applicant"', text)
		self.assertIn('"Student"', text)
		self.assertIn('"Program Enrollment"', text)
		self.assertNotIn('"Guardian": [', text)

	def test_program_enrollment_branch_is_read_only(self):
		text = (ROOT / "eduedge" / "education" / "custom_fields.py").read_text()
		program_section = text.split('"Program Enrollment": [', 1)[1]
		self.assertIn('"read_only": 1', program_section)

	def test_hooks_extend_without_overriding_upstream_enrollment_api(self):
		text = (ROOT / "eduedge" / "hooks.py").read_text()
		self.assertIn("doc_events", text)
		self.assertIn("permission_query_conditions", text)
		self.assertNotIn('"education.', text)
		self.assertNotIn('"erpnext.', text)
		self.assertIn('"eduedge.api.resource_center.get_resource_page"', text)

	def test_guardian_scope_is_derived_from_linked_students(self):
		text = (ROOT / "eduedge" / "education" / "permissions.py").read_text()
		self.assertIn("tabGuardian Student", text)
		self.assertIn("tabStudent", text)
		self.assertIn("BRANCH_FIELD", text)


if __name__ == "__main__":
	unittest.main()
