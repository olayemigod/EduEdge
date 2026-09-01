from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAcademicFoundationReadinessContract(unittest.TestCase):
	def test_foundation_api_returns_native_hierarchy_calendars_and_readiness(self):
		api = (APP / "api" / "academic_foundation_safe.py").read_text(encoding="utf-8")
		for token in (
			"_departments",
			"_programmes",
			"_student_groups",
			"_calendars",
			"_build_hierarchy",
			"_effective_calendar",
			"_build_readiness",
			'"can_write_calendar"',
		):
			self.assertIn(token, api)

	def test_calendar_readiness_keeps_intentional_gaps_visible(self):
		api = (APP / "api" / "academic_foundation_safe.py").read_text(encoding="utf-8")
		self.assertIn('"code": "calendar_gap"', api)
		self.assertIn("outside every configured Term / Semester", api)
		self.assertIn('"code": "calendar_without_periods"', api)
		self.assertNotIn("Education Settings", api)

	def test_hierarchy_readiness_reports_missing_native_context(self):
		api = (APP / "api" / "academic_foundation_safe.py").read_text(encoding="utf-8")
		self.assertIn('"code": "no_departments"', api)
		self.assertIn('"code": "no_programmes"', api)
		self.assertIn('"code": "programmes_without_department"', api)
		self.assertIn('"code": "incomplete_student_groups"', api)

	def test_foundation_page_exposes_native_hierarchy_and_calendar_surfaces(self):
		component = (APP / "public" / "js" / "eduedge_academic_foundation" / "EduEdgeAcademicFoundation.vue").read_text(encoding="utf-8")
		for token in (
			"<EdgeDashboardLayout",
			"Foundation Readiness",
			"Configured native hierarchy",
			"Institution calendar",
			"flatDepartments",
			"programme.student_groups",
			"has_calendar_gap_today",
			"createStudentGroup",
		):
			self.assertIn(token, component)
		self.assertIn("Department", component)
		self.assertNotIn("Progression pathway", component)

	def test_calendar_mutations_use_smart_dialog_and_validated_controller(self):
		bundle = (APP / "public" / "js" / "eduedge_academic_foundation.bundle.js").read_text(encoding="utf-8")
		fixes = (APP / "public" / "js" / "eduedge_academic_foundation" / "qa_fixes.js").read_text(encoding="utf-8")
		editor = (APP / "api" / "academic_foundation_editor.py").read_text(encoding="utf-8")
		controller = (APP / "eduedge" / "doctype" / "eduedge_institution_academic_calendar" / "eduedge_institution_academic_calendar.py").read_text(encoding="utf-8")
		self.assertIn("installAcademicFoundationQaFixes", bundle)
		self.assertIn("new frappe.ui.Dialog", fixes)
		self.assertIn("save_academic_calendar", fixes)
		self.assertIn("Open Advanced Form", fixes)
		self.assertIn('doc.check_permission("write")', editor)
		self.assertIn('frappe.has_permission(CALENDAR_DOCTYPE, "create")', editor)
		self.assertIn('doc.set("periods", [])', editor)
		self.assertIn("doc.save()", editor)
		self.assertNotIn("ignore_permissions", editor)
		self.assertIn("_validate_periods", controller)
		self.assertIn("overlaps with", controller)
		self.assertIn("Calendar Institution and Academic Year cannot change after creation", controller)

	def test_selected_institution_drives_calendar_terminology(self):
		fixes = (APP / "public" / "js" / "eduedge_academic_foundation" / "qa_fixes.js").read_text(encoding="utf-8")
		editor = (APP / "api" / "academic_foundation_editor.py").read_text(encoding="utf-8")
		self.assertIn("selectedInstitutionTerminology", fixes)
		self.assertIn("get_institution_terminology", fixes)
		self.assertIn('termFromContext(context, "academic_term"', fixes)
		self.assertIn("get_terminology_map", editor)
		self.assertIn('doc.check_permission("read")', editor)

	def test_native_quick_editors_preserve_full_forms(self):
		component = (APP / "public" / "js" / "eduedge_academic_foundation" / "EduEdgeAcademicFoundation.vue").read_text(encoding="utf-8")
		api = (APP / "api" / "academic_foundation_safe.py").read_text(encoding="utf-8")
		self.assertIn("saveDepartment", component)
		self.assertIn("saveProgramme", component)
		self.assertIn('frappe.set_route("Form", "Department", name)', component)
		self.assertIn('frappe.set_route("Form", "Program", name)', component)
		self.assertIn("save_department", api)


if __name__ == "__main__":
	unittest.main()
