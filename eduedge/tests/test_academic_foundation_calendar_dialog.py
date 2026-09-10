from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAcademicFoundationCalendarDialog(unittest.TestCase):
	def test_page_loader_loads_and_wires_dialog_before_mount(self):
		loader = (
			APP
			/ "eduedge"
			/ "page"
			/ "eduedge_academic_foundation"
			/ "eduedge_academic_foundation.js"
		).read_text()
		for token in (
			'/assets/eduedge/js/academic_foundation_calendar_dialog.js',
			"EduEdgeAcademicCalendarDialog?.open",
			"component.methods.createCalendar = function",
			"institution: this.selectedInstitution",
			"academicYearLabel: this.academicYearSingular",
			"academicTermLabel: this.academicTermPlural",
			"await this.load();",
		):
			self.assertIn(token, loader)
		self.assertLess(
			loader.index("component.methods.createCalendar = function"),
			loader.index("window.createEduEdgeAcademicFoundationApp()"),
		)

	def test_dialog_derives_dates_and_term_preview(self):
		script = (APP / "public" / "js" / "academic_foundation_calendar_dialog.js").read_text()
		for token in (
			"eduedge.api.calendar_setup.get_calendar_dialog_context",
			"eduedge.api.calendar_setup.create_calendar_from_foundation",
			'fieldname: "academic_year"',
			'fieldname: "start_date"',
			'fieldname: "end_date"',
			'fieldname: "term_summary"',
			'await dialog.set_value("start_date", preview?.start_date || "");',
			'await dialog.set_value("end_date", preview?.end_date || "");',
			"preview.periods || []",
			'type: "POST"',
			"onCreated",
		):
			self.assertIn(token, script)
		self.assertNotIn('frappe.new_doc("EduEdge Institution Academic Calendar"', script)

	def test_backend_is_permission_aware_and_builds_periods_server_side(self):
		api = (APP / "api" / "calendar_setup.py").read_text()
		for token in (
			"require_eduedge_access",
			'doc.check_permission("read")',
			'frappe.has_permission(CALENDAR_DOCTYPE, "create")',
			'@frappe.whitelist(methods=["POST"])',
			"create_calendar_from_foundation",
			"frappe.db.exists(",
			'filters={"academic_year": academic_year}',
			"doc = frappe.new_doc(CALENDAR_DOCTYPE)",
			'doc.append(\n\t\t\t"periods"',
			"doc.insert()",
		):
			self.assertIn(token, api)
		for forbidden in (
			"ignore_permissions=True",
			"doc.submit()",
			"frappe.db.set_value",
		):
			self.assertNotIn(forbidden, api)

	def test_existing_calendar_and_incomplete_term_setup_are_blocked(self):
		api = (APP / "api" / "calendar_setup.py").read_text()
		for token in (
			"existing_by_year",
			'"available": not bool(existing_by_year.get(row["name"]))',
			"An Institution Academic Calendar already exists",
			"Create at least one Academic Term",
			"Complete Start Date and End Date for these Academic Terms",
		):
			self.assertIn(token, api)


if __name__ == "__main__":
	unittest.main()
