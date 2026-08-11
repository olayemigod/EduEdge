from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAcademicReadinessContract(unittest.TestCase):
    def test_readiness_service_is_management_branch_scoped_and_read_only(self):
        source = (APP / "api" / "academic_readiness.py").read_text(encoding="utf-8")
        for token in (
            "READINESS_MANAGER_ROLES",
            "_require_manager()",
            'require_eduedge_access(feature_key="academics", action="view_academic_readiness")',
            "assert_branch_access(value)",
            "get_allowed_school_branches",
            "Select a permitted Branch / Campus",
        ):
            self.assertIn(token, source)
        for forbidden in (".save()", ".insert(", ".delete(", "frappe.db.set_value"):
            self.assertNotIn(forbidden, source)

    def test_expected_teaching_contexts_derive_from_offering_program_course_and_class_arms(self):
        source = (APP / "api" / "academic_readiness.py").read_text(encoding="utf-8")
        self.assertIn("Program Course", source)
        self.assertIn("_expected_contexts", source)
        self.assertIn("groups_by_offering", source)
        self.assertIn('group_targets = offering_groups or [{"name": "", "label": "Class-wide"}]', source)
        self.assertIn("COURSE_REQUIRED_TYPES", source)
        self.assertIn("CLASS_SCOPE", source)
        self.assertIn("CLASS_ARM_SCOPE", source)
        self.assertIn("_date_overlap", source)

    def test_readiness_keeps_independent_auditable_signals_instead_of_opaque_score(self):
        source = (APP / "api" / "academic_readiness.py").read_text(encoding="utf-8")
        for token in (
            '"teaching_assignment_coverage"',
            '"identity_attention"',
            '"scheme_approval_coverage"',
            '"average_delivery_coverage"',
            '"assessment_plans"',
            '"readiness_score"',
            "No single readiness score is calculated",
        ):
            self.assertIn(token, source)

    def test_identity_scheme_and_delivery_attention_are_actionable(self):
        source = (APP / "api" / "academic_readiness.py").read_text(encoding="utf-8")
        for token in (
            '"Teaching Assignment"',
            '"Instructor Identity"',
            '"Scheme of Work"',
            '"Curriculum Delivery"',
            "get_instructor_identity_states",
            "_select_scheme_for_context",
            "_delivery_state",
            '"/app/eduedge-instructor-assignments"',
            '"/app/eduedge-scheme-of-work"',
        ):
            self.assertIn(token, source)

    def test_assessment_counts_are_activity_metrics_not_invented_missing_plan_policy(self):
        source = (APP / "api" / "academic_readiness.py").read_text(encoding="utf-8")
        self.assertIn("Assessment Plan", source)
        self.assertIn('"draft_assessment_plans"', source)
        self.assertIn('"submitted_assessment_plans"', source)
        self.assertIn("Assessment counts show recorded planning activity only", source)
        self.assertIn("does not infer a missing Assessment Plan", source)

    def test_edgesuite_page_has_smart_filters_metrics_and_action_queue(self):
        page = (APP / "public" / "js" / "eduedge_academic_readiness" / "EduEdgeAcademicReadiness.vue").read_text(encoding="utf-8")
        loader = (APP / "eduedge" / "page" / "eduedge_academic_readiness" / "eduedge_academic_readiness.js").read_text(encoding="utf-8")
        for token in (
            "<EdgeAppShell",
            "<EdgePageLayout>",
            "<EdgePageHeader",
            "<EdgeFilterBar",
            "Teaching Assignment Coverage",
            "Instructor Identity",
            "Approved Scheme Coverage",
            "Curriculum Delivery",
            "Assessment planning activity",
            "Management action queue",
            "openAttention(row)",
            "URLSearchParams",
            "get_academic_readiness",
        ):
            self.assertIn(token, page)
        self.assertIn('frappe.require("edgesuite_ui.bundle.js"', loader)
        self.assertIn('frappe.require("eduedge_academic_readiness.bundle.js"', loader)

    def test_navigation_and_manifest_register_academic_readiness(self):
        navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text(encoding="utf-8")
        access = (APP / "access_control.py").read_text(encoding="utf-8")
        self.assertIn('menuItem(__("Academic Readiness"), "/app/eduedge-academic-readiness"', navigation)
        self.assertIn('"/app/eduedge-academic-readiness"', navigation)
        self.assertIn('"/app/eduedge-academic-readiness": (("program_offering", "read"),)', access)
        self.assertIn("API separately enforces academic-management roles and Branch access", access)


if __name__ == "__main__":
    unittest.main()
