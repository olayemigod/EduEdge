from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestStudentEnrollmentsPageContract(unittest.TestCase):
	def test_page_is_registered_as_an_edgesuite_surface(self):
		page_json = APP / "eduedge" / "page" / "eduedge_student_enrollments" / "eduedge_student_enrollments.json"
		page = json.loads(page_json.read_text(encoding="utf-8"))
		self.assertEqual(page["name"], "eduedge-student-enrollments")
		self.assertEqual(page["module"], "EduEdge")
		self.assertEqual(page["roles"], [])

		loader = (page_json.parent / "eduedge_student_enrollments.js").read_text(encoding="utf-8")
		bundle = (APP / "public" / "js" / "eduedge_student_enrollments.bundle.js").read_text(encoding="utf-8")
		self.assertLess(loader.index("edgesuite_ui.bundle.js"), loader.index("eduedge_student_enrollments.bundle.js"))
		self.assertIn("createEduEdgeStudentEnrollmentsApp", bundle)
		self.assertIn("window.EduEdgeStudentEnrollments", bundle)

	def test_api_preserves_native_enrollment_truth_and_submitted_immutability(self):
		api = (APP / "api" / "student_enrollments.py").read_text(encoding="utf-8")
		for token in (
			'frappe.new_doc("Program Enrollment")',
			'doc = frappe.get_doc("Program Enrollment", name)',
			"if doc.docstatus != 0:",
			"Submitted or cancelled Enrollments cannot be edited.",
			"doc.save()",
			"doc.submit()",
			'require_eduedge_access(feature_key="academics", action="save_student_enrollment")',
		):
			self.assertIn(token, api)
		self.assertNotIn("ignore_permissions", api)
		self.assertNotIn("frappe.db.set_value", api)

	def test_api_enforces_branch_institution_offering_duplicate_and_capacity_context(self):
		api = (APP / "api" / "student_enrollments.py").read_text(encoding="utf-8")
		for token in (
			"assert_branch_access(branch)",
			'"is_active": 1, "enrollment_enabled": 1',
			"Student, Branch and Programme Offering must belong to the same Institution.",
			'OFFERING_FIELD: offering',
			'"docstatus": ["<", 2]',
			"count_capacity_consuming_enrollments",
			"A Student may enroll across Campuses only within the same Institution.",
		):
			self.assertIn(token, api)

	def test_page_supports_draft_submit_context_and_fee_warning(self):
		component = (APP / "public" / "js" / "eduedge_student_enrollments" / "EduEdgeStudentEnrollments.vue").read_text(encoding="utf-8")
		for token in (
			"Save Draft",
			"Submit Enrollment",
			"Programme Offering",
			"Academic Session",
			"Term / Semester",
			"Batch / Cohort",
			"may create configured fee records",
			"immediately makes the Student eligible for the matching Class Arm",
			"Promotion or transfer must use a separate controlled workflow",
		):
			self.assertIn(token, component)

	def test_student_page_links_selected_student_to_enrollment_workflow(self):
		component = (APP / "public" / "js" / "eduedge_students" / "EduEdgeStudents.vue").read_text(encoding="utf-8")
		self.assertIn("View Enrollments", component)
		self.assertIn("Enroll Student", component)
		self.assertIn("/app/eduedge-student-enrollments", component)
		self.assertIn("resources?.program_enrollment", component)
		self.assertIn('params.get("student")', component)

	def test_access_navigation_and_ci_register_enrollment_page(self):
		access = (APP / "access_control.py").read_text(encoding="utf-8")
		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text(encoding="utf-8")
		workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
		self.assertIn('"program_enrollment": "Program Enrollment"', access)
		self.assertIn('"/app/eduedge-student-enrollments": (("program_enrollment", "read"),)', access)
		self.assertIn('menuItem(__("Student Enrollments"), "/app/eduedge-student-enrollments"', navigation)
		self.assertIn('"/app/eduedge-student-enrollments"', navigation)
		self.assertIn("node --check eduedge/public/js/eduedge_student_enrollments.bundle.js", workflow)
		self.assertIn("node --check eduedge/eduedge/page/eduedge_student_enrollments/eduedge_student_enrollments.js", workflow)


if __name__ == "__main__":
	unittest.main()
