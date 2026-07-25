from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class TestAcademicOperationsContract(unittest.TestCase):
	def test_operational_doctypes_receive_branch_fields(self):
		text = (ROOT / "eduedge" / "education" / "custom_fields.py").read_text()
		for doctype in ("Student Group", "Room", "Course Schedule", "Student Attendance"):
			self.assertIn(f'"{doctype}": [', text)

	def test_instructor_is_many_to_many_by_assignment(self):
		text = (
			ROOT
			/ "eduedge"
			/ "eduedge"
			/ "doctype"
			/ "eduedge_instructor_branch_assignment"
			/ "eduedge_instructor_branch_assignment.json"
		).read_text()
		self.assertIn('"instructor"', text)
		self.assertIn('"school_branch"', text)
		self.assertNotIn('"Instructor": [', (ROOT / "eduedge" / "education" / "custom_fields.py").read_text())

	def test_attendance_submission_does_not_mutate_submitted_records(self):
		text = (ROOT / "eduedge" / "api" / "academic_operations.py").read_text()
		self.assertIn("Submitted attendance cannot be changed", text)
		self.assertIn('current["locked"]', text)
		self.assertNotIn("db_set(", text)

	def test_aggregate_queries_use_frappe_v16_function_dicts(self):
		text = (ROOT / "eduedge" / "api" / "academic_operations.py").read_text()
		self.assertIn('{"COUNT": "name", "as": "student_count"}', text)
		self.assertIn('{"COUNT": "name", "as": "record_count"}', text)
		self.assertNotIn("count(name) as student_count", text)
		self.assertNotIn("count(name) as record_count", text)

	def test_academic_operations_page_uses_edgesuite_shell(self):
		component = (
			ROOT
			/ "eduedge"
			/ "public"
			/ "js"
			/ "eduedge_academic_operations"
			/ "EduEdgeAcademicOperations.vue"
		).read_text()
		loader = (
			ROOT
			/ "eduedge"
			/ "eduedge"
			/ "page"
			/ "eduedge_academic_operations"
			/ "eduedge_academic_operations.js"
		).read_text()
		self.assertIn("<EdgeAppShell", component)
		self.assertIn("<EdgePageLayout", component)
		self.assertLess(
			loader.index("edgesuite_ui.bundle.js"),
			loader.index("eduedge_academic_operations.bundle.js"),
		)
		self.assertNotIn('frappe.require("edgeui.bundle.js"', loader)

	def test_hooks_scope_academic_records_by_branch(self):
		hooks = (ROOT / "eduedge" / "hooks.py").read_text()
		for doctype in ("Student Group", "Room", "Course Schedule", "Student Attendance"):
			self.assertIn(f'"{doctype}"', hooks)
		self.assertIn("permission_query_conditions", hooks)
		self.assertIn("has_permission", hooks)


if __name__ == "__main__":
	unittest.main()
