from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSessionalClassArmDownstreamAlignmentContract(unittest.TestCase):
    def test_assessment_operations_keeps_sessional_group_visible_inside_selected_term(self):
        api = (APP / "api/assessment_operations_sessional.py").read_text(encoding="utf-8")
        bundle = (APP / "public/js/eduedge_assessment_operations.bundle.js").read_text(encoding="utf-8")
        self.assertIn("def _term_compatible", api)
        self.assertIn("not selected_term or not group_term", api)
        self.assertNotIn('["in", [academic_term, ""]]', api)
        self.assertIn('plan_filters["academic_term"] = academic_term', api)
        self.assertIn('"academic_term": academic_term or ""', api)
        self.assertIn("assessment_operations_sessional.get_assessment_context", bundle)

    def test_assessment_plan_link_query_uses_reviewed_session_term_compatibility(self):
        api = (APP / "api/assessment_assignment_options.py").read_text(encoding="utf-8")
        self.assertIn("from eduedge.api.academic_operations_review import student_group_query", api)
        self.assertIn("def _session_term_compatible", api)
        self.assertIn("compatible = [row for row in rows if _session_term_compatible", api)
        self.assertNotIn('group_filters["academic_term"] = filters["academic_term"]', api)
        self.assertIn('filters["academic_term"] = ["is", "not set"]', api)

    def test_cbt_student_group_options_do_not_require_course_on_class_arm(self):
        api = (APP / "api/cbt_schedule_operations.py").read_text(encoding="utf-8")
        self.assertIn("def _sessional_student_group_options", api)
        self.assertIn('filters["academic_year"] = payload.get("academic_year")', api)
        self.assertIn('filters["program"] = payload.get("program")', api)
        self.assertNotIn('filters["course"] = payload.get("course")', api)
        self.assertIn("not selected_course or not group_course", api)
        self.assertIn("not selected_term or not group_term", api)
        self.assertIn('row.academic_term or "Full session"', api)

    def test_cbt_schedule_and_result_sync_remain_exact_term_transaction_context(self):
        schedule = (APP / "eduedge/doctype/eduedge_cbt_exam_schedule/eduedge_cbt_exam_schedule.py").read_text(encoding="utf-8")
        result_sync = (APP / "cbt/result_sync.py").read_text(encoding="utf-8")
        self.assertIn('("academic_term", _("Academic Term"))', schedule)
        self.assertIn("group_value = group.get(fieldname)", schedule)
        self.assertIn("if self.get(fieldname) and group_value and self.get(fieldname) != group_value", schedule)
        self.assertIn("Assessment Plan Student Group must match the actual Schedule Student Group / Class", schedule)
        self.assertIn("if plan.student_group != schedule.student_group or plan.course != schedule.course", result_sync)

    def test_results_and_report_cards_remain_publication_scoped_not_rollover_copied(self):
        report_cards = (APP / "api/report_cards.py").read_text(encoding="utf-8")
        rollover = (APP / "api/class_arm_session_rollover.py").read_text(encoding="utf-8")
        self.assertIn('"EduEdge Result Publication"', report_cards)
        self.assertIn('"academic_term"', report_cards)
        self.assertIn('"assessment_results_carried_forward": False', rollover)
        self.assertIn('"cbt_attempts_or_results_carried_forward": False', rollover)


if __name__ == "__main__":
    unittest.main()
