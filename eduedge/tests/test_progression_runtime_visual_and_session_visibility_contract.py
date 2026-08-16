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
        ):
            self.assertIn(token, css)
        self.assertIn("eduedge_student_progression_runtime_fix.css", page)
        self.assertIn("ensure_student_progression_runtime_styles", page)

    def test_programme_offering_page_exposes_global_sessions_without_hiding_calendar_readiness(self):
        page = (APP / "eduedge/page/eduedge_program_offerings/eduedge_program_offerings.js").read_text(encoding="utf-8")
        for token in (
            "merge_academic_year_options",
            'frappe.db.get_list("Academic Year"',
            "proxy.data?.options",
            "proxy.draftOptions",
            "calendar_ready: false",
            "Academic Calendar required",
            "Academic Setup → Academic Foundation",
            "proxy.loadDraftOptions = async",
            "proxy.saveOffering = async",
        ):
            self.assertIn(token, page)
        self.assertIn("program_offering: context.offering", page)


if __name__ == "__main__":
    unittest.main()
