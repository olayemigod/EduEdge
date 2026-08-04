from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestClassArmsPageContract(unittest.TestCase):
	def test_page_is_registered_as_an_edgesuite_surface(self):
		page_json = APP / "eduedge" / "page" / "eduedge_class_arms" / "eduedge_class_arms.json"
		page = json.loads(page_json.read_text(encoding="utf-8"))
		self.assertEqual(page["name"], "eduedge-class-arms")
		self.assertEqual(page["module"], "EduEdge")
		self.assertEqual(page["roles"], [])

		loader = (page_json.parent / "eduedge_class_arms.js").read_text(encoding="utf-8")
		bundle = (APP / "public" / "js" / "eduedge_class_arms.bundle.js").read_text(encoding="utf-8")
		self.assertLess(loader.index("edgesuite_ui.bundle.js"), loader.index("eduedge_class_arms.bundle.js"))
		self.assertIn("createEduEdgeClassArmsApp", bundle)
		self.assertIn("window.EduEdgeClassArms", bundle)

	def test_manager_uses_native_student_group_truth(self):
		api = (APP / "api" / "class_arms.py").read_text(encoding="utf-8")
		for token in (
			'frappe.get_list(\n\t\t"Student Group"',
			'frappe.new_doc("Student Group")',
			'doc.append(\n\t\t\t"students"',
			'doc.append("instructors"',
			"doc.save()",
			'require_eduedge_access(feature_key="academics", action="save_class_arm")',
		):
			self.assertIn(token, api)
		self.assertNotIn("ignore_permissions", api)
		self.assertNotIn("frappe.db.set_value", api)

	def test_options_are_branch_offering_enrollment_and_assignment_scoped(self):
		api = (APP / "api" / "class_arms.py").read_text(encoding="utf-8")
		for token in (
			"assert_branch_access",
			'"school_branch": branch, "is_active": 1, "enrollment_enabled": 1',
			'"docstatus": 1',
			'enrollment_filters[OFFERING_FIELD] = context.name',
			'filters={"school_branch": branch, "enabled": 1}',
			'_assert_unique(student_rows, "student", _("Student"))',
			'_assert_unique(instructor_rows, "instructor", _("Instructor"))',
		):
			self.assertIn(token, api)

	def test_page_supports_context_cascade_rosters_and_full_form_fallback(self):
		component = (APP / "public" / "js" / "eduedge_class_arms" / "EduEdgeClassArms.vue").read_text(encoding="utf-8")
		for token in (
			"draftBranchChanged",
			"draftOfferingChanged",
			"applyOfferingContext",
			"Only enabled students with submitted enrollment in this exact Programme Offering and Branch",
			"Instructor Branch Assignment",
			"toggleStudent",
			"toggleInstructor",
			"save_class_arm",
			"openFullForm",
		):
			self.assertIn(token, component)

	def test_academic_operations_uses_edgesuite_class_arm_workflow(self):
		component = (APP / "public" / "js" / "eduedge_academic_operations" / "EduEdgeAcademicOperations.vue").read_text(encoding="utf-8")
		self.assertIn('@action="openClassArms(true)"', component)
		self.assertIn("Manage {{ term('student_group', true, 'Class Arms') }}", component)
		self.assertIn("/app/eduedge-class-arms", component)
		self.assertNotIn("/app/student-group/new-student-group", component)
		self.assertIn("canCreateStudentGroup() { return Boolean(this.permissions.can_create_student_group); }", component)

	def test_access_manifest_registers_class_arms_route(self):
		access = (APP / "access_control.py").read_text(encoding="utf-8")
		self.assertIn('"/app/eduedge-class-arms": (("student_group", "read"),)', access)

	def test_ci_checks_class_arm_entries(self):
		workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
		self.assertIn("node --check eduedge/public/js/eduedge_class_arms.bundle.js", workflow)
		self.assertIn("node --check eduedge/eduedge/page/eduedge_class_arms/eduedge_class_arms.js", workflow)


if __name__ == "__main__":
	unittest.main()
