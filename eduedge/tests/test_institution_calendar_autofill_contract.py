from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstitutionCalendarAutofillContract(unittest.TestCase):
	def test_calendar_client_script_is_registered(self):
		hooks = (APP / "hooks.py").read_text()
		self.assertIn(
			'"EduEdge Institution Academic Calendar": '
			'"eduedge/doctype/eduedge_institution_academic_calendar/'
			'eduedge_institution_academic_calendar.js"',
			hooks,
		)

	def test_client_autofill_uses_year_and_term_dates(self):
		script = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_institution_academic_calendar"
			/ "eduedge_institution_academic_calendar.js"
		).read_text()
		for token in (
			'"year_start_date", "year_end_date"',
			'filters: { academic_year: academicYear }',
			'"term_start_date", "term_end_date"',
			'frm.clear_table("periods")',
			'row.academic_term = term.name',
			'frm.set_query("academic_term", "periods"',
		):
			self.assertIn(token, script)

	def test_server_autofill_remains_available(self):
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
