from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSchemeCoverageContract(unittest.TestCase):
    def test_report_distinguishes_actionable_curriculum_states(self):
        source = (APP / "api" / "scheme_coverage.py").read_text(encoding="utf-8")
        for status in (
            "Missing Scheme",
            "Draft Scheme",
            "No Delivery Data",
            "In Progress",
            "Deferred",
            "Completed",
            "Historical",
        ):
            self.assertIn(status, source)
        self.assertIn("ATTENTION_STATUSES", source)
        self.assertIn('"average_coverage"', source)
        self.assertIn('"missing_schemes"', source)
        self.assertIn('"completed"', source)

    def test_expected_contexts_come_from_offering_curriculum_not_arbitrary_cartesian_records(self):
        source = (APP / "api" / "scheme_coverage.py").read_text(encoding="utf-8")
        self.assertIn("Program Course", source)
        self.assertIn("program_courses.get(offering.get(\"program\"), [])", source)
        self.assertIn("_assignment_applies", source)
        self.assertIn("COURSE_REQUIRED_TYPES", source)
        self.assertIn("CLASS_SCOPE", source)
        self.assertIn("CLASS_ARM_SCOPE", source)

    def test_limited_instructor_report_fails_closed_to_exact_identity_assignment_and_view_capability(self):
        source = (APP / "api" / "scheme_coverage.py").read_text(encoding="utf-8")
        self.assertIn("_exact_limited_instructor", source)
        self.assertIn("get_active_instructor_names_for_user", source)
        self.assertIn("must resolve to exactly one active Instructor", source)
        self.assertIn("require_view_capability", source)
        self.assertIn("can_view_subject_content", source)
        self.assertIn("assignment_capability_enforcement_enabled()", source)

    def test_report_is_read_only_and_uses_delivery_history_as_source_of_truth(self):
        source = (APP / "api" / "scheme_coverage.py").read_text(encoding="utf-8")
        self.assertIn("EduEdge Scheme Delivery Log", source)
        self.assertIn("latest_by_item", source)
        self.assertIn("periods_delivered", source)
        for forbidden in (".save()", ".insert(", ".delete(", "frappe.db.set_value"):
            self.assertNotIn(forbidden, source)

    def test_coverage_panel_has_filters_summary_attention_and_clickable_context(self):
        source = (APP / "public" / "js" / "eduedge_ui" / "components" / "SchemeCoveragePanel.vue").read_text(encoding="utf-8")
        for token in (
            "Academic Session",
            "Term / Semester",
            "Instructor",
            "Coverage Status",
            "Include historical academic periods",
            "Needs Attention",
            "Missing Schemes",
            "Average Coverage",
            "Open Scheme",
            "Open Context",
            "get_scheme_coverage_report",
        ):
            self.assertIn(token, source)
        for forbidden in ("frappe.db.set_value", "frappe.db.insert", "frappe.db.delete_doc"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
