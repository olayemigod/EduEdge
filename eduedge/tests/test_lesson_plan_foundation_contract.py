import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestLessonPlanFoundationContract(unittest.TestCase):
    def test_lesson_plan_doctype_has_governed_context_content_workflow_and_snapshots(self):
        doctype = json.loads((APP / "eduedge" / "doctype" / "eduedge_lesson_plan" / "eduedge_lesson_plan.json").read_text())
        fields = {row["fieldname"]: row for row in doctype["fields"]}
        for fieldname in (
            "lesson_plan_title", "status", "scheme_of_work", "scheme_item_reference", "scheme_version",
            "school_branch", "program_offering", "student_group", "course", "academic_year", "academic_term",
            "lesson_date", "period_label", "duration_minutes", "instructor", "instructor_assignment",
            "lesson_objectives", "prior_knowledge", "introduction", "teaching_methods", "teacher_activities",
            "learner_activities", "learning_resources", "formative_assessment", "differentiation_notes", "homework",
            "prepared_by", "submitted_by", "submitted_on", "reviewed_by", "reviewed_on", "review_comment",
            "return_reason", "scheme_title_snapshot", "offering_title_snapshot", "student_group_name_snapshot",
            "course_name_snapshot", "topic_name_snapshot", "learning_objective_snapshot",
        ):
            self.assertIn(fieldname, fields)
        self.assertEqual(fields["status"]["options"], "Draft\nSubmitted\nApproved\nReturned")
        roles = {row["role"] for row in doctype.get("permissions") or []}
        self.assertNotIn("Teacher", roles)
        self.assertNotIn("Instructor", roles)

    def test_controller_requires_approved_scheme_exact_scheme_item_assignment_and_period(self):
        source = (APP / "eduedge" / "doctype" / "eduedge_lesson_plan" / "eduedge_lesson_plan.py").read_text()
        for token in (
            'scheme.status != "Approved"',
            "Select a valid item from the approved Scheme of Work",
            "resolve_lesson_instructor_assignment",
            '"assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)]',
            '"enabled": 1',
            "scope == CLASS_SCOPE",
            "scope == CLASS_ARM_SCOPE and student_group and row.student_group == student_group",
            "Lesson Date cannot precede the Scheme academic period",
            "Lesson Date cannot extend beyond the Scheme academic period",
            "A Lesson Plan already exists",
        ):
            self.assertIn(token, source)

    def test_submitted_and_approved_history_is_protected_and_approval_snapshots_context(self):
        controller = (APP / "eduedge" / "doctype" / "eduedge_lesson_plan" / "eduedge_lesson_plan.py").read_text()
        api = (APP / "api" / "lesson_plans.py").read_text()
        self.assertIn("Approved Lesson Plans are immutable academic history", controller)
        self.assertIn("Submitted Lesson Plans are read-only until Academic Review", controller)
        self.assertIn("Submitted, Returned or Approved Lesson Plans are retained as academic history", controller)
        self.assertIn("def snapshot_lesson_plan_context", controller)
        self.assertIn("def submit_lesson_plan", api)
        self.assertIn("def approve_lesson_plan", api)
        self.assertIn("def return_lesson_plan", api)
        self.assertIn("snapshot_lesson_plan_context(doc)", api)
        self.assertIn('doc.status = "Approved"', api)
        self.assertIn('doc.status = "Returned"', api)

    def test_teacher_access_uses_exact_identity_assignment_and_migration_safe_capability(self):
        source = (APP / "api" / "lesson_plans.py").read_text()
        for token in (
            "resolve_exact_instructor_for_user(required=True)",
            "resolve_lesson_instructor_assignment",
            "assignment_capability_enforcement_enabled()",
            'require_instructor_assignment_capability(\n            "can_view_subject_content"',
            "You can access only Lesson Plans assigned to your Instructor identity",
        ):
            self.assertIn(token, source)

    def test_workbench_is_smart_cascading_permission_aware_and_bounded(self):
        source = (APP / "api" / "lesson_plans.py").read_text()
        for token in (
            "get_allowed_school_branches",
            "Program Course",
            '"status": "Approved"',
            "_group_options",
            "_course_options",
            "_scheme_options",
            "_scheme_items",
            "_instructor_options",
            'page_length=min(limit * 3 + 1, 151)',
            'page_length=min(max(cint(page_length) or 25, 1), 50)',
        ):
            self.assertIn(token, source)

    def test_submission_requires_minimum_teaching_preparation_content(self):
        source = (APP / "api" / "lesson_plans.py").read_text()
        for label in ("Lesson Objectives", "Teaching Methods", "Learner Activities", "Assessment / Evaluation"):
            self.assertIn(label, source)
        self.assertIn("Complete these Lesson Plan sections before submission", source)


if __name__ == "__main__":
    unittest.main()
