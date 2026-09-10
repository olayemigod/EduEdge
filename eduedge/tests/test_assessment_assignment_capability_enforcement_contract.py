from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAssessmentAssignmentCapabilityEnforcementContract(unittest.TestCase):
    def _source(self):
        return (APP / "education" / "assessment_operations.py").read_text(encoding="utf-8")

    def test_assessment_plan_preserves_existing_course_assignment_gate_and_adds_exact_capability(self):
        source = self._source()
        for token in (
            "if is_teacher_user():",
            "require_course_assignment(",
            'require_instructor_assignment_capability(\n\t\t\t"can_create_assessment_plans"',
            "school_branch=doc.get(BRANCH_FIELD)",
            "program_offering=program_offering or \"\"",
            "student_group=doc.student_group",
            "course=doc.course",
            "on_date=doc.schedule_date or nowdate()",
        ):
            self.assertIn(token, source)

    def test_plan_capability_is_evaluated_on_assessment_schedule_date(self):
        source = self._source()
        self.assertIn("on_date=doc.schedule_date or nowdate()", source)
        self.assertIn("Assessment date must lie within the Student Group academic period.", source)

    def test_mark_entry_requires_current_exact_capability_for_limited_teacher(self):
        source = self._source()
        for token in (
            "def before_validate_assessment_result",
            "if is_teacher_user():",
            "program_offering = group.get(OFFERING_FIELD) or _resolve_group_offering(group)",
            'require_instructor_assignment_capability(\n\t\t\t"can_enter_marks"',
            "student_group=plan.student_group",
            "course=plan.course",
            "on_date=nowdate()",
            "Former Instructors therefore do not",
            "retain mark-entry access",
        ):
            self.assertIn(token, source)

    def test_assessment_plan_lookup_includes_course_and_schedule_context(self):
        source = self._source()
        marker = source.split("def _get_assessment_plan", 1)[1]
        self.assertIn('"student_group"', marker)
        self.assertIn('"course"', marker)
        self.assertIn('"schedule_date"', marker)
        self.assertIn("BRANCH_FIELD", marker)

    def test_existing_branch_group_student_and_examiner_safety_is_preserved(self):
        source = self._source()
        for token in (
            "_validate_branch(doc)",
            "_validate_linked_context(doc, group)",
            "Assessment room must belong to the selected School Branch / Campus.",
            "assert_instructor_assignment(",
            "Assessment Result Branch must match the selected Assessment Plan Branch.",
            "Assessment Result Branch must match the selected Student Branch.",
            '"Student Group Student"',
            '"active": 1',
        ):
            self.assertIn(token, source)

    def test_rollout_remains_default_off_through_shared_capability_gate(self):
        source = self._source()
        self.assertIn("require_instructor_assignment_capability", source)
        gate = (APP / "education" / "instructor_assignment_capabilities.py").read_text(encoding="utf-8")
        self.assertIn("if not assignment_capability_enforcement_enabled() or not is_limited_instructor_user(resolved_user)", gate)
        settings = (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_settings"
            / "eduedge_settings.json"
        ).read_text(encoding="utf-8")
        self.assertIn('"default":"0","fieldname":"enforce_instructor_assignment_capabilities"', settings)


if __name__ == "__main__":
    unittest.main()
