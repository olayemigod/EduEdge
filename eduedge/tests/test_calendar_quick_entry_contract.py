from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestCalendarQuickEntryContract(unittest.TestCase):
	def test_global_quick_entry_adapter_is_loaded_before_command_early_return(self):
		script = (APP / "public" / "js" / "eduedge_keyboard_shortcuts.js").read_text()
		self.assertIn('const CALENDAR_DOCTYPE = "EduEdge Institution Academic Calendar";', script)
		self.assertIn('const CALENDAR_QUICK_ENTRY_MARKER = "__eduedgeCalendarQuickEntryAdapter";', script)
		self.assertIn("installCalendarQuickEntryAdapter();", script)
		self.assertLess(
			script.index("installCalendarQuickEntryAdapter();"),
			script.index('if (window.EdgeSuiteCommands?.version === COMMAND_VERSION) return;'),
		)

	def test_adapter_wraps_only_calendar_quick_entry_and_preserves_existing_callback(self):
		script = (APP / "public" / "js" / "eduedge_keyboard_shortcuts.js").read_text()
		for token in (
			"const originalMakeQuickEntry = formApi.make_quick_entry;",
			"formApi.make_quick_entry = function",
			"doctype !== CALENDAR_DOCTYPE",
			'if (typeof initCallback === "function") initCallback(target);',
			"setupCalendarQuickEntry(target);",
			"originalMakeQuickEntry.call(",
		):
			self.assertIn(token, script)

	def test_quick_entry_autofills_year_dates_terms_and_period_rows(self):
		script = (APP / "public" / "js" / "eduedge_keyboard_shortcuts.js").read_text()
		for token in (
			'frappe.db.get_value("Academic Year", academicYear, ["year_start_date", "year_end_date"])',
			'frappe.db.get_list("Academic Term", {',
			'filters: { academic_year: academicYear }',
			'await entry.set_value("start_date", year.year_start_date || "");',
			'await entry.set_value("end_date", year.year_end_date || "");',
			'frappe.model.clear_table(entry.doc, "periods");',
			'frappe.model.add_child(entry.doc, CALENDAR_PERIOD_DOCTYPE, "periods")',
			"row.sequence = (index + 1) * 10;",
			"renderCalendarQuickEntrySummary(entry, academicYear, year, terms);",
		):
			self.assertIn(token, script)

	def test_server_side_calendar_defaults_remain_as_fallback(self):
		controller = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_institution_academic_calendar"
			/ "eduedge_institution_academic_calendar.py"
		).read_text()
		for token in (
			"self._apply_academic_year_and_term_defaults()",
			'"year_start_date", "year_end_date"',
			'filters={"academic_year": self.academic_year}',
			'if not self.periods and terms:',
			'if not row.start_date:',
			'if not row.end_date:',
		):
			self.assertIn(token, controller)


if __name__ == "__main__":
	unittest.main()
