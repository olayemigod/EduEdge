from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestNativeHierarchyMigrationContract(unittest.TestCase):
	def test_install_and_migrate_use_collision_safe_wrapper(self):
		install = (APP / "install.py").read_text(encoding="utf-8")
		helper = (APP / "education" / "native_hierarchy_migration.py").read_text(encoding="utf-8")
		self.assertIn("ensure_native_academic_context_foundation", install)
		self.assertEqual(install.count("ensure_native_academic_context_foundation()"), 2)
		self.assertIn("academic_fields.backfill_legacy_sections_to_departments = backfill_legacy_sections_to_departments", helper)
		self.assertIn("finally:", helper)
		self.assertIn("academic_fields.backfill_legacy_sections_to_departments = original", helper)

	def test_same_name_sections_are_isolated_by_institution(self):
		helper = (APP / "education" / "native_hierarchy_migration.py").read_text(encoding="utf-8")
		self.assertIn("owners_by_key", helper)
		self.assertIn("_exact_owned_department", helper)
		self.assertIn("_unowned_department", helper)
		self.assertIn("unambiguous", helper)
		self.assertIn("_available_department_name", helper)
		self.assertIn("institution.institution_code", helper)
		self.assertIn('{"department_name": department_name, "company": company, INSTITUTION_FIELD: institution}', helper)

	def test_one_time_patch_preserves_legacy_and_avoids_tertiary_guessing(self):
		patch = (APP / "patches" / "v0_9" / "migrate_native_academic_hierarchy.py").read_text(encoding="utf-8")
		patches = (APP / "patches.txt").read_text(encoding="utf-8")
		self.assertIn("ensure_native_academic_context_foundation", patch)
		self.assertIn('SCHOOL_TYPES = {"PRIMARY", "SECONDARY"}', patch)
		self.assertIn("Tertiary Levels are deliberately not auto-created", patch)
		self.assertNotIn("frappe.delete_doc", patch)
		self.assertIn("eduedge.patches.v0_9.migrate_native_academic_hierarchy", patches)

	def test_legacy_operational_assets_are_removed(self):
		self.assertFalse((APP / "public" / "js" / "eduedge_programme_offerings" / "level_cascade.js").exists())
		self.assertFalse((APP / "public" / "js" / "eduedge_programme_offerings" / "terminology.js").exists())
		workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
		self.assertNotIn("eduedge_programme_offerings/level_cascade.js", workflow)
		self.assertNotIn("eduedge_programme_offerings/terminology.js", workflow)


if __name__ == "__main__":
	unittest.main()
