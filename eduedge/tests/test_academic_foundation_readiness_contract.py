from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAcademicFoundationReadinessContract(unittest.TestCase):
	def test_foundation_api_returns_calendar_periods_progression_and_readiness(self):
		api = (APP / "api" / "academic_foundation.py").read_text(encoding="utf-8")
		for token in (
			"MAX_PERIOD_ROWS",
			"_attach_calendar_periods",
			'"current_period"',
			'"has_calendar_gap_today"',
			"_build_progression",
			"_walk_progression_chain",
			"_build_readiness",
			'"can_write_calendar"',
		):
			self.assertIn(token, api)

	def test_calendar_readiness_keeps_intentional_gaps_visible(self):
		api = (APP / "api" / "academic_foundation.py").read_text(encoding="utf-8")
		self.assertIn('"code": "calendar_gap"', api)
		self.assertIn("outside every configured Academic Period", api)
		self.assertIn('"code": "calendar_without_periods"', api)
		self.assertNotIn("current_academic_term", api)

	def test_progression_readiness_reports_disabled_or_missing_targets(self):
		api = (APP / "api" / "academic_foundation.py").read_text(encoding="utf-8")
		self.assertIn("Next level is missing or disabled.", api)
		self.assertIn('"code": "progression_gap"', api)
		self.assertIn("progression link(s) point to missing or disabled Levels", api)

	def test_foundation_page_exposes_readiness_progression_and_calendar_surfaces(self):
		component = (
			APP
			/ "public"
			/ "js"
			/ "eduedge_academic_foundation"
			/ "EduEdgeAcademicFoundation.vue"
		).read_text(encoding="utf-8")
		for token in (
			"<EdgeDashboardLayout",
			"Foundation Readiness",
			"Progression pathway",
			"Academic calendars",
			"current_period",
			"has_calendar_gap_today",
			"selectedProgression",
			"selectedReadiness",
		):
			self.assertIn(token, component)

	def test_calendar_mutations_use_the_smart_dialog_and_validated_doctype_controller(self):
		bundle = (APP / "public" / "js" / "eduedge_academic_foundation.bundle.js").read_text(encoding="utf-8")
		fixes = (
			APP / "public" / "js" / "eduedge_academic_foundation" / "qa_fixes.js"
		).read_text(encoding="utf-8")
		editor = (APP / "api" / "academic_foundation_editor.py").read_text(encoding="utf-8")
		controller = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_institution_academic_calendar"
			/ "eduedge_institution_academic_calendar.py"
		).read_text(encoding="utf-8")

		self.assertIn("installAcademicFoundationQaFixes", bundle)
		self.assertIn("new frappe.ui.Dialog", fixes)
		self.assertIn("save_academic_calendar", fixes)
		self.assertIn("Open Advanced Form", fixes)
		self.assertIn('doc.check_permission("write")', editor)
		self.assertIn('frappe.has_permission(CALENDAR_DOCTYPE, "create")', editor)
		self.assertIn('doc.set("periods", [])', editor)
		self.assertIn("doc.save()", editor)
		self.assertNotIn("ignore_permissions", editor)
		self.assertNotIn("frappe.db.set_value", editor)
		self.assertIn("_validate_periods", controller)
		self.assertIn("overlaps with", controller)
		self.assertIn("Calendar Institution and Academic Year cannot change after creation", controller)

	def test_selected_institution_drives_foundation_terminology(self):
		fixes = (
			APP / "public" / "js" / "eduedge_academic_foundation" / "qa_fixes.js"
		).read_text(encoding="utf-8")
		editor = (APP / "api" / "academic_foundation_editor.py").read_text(encoding="utf-8")
		self.assertIn("selectedInstitutionTerminology", fixes)
		self.assertIn("get_institution_terminology", fixes)
		self.assertIn('selectedTerm(this, key, plural, fallback)', fixes)
		self.assertIn('termFromContext(context, "academic_term"', fixes)
		self.assertIn("Academic Periods", fixes)
		self.assertIn("get_terminology_map", editor)
		self.assertIn('doc.check_permission("read")', editor)

	def test_section_and_level_descriptions_round_trip_through_the_page_api(self):
		api = (APP / "api" / "academic_foundation.py").read_text(encoding="utf-8")
		self.assertGreaterEqual(api.count('"description"'), 4)


if __name__ == "__main__":
	unittest.main()
