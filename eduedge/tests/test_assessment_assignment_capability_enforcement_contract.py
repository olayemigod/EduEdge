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
            "assessment_date = doc.schedule_date or nowdate()",
            "on_date=assessment_date",
        ):
            self.assertIn(token, source)

    def test_plan_capability_is_evaluated_on_assessment_schedule_date(self):
        source = self._source()
        self.assertIn("assessment_date = doc.schedule_date or nowdate()", source)
        validator = source.split("def before_validate_assessment_plan", 1)[1].split(
            "def _validate_examiner_and_supervisor", 1
        )[0]
        self.assertGreaterEqual(validator.count("on_date=assessment_date"), 2)
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

    def test_assessment_result_scope_and_criteria_are_plan_authoritative(self):
        source = self._source()
        validator = source.split("def before_validate_assessment_result", 1)[1].split(
            "def validate_publication_scope",
            1,
        )[0]
        for token in (
            "if doc.is_new():",
            "_lock_assessment_plan_for_result(doc.assessment_plan)",
            "_assert_no_active_assessment_result_duplicate(doc)",
            "for update",
            '"docstatus": ["!=", 2]',
            'filters["name"] = ["!=", doc.name]',
            "frappe.DuplicateEntryError",
            "_apply_assessment_result_plan_contract(doc, plan)",
            '("student_group", plan.student_group)',
            '("program", plan.program)',
            '("course", plan.course)',
            '("academic_year", plan.academic_year)',
            '("academic_term", plan.academic_term)',
            '("assessment_group", plan.assessment_group)',
            '("grading_scale", plan.grading_scale)',
            "doc.maximum_score = flt(plan.maximum_assessment_score)",
            "if score_state not in SCORE_STATES:",
            "Invalid Assessment Result score state",
            '"Assessment Plan Criteria"',
            '"parenttype": "Assessment Plan"',
            "Assessment Result criteria must exactly match the submitted Assessment Plan.",
            'if raw_score in (None, ""):',
            "requires an explicit score",
            "if score < 0 or score > maximum_score:",
            "must be between 0 and {1}",
            "row.maximum_score = maximum_score",
        ):
            self.assertIn(token, validator)

        marker = source.split("def _get_assessment_plan", 1)[1]
        self.assertIn('"grading_scale"', marker)
        self.assertIn('"maximum_assessment_score"', marker)

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
