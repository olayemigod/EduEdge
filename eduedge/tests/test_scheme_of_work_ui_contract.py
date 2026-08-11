from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSchemeOfWorkUIContract(unittest.TestCase):
    def test_page_loader_uses_edgesuite_and_product_bundle(self):
        source = (APP / "eduedge" / "page" / "eduedge_scheme_of_work" / "eduedge_scheme_of_work.js").read_text(encoding="utf-8")
        self.assertIn('frappe.require("edgesuite_ui.bundle.js"', source)
        self.assertIn('frappe.require("eduedge_scheme_of_work.bundle.js"', source)
        self.assertIn("window.createEduEdgeSchemeOfWorkApp", source)

    def test_vue_uses_edgesuite_shell_and_smart_cascades(self):
        source = (APP / "public" / "js" / "eduedge_scheme_of_work" / "EduEdgeSchemeOfWork.vue").read_text(encoding="utf-8")
        for token in (
            "<EdgeAppShell",
            "<EdgePageLayout>",
            "<EdgePageHeader",
            "<EdgeFilterBar",
            "branchChanged()",
            "offeringChanged()",
            "groupChanged()",
            "courseChanged()",
            'this.filters.program_offering = ""',
            'this.filters.student_group = ""',
            'this.filters.course = ""',
        ):
            self.assertIn(token, source)

    def test_ui_uses_governed_post_actions_and_no_direct_database_mutation(self):
        source = (APP / "public" / "js" / "eduedge_scheme_of_work" / "EduEdgeSchemeOfWork.vue").read_text(encoding="utf-8")
        for method in (
            "eduedge.api.scheme_of_work.save_scheme",
            "eduedge.api.scheme_of_work.approve_scheme",
            "eduedge.api.scheme_of_work.create_next_version",
            "eduedge.api.scheme_of_work.retire_scheme",
        ):
            self.assertIn(method, source)
        self.assertIn('type: "POST"', source)
        for forbidden in ("frappe.db.set_value", "frappe.db.insert", "frappe.db.delete_doc"):
            self.assertNotIn(forbidden, source)

    def test_approved_history_is_read_only_and_snapshot_visible(self):
        source = (APP / "public" / "js" / "eduedge_scheme_of_work" / "EduEdgeSchemeOfWork.vue").read_text(encoding="utf-8")
        self.assertIn("Approved curriculum is immutable", source)
        self.assertIn("Approval snapshot", source)
        self.assertIn("topic_name_snapshot", source)
        self.assertIn('draft.status === "Draft"', source)
        self.assertIn("Create New Version", source)

    def test_workbench_filters_exact_assignment_curriculum_and_preserves_history(self):
        source = (APP / "api" / "scheme_of_work_workbench.py").read_text(encoding="utf-8")
        for token in (
            "get_active_instructor_names_for_user",
            "COURSE_REQUIRED_TYPES",
            "Program Course",
            "Course Topic",
            "can_view_subject_content",
            "can_manage_subject_topics",
            "_historical_scheme_exists",
            "requested_offering",
            'and cint(selected_offering.get("is_active"))',
        ):
            self.assertIn(token, source)

    def test_navigation_and_access_manifest_register_scheme_route(self):
        navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text(encoding="utf-8")
        access = (APP / "access_control.py").read_text(encoding="utf-8")
        self.assertIn('menuItem(__("Scheme of Work"), "/app/eduedge-scheme-of-work"', navigation)
        self.assertIn('"/app/eduedge-scheme-of-work"', navigation)
        self.assertIn('"/app/eduedge-scheme-of-work": (("course", "read"),)', access)
        self.assertIn("We intentionally do not grant broad DocType read permission to Instructor roles", access)


if __name__ == "__main__":
    unittest.main()
