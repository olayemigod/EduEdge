from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestProgressionRuntimeVisualAndSessionVisibilityContract(unittest.TestCase):
    def test_student_progression_runtime_css_prevents_panel_overlap_and_dark_text(self):
        css = (APP / "public/css/eduedge_student_progression_runtime_fix.css").read_text(encoding="utf-8")
        page = (APP / "eduedge/page/eduedge_student_progression/eduedge_student_progression.js").read_text(encoding="utf-8")
        for token in (
            ".progression-layout",
            ".progression-panel",
            ".progression-actions",
            "min-width: 0",
            "var(--text-color",
            "@media (max-width: 1320px)",
            "grid-template-columns: minmax(0, 1fr)",
            "overflow-wrap: anywhere",
            ".progression-row > .edge-button",
        ):
            self.assertIn(token, css)
        self.assertIn("eduedge_student_progression_runtime_fix.css", page)
        self.assertIn("ensure_student_progression_runtime_styles", page)

    def test_programme_offering_page_exposes_global_sessions_without_hiding_calendar_readiness(self):
        page = (APP / "eduedge/page/eduedge_program_offerings/eduedge_program_offerings.js").read_text(encoding="utf-8")
        api = (APP / "api/programme_offering_session_options.py").read_text(encoding="utf-8")
        for token in (
            "programme_offering_session_options.get_programme_offering_session_options",
            "install_session_option_loader",
            "proxy.draftOptions",
            "proxy.loadDraftOptions = async",
            "Academic Sessions & Terms",
        ):
            self.assertIn(token, page)
        for token in (
            'frappe.has_permission("Academic Year", "read")',
            'frappe.get_all(\n\t\t"Academic Year"',
            '"calendar_ready": bool(calendar.get("name"))',
            "selected_session_calendar_ready",
            "Academic Year is a global academic master",
        ):
            self.assertIn(token, api)
        self.assertNotIn("merge_academic_year_options", page)
        self.assertNotIn('frappe.db.get_list("Academic Year"', page)

    def test_programme_offering_page_filters_catalogue_by_selected_session(self):
        page = (APP / "eduedge/page/eduedge_program_offerings/eduedge_program_offerings.js").read_text(encoding="utf-8")
        for token in (
            "programme_offering_session_options.get_programme_offerings_page_with_sessions",
            "load_session_filtered_page",
            "requestedFilters.academic_year",
            "returnedYear !== selectedYear",
            "row.academic_year",
            "proxy.filterYearChanged = async",
            "proxy.applyFilters = async",
        ):
            self.assertIn(token, page)
        self.assertIn("Class Intake returned records outside Academic Session", page)

    def test_student_progression_uses_the_same_authoritative_academic_session_discovery(self):
        api = (APP / "api/student_progression.py").read_text(encoding="utf-8")
        for token in (
            'frappe.has_permission("Academic Year", "read")',
            'frappe.get_all("Academic Year", fields=fields',
            "Academic Year is a global academic master",
            "aligned with Class Intake",
        ):
            self.assertIn(token, api)
        self.assertNotIn('frappe.get_list("Academic Year", fields=fields', api)


if __name__ == "__main__":
    unittest.main()
