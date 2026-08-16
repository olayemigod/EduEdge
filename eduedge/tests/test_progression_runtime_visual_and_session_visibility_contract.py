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
            'frappe.get_list(\n\t\t"Academic Year"',
            '"calendar_ready": bool(calendar.get("name"))',
            "selected_session_calendar_ready",
            "Programme Offering is sessional",
        ):
            self.assertIn(token, api)
        self.assertNotIn("merge_academic_year_options", page)
        self.assertNotIn('frappe.db.get_list("Academic Year"', page)


if __name__ == "__main__":
    unittest.main()
