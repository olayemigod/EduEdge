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

	def test_generic_erpnext_department_bootstrap_remains_available_but_programme_use_is_strict(self):
		hierarchy = (APP / "education" / "academic_hierarchy.py").read_text()
		department = hierarchy.split("def before_validate_department", 1)[1].split("def _validate_managed_institution_root", 1)[0]
		programme_guard = hierarchy.split("def _validate_department", 1)[1]
		self.assertIn("Department is a native ERPNext company master too", department)
		self.assertIn("if not institution:", department)
		self.assertIn("return", department.split("if not institution:", 1)[1].split("institution_row =", 1)[0])
		self.assertNotIn("Institution is required for an academic Department / School Section", department)
		self.assertIn(
			"Assign the Department / School Section to an Institution before using it on a Programme.",
			programme_guard,
		)

	def test_department_root_normalisation_is_cycle_safe(self):
		helper = (APP / "education" / "institution_department_root.py").read_text()
		for expected in (
			"def _department_is_ancestor_of(ancestor: str, descendant: str) -> bool:",
			'frappe.db.get_value("Department", current, "parent_department")',
			"if row.name in company_roots:",
			"frappe.db.set_value(",
			"update_modified=False",
			"if _department_is_ancestor_of(row.name, institution_root):",
		):
			self.assertIn(expected, helper)
		self.assertLess(
			helper.index("if row.name in company_roots:"),
			helper.index("doc = frappe.get_doc(\"Department\", row.name)"),
		)
		self.assertLess(
			helper.index("if _department_is_ancestor_of(row.name, institution_root):"),
			helper.index("doc = frappe.get_doc(\"Department\", row.name)"),
		)

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
