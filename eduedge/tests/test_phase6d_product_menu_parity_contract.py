from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


PHASE6D_ROUTES = (
    "/app/eduedge-student-enrollments",
    "/app/eduedge-student-progression",
    "/app/eduedge-instructors",
    "/app/eduedge-instructor-assignments",
    "/app/eduedge-curriculum",
    "/app/eduedge-schemes-of-work",
    "/app/eduedge-lesson-plans",
    "/app/eduedge-program-offerings",
    "/app/eduedge-academic-operations",
    "/app/eduedge-academic-readiness",
)


class TestPhase6DProductMenuParityContract(unittest.TestCase):
    def test_phase6d_routes_exist_in_sidebar_waffle_and_access_manifest(self):
        navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text(encoding="utf-8")
        product_menu = (APP / "public" / "js" / "eduedge_product_menu.bundle.js").read_text(encoding="utf-8")
        access = (APP / "access_control.py").read_text(encoding="utf-8")
        for route in PHASE6D_ROUTES:
            self.assertIn(route, navigation, f"Sidebar navigation is missing {route}")
            self.assertIn(route, product_menu, f"EdgeSuite product/waffle menu is missing {route}")
            self.assertIn(route, access, f"Access manifest is missing {route}")

    def test_product_menu_remains_permission_filtered(self):
        source = (APP / "public" / "js" / "eduedge_product_menu.bundle.js").read_text(encoding="utf-8")
        for token in (
            "function itemAllowed(menuItem)",
            "frappe.boot?.eduedge_access_manifest",
            "manifest.resources",
            "manifest.routes",
            "items: section.items.filter(itemAllowed)",
        ):
            self.assertIn(token, source)

    def test_new_phase6d_menu_entries_use_readable_business_labels(self):
        source = (APP / "public" / "js" / "eduedge_product_menu.bundle.js").read_text(encoding="utf-8")
        for label in (
            'item("Student Enrollments"',
            'item("Student Progression"',
            'item("Instructors"',
            'item("Instructor Assignments"',
            'item("Scheme of Work"',
            'item("Lesson Plans"',
            'item("Academic Readiness"',
        ):
            self.assertIn(label, source)


if __name__ == "__main__":
    unittest.main()
