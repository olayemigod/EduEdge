from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "eduedge" / "patches" / "v0_9" / "migrate_native_academic_hierarchy.py"


class TestNativeHierarchyProgramCollisionContract(unittest.TestCase):
	def test_program_migration_handles_global_program_name_collisions(self):
		source = PATCH.read_text(encoding="utf-8")
		for expected in (
			"def _program_is_compatible",
			"def _available_program_name",
			'frappe.db.exists("Program", {"program_name": candidate})',
			"program_name = _available_program_name(level.level_name, level.institution)",
			"existing and _program_is_compatible(existing, level, department, program_meta)",
			"values[INSTITUTION_FIELD] = level.institution",
			"values[ACADEMIC_SECTION_FIELD] = level.academic_section",
		):
			self.assertIn(expected, source)

	def test_unowned_program_is_not_claimed_without_context_match(self):
		source = PATCH.read_text(encoding="utf-8")
		self.assertIn("Do not silently claim an unowned global Program", source)
		self.assertIn('existing.get("department") == department', source)
		self.assertIn("section == level.academic_section", source)
		self.assertIn("return False", source)

	def test_program_context_backfill_remains_idempotent(self):
		source = PATCH.read_text(encoding="utf-8")
		self.assertIn("def _sync_program_context", source)
		self.assertIn('if not current_department:', source)
		self.assertIn('not frappe.db.get_value("Program", program, INSTITUTION_FIELD)', source)
		self.assertIn('not frappe.db.get_value("Program", program, ACADEMIC_SECTION_FIELD)', source)
		self.assertIn("update_modified=False", source)


if __name__ == "__main__":
	unittest.main()
