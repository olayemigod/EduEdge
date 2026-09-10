from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestLessonPlanUIContract(unittest.TestCase):
    def test_page_loader_uses_edgesuite_and_lesson_plan_bundle(self):
        source = (APP / "eduedge" / "page" / "eduedge_lesson_plans" / "eduedge_lesson_plans.js").read_text(encoding="utf-8")
        self.assertIn('frappe.require("edgesuite_ui.bundle.js"', source)
        self.assertIn('frappe.require("eduedge_lesson_plans.bundle.js"', source)
        self.assertIn("window.createEduEdgeLessonPlansApp", source)

    def test_workbench_uses_edgesuite_smart_filters_and_cascade_clears(self):
        source = (APP / "public" / "js" / "eduedge_lesson_plans" / "EduEdgeLessonPlans.vue").read_text(encoding="utf-8")
        for token in (
            "<EdgeAppShell",
            "<EdgePageLayout>",
            "<EdgePageHeader",
            "<EdgeFilterBar",
            "Branch / Campus",
            "Class / Programme Offering",
            "Class Arm",
            "Subject / Course",
            "Approved Scheme of Work",
            "Scheme Item / Topic",
            "Lesson Date",
            "Select eligible Instructor",
            "branchChanged()",
            "offeringChanged()",
            "groupChanged()",
            "courseChanged()",
            'this.filters.program_offering = ""',
            'this.filters.student_group = ""',
            'this.filters.course = ""',
            'this.filters.scheme_of_work = ""',
        ):
            self.assertIn(token, source)

    def test_lesson_editor_uses_governed_post_workflow_without_direct_db_mutation(self):
        source = (APP / "public" / "js" / "eduedge_lesson_plans" / "EduEdgeLessonPlans.vue").read_text(encoding="utf-8")
        for method in (
            "eduedge.api.lesson_plans.save_lesson_plan",
            "eduedge.api.lesson_plans.submit_lesson_plan",
            "eduedge.api.lesson_plans.approve_lesson_plan",
            "eduedge.api.lesson_plans.return_lesson_plan",
        ):
            self.assertIn(method, source)
        self.assertIn('type: "POST"', source)
        for forbidden in ("frappe.db.set_value", "frappe.db.insert", "frappe.db.delete_doc"):
            self.assertNotIn(forbidden, source)

    def test_review_and_history_states_are_clear_and_readable(self):
        source = (APP / "public" / "js" / "eduedge_lesson_plans" / "EduEdgeLessonPlans.vue").read_text(encoding="utf-8")
        for token in (
            "Submit for Review",
            "Approve",
            "Return for Correction",
            "Returned for correction",
            "Approval snapshot",
            "Approved Lesson Plans are immutable academic history",
            "Submitted Lesson Plans are read-only",
        ):
            self.assertIn(token, source)

    def test_navigation_and_access_manifest_register_lesson_plan_route(self):
        navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text(encoding="utf-8")
        access = (APP / "access_control.py").read_text(encoding="utf-8")
        self.assertIn('menuItem(__("Lesson Plans"), "/app/eduedge-lesson-plans"', navigation)
        self.assertIn('"/app/eduedge-lesson-plans"', navigation)
        self.assertIn('"/app/eduedge-lesson-plans": (("instructor_assignment", "read"),)', access)
        self.assertIn("APIs separately enforce exact Instructor identity", access)

    def test_filters_are_url_persisted_and_results_are_paginated(self):
        source = (APP / "public" / "js" / "eduedge_lesson_plans" / "EduEdgeLessonPlans.vue").read_text(encoding="utf-8")
        for token in (
            "URLSearchParams",
            "window.history.replaceState",
            "Previous",
            "Next",
            "date_from",
            "date_to",
            "page_length: 25",
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
