from __future__ import annotations

import frappe
from education.education.test_utils import before_tests
from frappe.tests.utils import FrappeTestCase

from eduedge.api.programme_offering_session_options import (
	get_programme_offering_session_options,
	get_programme_offerings_page_with_sessions,
)


class TestClassIntakeSessionVisibilityRuntime(FrappeTestCase):
	"""Calendar readiness must never hide a readable future Academic Session."""

	def setUp(self) -> None:
		before_tests()
		frappe.set_user("Administrator")
		self.suffix = frappe.generate_hash(length=8).upper()

	def test_calendarless_future_session_is_visible_in_page_and_editor_options(self):
		year = frappe.get_doc(
			{
				"doctype": "Academic Year",
				"academic_year_name": f"QA FUTURE {self.suffix}",
				"year_start_date": "2098-09-01",
				"year_end_date": "2099-08-31",
			}
		).insert(ignore_permissions=True)
		institution = frappe.get_doc(
			{
				"doctype": "EduEdge Institution",
				"institution_name": f"QA Session Visibility School {self.suffix}",
				"institution_code": f"QASVIS{self.suffix}",
				"company": "_Test Company",
				"institution_type": "PRIMARY",
				"enabled": 1,
			}
		).insert(ignore_permissions=True)

		self.assertFalse(
			frappe.db.exists(
				"EduEdge Institution Academic Calendar",
				{"institution": institution.name, "academic_year": year.name},
			)
		)

		page = get_programme_offerings_page_with_sessions(institution=institution.name)
		page_years = {row["name"]: row for row in page["options"]["academic_years"]}
		self.assertIn(year.name, page_years)
		self.assertFalse(page_years[year.name]["calendar_ready"])

		editor = get_programme_offering_session_options(institution=institution.name)
		editor_years = {row["name"]: row for row in editor["options"]["academic_years"]}
		self.assertIn(year.name, editor_years)
		self.assertFalse(editor_years[year.name]["calendar_ready"])
