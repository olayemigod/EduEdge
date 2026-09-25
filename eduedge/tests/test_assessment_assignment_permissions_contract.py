from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAssessmentAssignmentPermissionsContract(unittest.TestCase):
    def _source(self):
        return (APP / "education" / "assessment_permissions.py").read_text(encoding="utf-8")

    def test_permission_queries_preserve_branch_behavior_until_enforcement_is_enabled(self):
        source = self._source()
        for token in (
            "branch_assessment_plan_query(resolved_user)",
            "branch_assessment_result_query(resolved_user)",
            "if not assignment_capability_enforcement_enabled() or not is_limited_instructor_user(resolved_user):",
            "return branch_condition",
        ):
            self.assertIn(token, source)

    def test_read_queries_require_view_content_on_exact_plan_subject_context(self):
        source = self._source()
        for token in (
            'capability="can_view_subject_content"',
            "assignment.school_branch =",
            "assignment.program_offering = student_group",
            "assignment.course =",
            "assignment.valid_from is null",
            "assignment.valid_to is null",
            "from `tabEduEdge Instructor Branch Assignment` eligibility",
            "eligibility.instructor = assignment.instructor",
            "eligibility.school_branch =",
            "eligibility.enabled = 1",
            "eligibility.valid_from is null",
            "eligibility.valid_to is null",
            "assignment.assignment_scope",
            "CLASS_SCOPE",
            "CLASS_ARM_SCOPE",
            "assignment.student_group =",
        ):
            self.assertIn(token, source)

    def test_list_query_requires_branch_eligibility_on_same_effective_date(self):
        source = self._source()
        helper = source.split("def _assignment_exists_sql", 1)[1].split(
            "def assessment_plan_query", 1
        )[0]
        self.assertIn("from `tabEduEdge Instructor Branch Assignment` eligibility", helper)
        self.assertIn("eligibility.instructor = assignment.instructor", helper)
        self.assertIn("eligibility.school_branch = {branch_expr}", helper)
        self.assertIn("eligibility.enabled = 1", helper)
        self.assertIn("eligibility.valid_from is null or eligibility.valid_from <= {date_expr}", helper)
        self.assertIn("eligibility.valid_to is null or eligibility.valid_to >= {date_expr}", helper)


    def test_query_fails_closed_for_missing_or_ambiguous_instructor_identity(self):
        source = self._source()
        for token in (
            "def _exact_active_instructor",
            "return names[0] if len(names) == 1 else \"\"",
            "if not instructor:",
            'return "1=0"',
        ):
            self.assertIn(token, source)

    def test_create_permission_derives_read_only_branch_before_before_validate(self):
        source = self._source()

        plan_context = source.split("def _plan_context", 1)[1].split("def _result_context", 1)[0]
        self.assertIn('frappe.db.get_value("Student Group", student_group, BRANCH_FIELD)', plan_context)
        self.assertIn('"school_branch": str(doc.get(BRANCH_FIELD) or derived_branch or "")', plan_context)

        helper = source.split("def _has_context_branch_permission", 1)[1].split(
            "def has_assessment_plan_permission", 1
        )[0]
        for token in (
            "if doc.get(BRANCH_FIELD):",
            "if not branch:",
            '"doctype": doc.doctype',
            "BRANCH_FIELD: branch",
            "has_education_branch_permission(proxy, user, permission_type)",
        ):
            self.assertIn(token, helper)

        plan_permission = source.split("def has_assessment_plan_permission", 1)[1].split(
            "def has_assessment_result_permission", 1
        )[0]
        self.assertIn("context = _plan_context(doc)", plan_permission)
        self.assertIn("_has_context_branch_permission(", plan_permission)

        result_permission = source.split("def has_assessment_result_permission", 1)[1]
        self.assertIn("context = _result_context(doc)", result_permission)
        self.assertIn("_has_context_branch_permission(", result_permission)

    def test_controller_hook_does_not_replace_role_permission_manager(self):
        source = self._source()
        self.assertGreaterEqual(source.count("if not doc:\n        return True"), 2)


    def test_plan_mutation_requires_create_assessment_plan_capability(self):
        source = self._source()
        for token in (
            "def has_assessment_plan_permission",
            'capability = "can_create_assessment_plans" if permission_type in PLAN_MUTATION_TYPES else "can_view_subject_content"',
            "user_has_instructor_assignment_capability(",
            'on_date=context["on_date"]',
        ):
            self.assertIn(token, source)

    def test_result_read_uses_plan_date_but_mark_entry_uses_current_date(self):
        source = self._source()
        for token in (
            "def has_assessment_result_permission",
            'capability = "can_enter_marks" if mutation else "can_view_subject_content"',
            'effective_date = nowdate() if mutation else context["plan_date"]',
            "Historical result visibility follows the assignment",
            "Mark entry remains a current operational permission",
        ):
            self.assertIn(token, source)

    def test_limited_teacher_delete_cancel_and_other_destructive_actions_remain_blocked(self):
        source = self._source()
        self.assertIn('BLOCKED_MUTATION_TYPES = {"delete", "cancel", "amend", "share", "import"}', source)
        self.assertGreaterEqual(source.count("if permission_type in BLOCKED_MUTATION_TYPES"), 2)

    def test_existing_branch_permission_remains_a_prerequisite(self):
        source = self._source()
        helper = source.split("def _has_context_branch_permission", 1)[1].split(
            "def has_assessment_plan_permission", 1
        )[0]
        self.assertIn("has_education_branch_permission(doc, user, permission_type)", helper)
        self.assertIn("has_education_branch_permission(proxy, user, permission_type)", helper)
        self.assertGreaterEqual(source.count("if not _has_context_branch_permission("), 2)

    def test_hooks_use_exact_assessment_permission_layer(self):
        hooks = (APP / "hooks.py").read_text(encoding="utf-8")
        for token in (
            '"Assessment Plan": "eduedge.education.assessment_permissions.assessment_plan_query"',
            '"Assessment Result": "eduedge.education.assessment_permissions.assessment_result_query"',
            '"Assessment Plan": "eduedge.education.assessment_permissions.has_assessment_plan_permission"',
            '"Assessment Result": "eduedge.education.assessment_permissions.has_assessment_result_permission"',
        ):
            self.assertIn(token, hooks)


if __name__ == "__main__":
    unittest.main()
