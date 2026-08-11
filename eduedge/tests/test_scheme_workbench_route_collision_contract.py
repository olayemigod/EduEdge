from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
OLD_PAGE = "eduedge-scheme-of-work"
NEW_PAGE = "eduedge-schemes-of-work"
NEW_ROUTE = f"/app/{NEW_PAGE}"


class TestSchemeWorkbenchRouteCollisionContract(unittest.TestCase):
    def test_scheme_workbench_page_uses_collision_free_name(self):
        old_dir = APP / "eduedge" / "page" / "eduedge_scheme_of_work"
        new_json = APP / "eduedge" / "page" / "eduedge_schemes_of_work" / "eduedge_schemes_of_work.json"
        self.assertFalse(old_dir.exists(), "The old Page collides with the EduEdge Scheme of Work DocType Desk route.")
        self.assertTrue(new_json.exists())
        payload = json.loads(new_json.read_text(encoding="utf-8"))
        self.assertEqual(payload.get("name"), NEW_PAGE)
        self.assertEqual(payload.get("page_name"), NEW_PAGE)
        self.assertEqual(payload.get("title"), "Scheme of Work")

    def test_navigation_waffle_and_access_manifest_use_new_route(self):
        navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text(encoding="utf-8")
        waffle = (APP / "public" / "js" / "eduedge_product_menu.bundle.js").read_text(encoding="utf-8")
        access = (APP / "access_control.py").read_text(encoding="utf-8")
        for source in (navigation, waffle, access):
            self.assertIn(NEW_ROUTE, source)
        self.assertIn(f'"/app/{OLD_PAGE}": "{NEW_ROUTE}"', navigation)
        self.assertNotIn(f'"{NEW_ROUTE}": False', access)

    def test_idempotent_patch_removes_old_page_and_is_registered(self):
        patch = (APP / "patches" / "v0_9" / "rename_scheme_of_work_page_route.py").read_text(encoding="utf-8")
        patches = (APP / "patches.txt").read_text(encoding="utf-8")
        for token in (
            f'OLD_PAGE = "{OLD_PAGE}"',
            f'NEW_PAGE = "{NEW_PAGE}"',
            'frappe.rename_doc("Page", OLD_PAGE, NEW_PAGE',
            'frappe.delete_doc("Page", OLD_PAGE',
            "frappe.clear_cache()",
        ):
            self.assertIn(token, patch)
        self.assertIn("eduedge.patches.v0_9.rename_scheme_of_work_page_route", patches)

    def test_custom_page_route_does_not_equal_scheme_doctype_slug(self):
        scheme_json = APP / "eduedge" / "doctype" / "eduedge_scheme_of_work" / "eduedge_scheme_of_work.json"
        payload = json.loads(scheme_json.read_text(encoding="utf-8"))
        doctype_slug = str(payload.get("name") or "").strip().lower().replace(" ", "-")
        self.assertEqual(doctype_slug, OLD_PAGE)
        self.assertNotEqual(NEW_PAGE, doctype_slug)


if __name__ == "__main__":
    unittest.main()
