import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
DOCTYPE_ROOT = APP / "eduedge/doctype/eduedge_question_responsibility_assignment"
PAGE_ROOT = APP / "eduedge/page/eduedge_question_responsibilities"


class TestQuestionResponsibilityContract(unittest.TestCase):
	def test_doctype_defines_scoped_action_flags_and_management_permissions(self):
		metadata = json.loads(
			(DOCTYPE_ROOT / "eduedge_question_responsibility_assignment.json").read_text(encoding="utf-8")
		)
		self.assertEqual(metadata["name"], "EduEdge Question Responsibility Assignment")
		fields = {row["fieldname"]: row for row in metadata["fields"]}
		for fieldname in (
			"user",
			"institution",
			"school_branch",
			"course",
			"can_author",
			"can_subject_review",
			"can_final_approve",
			"enabled",
			"valid_from",
			"valid_to",
		):
			self.assertIn(fieldname, fields)
		self.assertEqual(fields["school_branch"]["reqd"] if "reqd" in fields["school_branch"] else 0, 0)
		roles = {row["role"] for row in metadata["permissions"]}
		self.assertIn("School Administrator", roles)
		self.assertIn("Academic Administrator", roles)
		self.assertNotIn("Teacher", roles)
		self.assertNotIn("Instructor", roles)

	def test_validation_locks_scope_dates_flags_and_one_user_course_assignment(self):
		source = (
			DOCTYPE_ROOT / "eduedge_question_responsibility_assignment.py"
		).read_text(encoding="utf-8")
		for expected in (
			"Select an enabled System User",
			"Select an enabled Institution",
			"does not belong to this Institution",
			"belongs to another Institution",
			"Select at least one Question responsibility",
			"Valid To cannot be earlier than Valid From",
			'"user": self.user',
			'"course": self.course',
			"assert_responsibility_scope_access",
		):
			self.assertIn(expected, source)
		for forbidden in ("add_roles", "remove_roles", "Has Role", "insert_ignore_permissions"):
			self.assertNotIn(forbidden, source)

	def test_matching_service_requires_active_exact_scope_assignments(self):
		source = (APP / "cbt/question_responsibilities.py").read_text(encoding="utf-8")
		for expected in (
			"RESPONSIBILITY_FIELDS",
			"permitted_responsibility_scope",
			"assert_responsibility_scope_access",
			"assignment_is_active",
			"get_matching_question_responsibilities",
			'"user": user',
			'"institution": institution',
			'"course": course',
			'"enabled": 1',
			"assignment_branch != (school_branch or",
			"can_subject_review",
			"can_final_approve",
		):
			self.assertIn(expected, source)
		self.assertNotIn("frappe.get_roles(user)[0]", source)

	def test_management_api_is_permission_and_scope_aware(self):
		source = (APP / "api/question_responsibilities.py").read_text(encoding="utf-8")
		for expected in (
			'_require_permission("read")',
			"permitted_responsibility_scope",
			"assert_responsibility_scope_access",
			"resolve_question_governance",
			"require_eduedge_access",
			'fieldname == "school_branch"',
			'fieldname == "course"',
			'filters["eduedge_institution"] = selected_institution',
			"set_enabled",
		):
			self.assertIn(expected, source)
		for forbidden in ("ignore_permissions=True", "frappe.db.sql(", "add_roles", "remove_roles"):
			self.assertNotIn(forbidden, source)

	def test_edgesuite_page_is_registered_and_uses_quick_editor(self):
		page = json.loads((PAGE_ROOT / "eduedge_question_responsibilities.json").read_text(encoding="utf-8"))
		self.assertEqual(page["name"], "eduedge-question-responsibilities")
		self.assertEqual(page["roles"], [])
		loader = (PAGE_ROOT / "eduedge_question_responsibilities.js").read_text(encoding="utf-8")
		bundle = (APP / "public/js/eduedge_question_responsibilities.bundle.js").read_text(encoding="utf-8")
		component = (
			APP / "public/js/eduedge_question_responsibilities/EduEdgeQuestionResponsibilities.vue"
		).read_text(encoding="utf-8")
		self.assertLess(loader.index("edgesuite_ui.bundle.js"), loader.index("eduedge_question_responsibilities.bundle.js"))
		self.assertIn("createEduEdgeQuestionResponsibilitiesApp", bundle)
		for expected in (
			"<EdgeAppShell",
			"<EdgeFormDialog",
			"<EdgeModal",
			"Question Author",
			"Subject Reviewer",
			"Final Approver",
			"All Institution Branches",
			"eduedge.api.question_responsibilities.save_assignment",
			"eduedge.api.question_responsibilities.search_options",
		):
			self.assertIn(expected, component)
		self.assertIn("does not add or remove Frappe roles", component)

	def test_navigation_access_and_ci_include_question_responsibilities(self):
		navigation = (APP / "public/js/eduedge_ui/navigation.js").read_text(encoding="utf-8")
		access = (APP / "access_control.py").read_text(encoding="utf-8")
		workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
		for source in (navigation, access):
			self.assertIn("/app/eduedge-question-responsibilities", source)
		self.assertIn(
			'"question_responsibility_assignment": "EduEdge Question Responsibility Assignment"',
			access,
		)
		self.assertIn("node --check eduedge/public/js/eduedge_question_responsibilities.bundle.js", workflow)
		self.assertIn(
			"node --check eduedge/eduedge/page/eduedge_question_responsibilities/eduedge_question_responsibilities.js",
			workflow,
		)


if __name__ == "__main__":
	unittest.main()
