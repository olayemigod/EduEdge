from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestCurriculumManagementPageContract(unittest.TestCase):
	def test_page_is_registered_as_an_edgesuite_surface(self):
		page_dir = APP / "eduedge" / "page" / "eduedge_curriculum"
		page = json.loads((page_dir / "eduedge_curriculum.json").read_text(encoding="utf-8"))
		self.assertEqual(page["name"], "eduedge-curriculum")
		self.assertEqual(page["module"], "EduEdge")
		self.assertEqual(page["roles"], [])
		loader = (page_dir / "eduedge_curriculum.js").read_text(encoding="utf-8")
		bundle = (APP / "public" / "js" / "eduedge_curriculum.bundle.js").read_text(encoding="utf-8")
		self.assertLess(loader.index("edgesuite_ui.bundle.js"), loader.index("eduedge_curriculum.bundle.js"))
		self.assertIn("createEduEdgeCurriculumApp", bundle)
		self.assertIn("window.EduEdgeCurriculum", bundle)

	def test_visible_course_title_is_institution_type_driven(self):
		fields = (APP / "education" / "curriculum_fields.py").read_text(encoding="utf-8")
		component = (APP / "public" / "js" / "eduedge_curriculum" / "EduEdgeCurriculum.vue").read_text(encoding="utf-8")
		for token in (
			'"PRIMARY":',
			'"SECONDARY":',
			'"TERTIARY":',
			'"TRAINING_CENTRE":',
			'"course": ("Subject", "Subjects")',
			'"course": ("Course", "Courses")',
			'"course": ("Training Course", "Training Courses")',
		):
			self.assertIn(token, fields)
		self.assertIn('this.term("course", false', component)
		self.assertIn('this.term("course", true', component)
		self.assertIn('this.term("topic", true', component)
		self.assertNotIn('title="Courses & Topics"', component)

	def test_subject_master_is_institution_wide_but_delivery_is_class_aware(self):
		api = (APP / "api" / "curriculum_management.py").read_text(encoding="utf-8")
		component = (APP / "public" / "js" / "eduedge_curriculum" / "EduEdgeCurriculum.vue").read_text(encoding="utf-8")
		for token in (
			"Class / Programme Offering",
			"Class Arm",
			"Institution-wide master",
			"Institution curriculum",
			"Class curriculum",
			"program_offering",
			"student_group",
		):
			self.assertIn(token, component if token in component else api)
		self.assertIn("active_assignment_rows", api)
		self.assertIn("Program Course", api)
		self.assertIn("_program_courses", api)

	def test_assigned_teacher_scope_comes_from_active_class_assignments(self):
		permissions = (APP / "education" / "curriculum_permissions.py").read_text(encoding="utf-8")
		assignments = (APP / "education" / "teaching_assignments.py").read_text(encoding="utf-8")
		api = (APP / "api" / "curriculum_management.py").read_text(encoding="utf-8")
		for token in (
			'"EduEdge Instructor Assignment"',
			'"enabled": 1',
			"valid_from",
			"valid_to",
			"current_user_instructors",
			"Employee",
			"eduedge_email",
			"program_offering",
			"student_group",
			"assigned_courses",
		):
			self.assertIn(token, assignments if token in assignments else permissions)
		self.assertIn("This Subject / Course is not assigned to you for the selected Class or Class Arm.", api)

	def test_course_master_and_native_grading_are_manager_controlled(self):
		api = (APP / "api" / "curriculum_management.py").read_text(encoding="utf-8")
		permissions = (APP / "education" / "curriculum_permissions.py").read_text(encoding="utf-8")
		validation = (APP / "education" / "curriculum_validation.py").read_text(encoding="utf-8")
		component = (APP / "public" / "js" / "eduedge_curriculum" / "EduEdgeCurriculum.vue").read_text(encoding="utf-8")
		for token in (
			"Default Grading Scale",
			"Assessment Criteria",
			"weightage",
			"Assessment Criteria weightage must total 100%.",
			"Only authorised academic managers can change Institution-wide Subject / Course masters and grading governance.",
		):
			self.assertIn(token, component if token in component else api)
		self.assertIn('permission_type in {"create", "write", "delete", "submit", "cancel", "amend", "share", "import"}', permissions)
		self.assertIn("Subject / Course masters and grading governance are controlled by authorised academic managers", validation)
		self.assertIn("in_eduedge_topic_link_update", permissions)
		self.assertNotIn("ignore_permissions", api)
		self.assertNotIn("frappe.db.set_value", api)

	def test_topics_support_institution_class_and_class_arm_scope(self):
		api = (APP / "api" / "curriculum_management.py").read_text(encoding="utf-8")
		fields = (APP / "education" / "curriculum_fields.py").read_text(encoding="utf-8")
		validation = (APP / "education" / "curriculum_validation.py").read_text(encoding="utf-8")
		for token in (
			'frappe.new_doc("Topic")',
			'frappe.get_doc("Topic", name)',
			'course_doc.append("topics", {"topic": topic})',
			'"Course Topic"',
			'TOPIC_COURSE_FIELD = "eduedge_course"',
			'TOPIC_SCOPE_INSTITUTION = "Institution-wide"',
			'TOPIC_SCOPE_CLASS = "Class / Programme Offering"',
			'TOPIC_SCOPE_CLASS_ARM = "Class Arm"',
			'TOPIC_OFFERING_FIELD = "eduedge_program_offering"',
			'TOPIC_GROUP_FIELD = "eduedge_student_group"',
		):
			self.assertIn(token, api if token in api else fields)
		self.assertIn("Assigned teachers cannot create or edit Institution-wide Topics.", validation)
		self.assertIn("Assigned teachers cannot rename a saved Topic or move it to another Subject, Class, or Class Arm.", validation)

	def test_route_navigation_hooks_migration_and_ci_are_registered(self):
		access = (APP / "access_control.py").read_text(encoding="utf-8")
		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text(encoding="utf-8")
		hooks = (APP / "hooks.py").read_text(encoding="utf-8")
		install = (APP / "install.py").read_text(encoding="utf-8")
		patches = (APP / "patches.txt").read_text(encoding="utf-8")
		workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
		self.assertIn('"/app/eduedge-curriculum":', access)
		self.assertIn('menuItem(`${courses} & ${topics}`, "/app/eduedge-curriculum"', navigation)
		self.assertIn('"/app/eduedge-curriculum"', navigation)
		self.assertIn('"Course": "eduedge.education.curriculum_permissions.course_query"', hooks)
		self.assertIn('"Topic": "eduedge.education.curriculum_permissions.topic_query"', hooks)
		self.assertIn('"Topic": {"before_validate": "eduedge.education.curriculum_validation.before_validate_topic"}', hooks)
		self.assertIn("ensure_curriculum_management_foundation()", install)
		self.assertIn("ensure_teaching_assignment_foundation()", install)
		self.assertIn("eduedge.patches.v0_9.add_curriculum_management_permissions", patches)
		self.assertIn("node --check eduedge/public/js/eduedge_curriculum.bundle.js", workflow)
		self.assertIn("node --check eduedge/eduedge/page/eduedge_curriculum/eduedge_curriculum.js", workflow)


if __name__ == "__main__":
	unittest.main()
