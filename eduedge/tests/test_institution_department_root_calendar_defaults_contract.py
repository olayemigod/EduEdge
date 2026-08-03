from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstitutionDepartmentRootCalendarDefaultsContract(unittest.TestCase):
	def test_department_root_is_institution_owned_hidden_and_idempotent(self):
		helper = (APP / "education" / "institution_department_root.py").read_text()
		hierarchy = (APP / "education" / "academic_hierarchy.py").read_text()
		migration = (APP / "education" / "native_hierarchy_migration.py").read_text()
		for expected in (
			'INSTITUTION_ROOT_FLAG = "eduedge_is_institution_root"',
			'INSTITUTION_ROOT_OWNER = "eduedge_root_institution"',
			"ensure_institution_department_root_fields",
			"ensure_institution_department_root",
			"normalise_institution_department_roots",
			'"hidden": 1',
			'"read_only": 1',
		):
			self.assertIn(expected, helper)
		for expected in (
			"if not parent or parent in company_roots:",
			"ensure_institution_department_root(institution)",
			"Institution root must belong to the selected Institution.",
			"Institution academic roots are managed by EduEdge.",
		):
			self.assertIn(expected, hierarchy)
		self.assertIn("ensure_institution_department_root_fields()", migration)
		self.assertIn("normalise_institution_department_roots(ignore_permissions=True)", migration)

	def test_calendar_derives_year_and_term_dates_in_ui_and_backend(self):
		controller = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_institution_academic_calendar"
			/ "eduedge_institution_academic_calendar.py"
		).read_text()
		client = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_institution_academic_calendar"
			/ "eduedge_institution_academic_calendar.js"
		).read_text()
		for expected in (
			"_apply_academic_year_and_term_defaults",
			'"year_start_date", "year_end_date"',
			'filters={"academic_year": self.academic_year}',
			"if not self.periods and terms:",
			"row.start_date = term.term_start_date",
			"row.end_date = term.term_end_date",
		):
			self.assertIn(expected, controller)
		for expected in (
			"applyAcademicYearDefaults",
			"getAcademicTerms",
			'frm.clear_table("periods")',
			'frm.set_query("academic_term", "periods"',
			"applyAcademicTermDefaults",
			'frm.set_df_property("academic_year", "read_only"',
		):
			self.assertIn(expected, client)


if __name__ == "__main__":
	unittest.main()
