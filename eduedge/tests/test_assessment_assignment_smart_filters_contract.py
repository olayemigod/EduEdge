from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAssessmentAssignmentSmartFiltersContract(unittest.TestCase):
    def _api(self):
        return (APP / "api" / "assessment_assignment_options.py").read_text(encoding="utf-8")

    def _client(self):
        return (APP / "public" / "js" / "education" / "assessment_plan.js").read_text(encoding="utf-8")

    def test_student_group_query_preserves_existing_behavior_until_capability_enforcement_is_enabled(self):
        source = self._api()
        for token in (
            "def assessment_plan_student_group_query",
            "if not (is_teacher_user() and assignment_capability_enforcement_enabled()):",
            "return student_group_query(doctype, txt, searchfield, start, page_len, filters)",
        ):
            self.assertIn(token, source)

    def test_enforced_student_group_query_is_exact_assignment_and_schedule_date_aware(self):
        source = self._api()
        for token in (
            "getdate(filters.get(\"schedule_date\") or nowdate())",
            "def _capability_group_names",
            '"can_create_assessment_plans"',
            "school_branch=branch",
            "on_date=reference_date",
            "row.get(\"assignment_scope\") == CLASS_SCOPE",
            "row.get(\"assignment_scope\") == CLASS_ARM_SCOPE",
            "allowed_groups",
        ):
            self.assertIn(token, source)

    def test_course_query_cascades_from_group_offering_curriculum_and_exact_capability(self):
        source = self._api()
        for token in (
            "def assessment_plan_course_query",
            'student_group = str(filters.get("student_group")',
            "offering = _resolve_group_offering(group)",
            '"Program Course"',
            '"parent": group.program',
            "curriculum_courses &= set(allowed_courses)",
            '"can_create_assessment_plans"',
            "row.get(\"program_offering\") == offering",
            "_row_covers_group(row, student_group)",
        ):
            self.assertIn(token, source)

    def test_default_off_teacher_course_query_still_uses_existing_assignment_scope(self):
        source = self._api()
        for token in (
            "else:",
            "allowed_courses = assigned_courses(",
            "branch=branch",
            "program_offering=offering",
            "student_group=student_group",
        ):
            self.assertIn(token, source)

    def test_client_cascade_filters_and_clears_invalid_children(self):
        source = self._client()
        for token in (
            "assessment_plan_student_group_query",
            "assessment_plan_course_query",
            "schedule_date: frm.doc.schedule_date",
            "eduedge_school_branch(frm)",
            "academic_year(frm)",
            "academic_term(frm)",
            "student_group(frm)",
            "schedule_date(frm)",
            'frm.set_value("student_group", null)',
            'frm.set_value("course", null)',
        ):
            self.assertIn(token, source)

    def test_backend_before_validate_remains_authoritative_over_smart_queries(self):
        operations = (APP / "education" / "assessment_operations.py").read_text(encoding="utf-8")
        for token in (
            "before_validate_assessment_plan",
            "require_course_assignment(",
            'require_instructor_assignment_capability(\n\t\t\t"can_create_assessment_plans"',
            "_validate_linked_context(doc, group)",
        ):
            self.assertIn(token, operations)


if __name__ == "__main__":
    unittest.main()
