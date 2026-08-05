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

	def test_teacher_scope_comes_from_active_instructor_assignments(self):
		permissions = (APP / "education" / "curriculum_permissions.py").read_text(encoding="utf-8")
		for token in (
			'"EduEdge Instructor Assignment"',
			'"enabled": 1',
			'"course": ["is", "set"]',
			"valid_from",
			"valid_to",
			"current_user_instructors",
			"Employee",
			"eduedge_email",
			"This Course / Subject is not actively assigned to you.",
		):
			self.assertIn(token, permissions if token != "This Course / Subject is not actively assigned to you." else (APP / "api" / "curriculum_management.py").read_text(encoding="utf-8"))

	def test_teacher_cannot_create_course_identity_or_manage_unassigned_topics(self):
		api = (APP / "api" / "curriculum_management.py").read_text(encoding="utf-8")
		permissions = (APP / "education" / "curriculum_permissions.py").read_text(encoding="utf-8")
		for token in (
			"Only authorised academic managers can create a new Course / Subject.",
			"You can manage Topics only for Courses / Subjects actively assigned to you.",
			"Course / Subject and Branch must belong to the same Institution.",
			"Department / School Section must belong to the selected Institution.",
		):
			self.assertIn(token, api)
		self.assertIn('permission_type in {"create", "delete", "submit", "cancel", "amend"}', permissions)
		self.assertNotIn("ignore_permissions", api)
		self.assertNotIn("frappe.db.set_value", api)

	def test_topics_use_native_records_and_course_topic_links(self):
		api = (APP / "api" / "curriculum_management.py").read_text(encoding="utf-8")
		fields = (APP / "education" / "curriculum_fields.py").read_text(encoding="utf-8")
		for token in (
			'frappe.new_doc("Topic")',
			'frappe.get_doc("Topic", name)',
			'course_doc.append("topics", {"topic": topic})',
			'"Course Topic"',
			'TOPIC_COURSE_FIELD = "eduedge_course"',
		):
			self.assertIn(token, api if token != 'TOPIC_COURSE_FIELD = "eduedge_course"' else fields)

	def test_route_navigation_hooks_permissions_patch_and_ci_are_registered(self):
		access = (APP / "access_control.py").read_text(encoding="utf-8")
		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text(encoding="utf-8")
		hooks = (APP / "hooks.py").read_text(encoding="utf-8")
		patches = (APP / "patches.txt").read_text(encoding="utf-8")
		workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
		self.assertIn('"/app/eduedge-curriculum":', access)
		self.assertIn('menuItem(`${courses} & ${topics}`, "/app/eduedge-curriculum"', navigation)
		self.assertIn('"/app/eduedge-curriculum"', navigation)
		self.assertIn('"Course": "eduedge.education.curriculum_permissions.course_query"', hooks)
		self.assertIn('"Topic": "eduedge.education.curriculum_permissions.topic_query"', hooks)
		self.assertIn('"Topic": {"before_validate": "eduedge.education.curriculum_validation.before_validate_topic"}', hooks)
		self.assertIn("eduedge.patches.v0_9.add_curriculum_management_permissions", patches)
		self.assertIn("node --check eduedge/public/js/eduedge_curriculum.bundle.js", workflow)
		self.assertIn("node --check eduedge/eduedge/page/eduedge_curriculum/eduedge_curriculum.js", workflow)


if __name__ == "__main__":
	unittest.main()
