from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestClassIntakeRuntimeSessionRedirectContract(unittest.TestCase):
    def test_stale_class_intake_browser_calls_redirect_to_all_session_runtime(self):
        guard = (APP / "security/request_method.py").read_text(encoding="utf-8")
        expected = {
            '"eduedge.api.programme_offerings.get_programme_offerings_page": "eduedge.api.programme_offering_session_options.get_programme_offerings_page_with_sessions"',
            '"eduedge.api.programme_offerings_safe.get_programme_offering_options": "eduedge.api.programme_offering_session_options.get_programme_offering_session_options"',
        }
        for mapping in expected:
            self.assertIn(mapping, guard)

    def test_page_and_editor_share_the_authoritative_global_session_catalogue(self):
        api = (APP / "api/programme_offering_session_options.py").read_text(encoding="utf-8")
        self.assertIn("def _apply_all_sessions", api)
        self.assertIn("def get_programme_offerings_page_with_sessions", api)
        self.assertIn("result = base.get_programme_offerings_page(**kwargs)", api)
        self.assertIn("result = base.get_programme_offering_options(", api)
        self.assertGreaterEqual(api.count("return _apply_all_sessions("), 2)
        self.assertIn('frappe.has_permission("Academic Year", "read")', api)
        self.assertIn('frappe.get_all(\n\t\t"Academic Year"', api)
        self.assertIn('"calendar_ready": bool(calendar.get("name"))', api)


if __name__ == "__main__":
    unittest.main()
