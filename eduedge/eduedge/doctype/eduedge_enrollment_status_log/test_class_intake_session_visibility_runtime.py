from __future__ import annotations

import frappe
from education.education.test_utils import before_tests
from frappe.tests.utils import FrappeTestCase

from eduedge.api.programme_offering_session_options import (
	get_programme_offering_session_options,
	get_programme_offerings_page_with_sessions,
)
from eduedge.api.programme_offerings_safe import save_programme_offering
from eduedge.education.academic_fields import INSTITUTION_FIELD


class TestClassIntakeSessionVisibilityRuntime(FrappeTestCase):
	"""Academic Session discovery, filtering and Class Intake readiness must remain authoritative."""

	def setUp(self) -> None:
		before_tests()
		frappe.set_user("Administrator")
		self.suffix = frappe.generate_hash(length=8).upper()

	def _insert(self, doctype: str, **values):
		return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)

	def _make_year(self, label: str, start: str, end: str):
		return self._insert(
			"Academic Year",
			academic_year_name=f"QA {label} {self.suffix}",
			year_start_date=start,
			year_end_date=end,
		)

	def _make_institution(self, label: str):
		return self._insert(
			"EduEdge Institution",
			institution_name=f"QA {label} School {self.suffix}",
			institution_code=f"QA{label[:4].upper()}{self.suffix}",
			company="_Test Company",
			institution_type="PRIMARY",
			enabled=1,
		)

	def test_calendarless_future_session_is_visible_in_page_and_editor_options(self):
		year = self._make_year("FUTURE", "2098-09-01", "2099-08-31")
		institution = self._make_institution("Session Visibility")

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

	def test_class_intake_save_prepares_calendar_from_configured_session_terms(self):
		year = self._make_year("AUTO CALENDAR", "2092-09-01", "2093-08-31")
		institution = self._make_institution("Auto Calendar")
		branch = self._insert(
			"EduEdge School Branch",
			branch_name=f"QA Auto Calendar Campus {self.suffix}",
			branch_code=f"QAAUTO{self.suffix}",
			company="_Test Company",
			institution=institution.name,
			enabled=1,
		)
		terms = []
		for label, start, end in (
			("First", "2092-09-01", "2092-12-15"),
			("Second", "2093-01-10", "2093-04-15"),
			("Third", "2093-05-01", "2093-08-15"),
		):
			terms.append(
				self._insert(
					"Academic Term",
					academic_year=year.name,
					term_name=f"QA {label} Term {self.suffix}",
					term_start_date=start,
					term_end_date=end,
				)
			)
		department = self._insert(
			"Department",
			department_name=f"QA Auto Calendar Section {self.suffix}",
			company="_Test Company",
			is_group=0,
			**{INSTITUTION_FIELD: institution.name},
		)
		program = self._insert(
			"Program",
			program_name=f"QA Auto Calendar Class {self.suffix}",
			department=department.name,
			**{INSTITUTION_FIELD: institution.name},
		)
		self.assertFalse(
			frappe.db.exists(
				"EduEdge Institution Academic Calendar",
				{"institution": institution.name, "academic_year": year.name},
			)
		)

		result = save_programme_offering(
			school_branch=branch.name,
			institution=institution.name,
			program=program.name,
			academic_year=year.name,
			offering_title=f"QA Auto Calendar Intake {self.suffix}",
			offering_code=f"QA-AUTO-{self.suffix}",
		)

		calendar = frappe.db.get_value(
			"EduEdge Institution Academic Calendar",
			{"institution": institution.name, "academic_year": year.name, "enabled": 1},
			"name",
		)
		self.assertTrue(calendar)
		periods = frappe.get_all(
			"EduEdge Academic Calendar Period",
			filters={"parent": calendar, "parenttype": "EduEdge Institution Academic Calendar"},
			pluck="academic_term",
			order_by="sequence asc",
		)
		self.assertEqual(periods, [term.name for term in terms])
		self.assertTrue(frappe.db.exists("EduEdge Program Offering", result["name"]))

		# Retrying the same readiness step must reuse the one Institution calendar.
		save_programme_offering(
			school_branch=branch.name,
			institution=institution.name,
			program=program.name,
			academic_year=year.name,
			offering=result["name"],
			offering_title=f"QA Auto Calendar Intake {self.suffix}",
			offering_code=f"QA-AUTO-{self.suffix}",
		)
		self.assertEqual(
			frappe.db.count(
				"EduEdge Institution Academic Calendar",
				{"institution": institution.name, "academic_year": year.name},
			),
			1,
		)

	def test_selected_session_filters_the_class_intake_catalogue(self):
		source_year = self._make_year("FILTER SOURCE", "2095-09-01", "2096-08-31")
		destination_year = self._make_year("FILTER DEST", "2096-09-01", "2097-08-31")
		institution = self._make_institution("Session Filter")
		branch = self._insert(
			"EduEdge School Branch",
			branch_name=f"QA Filter Campus {self.suffix}",
			branch_code=f"QAFILT{self.suffix}",
			company="_Test Company",
			institution=institution.name,
			enabled=1,
		)
		for index, (year, start, end) in enumerate(
			(
				(source_year, "2095-09-01", "2096-08-31"),
				(destination_year, "2096-09-01", "2097-08-31"),
			),
			start=1,
		):
			term = self._insert(
				"Academic Term",
				academic_year=year.name,
				term_name=f"QA Filter Term {index} {self.suffix}",
				term_start_date=start,
				term_end_date=end,
			)
			self._insert(
				"EduEdge Institution Academic Calendar",
				institution=institution.name,
				academic_year=year.name,
				enabled=1,
				start_date=start,
				end_date=end,
				periods=[
					{
						"academic_term": term.name,
						"start_date": start,
						"end_date": end,
						"sequence": 10,
					}
				],
			)

		department = self._insert(
			"Department",
			department_name=f"QA Filter Section {self.suffix}",
			company="_Test Company",
			is_group=0,
			**{INSTITUTION_FIELD: institution.name},
		)
		program = self._insert(
			"Program",
			program_name=f"QA Filter Class {self.suffix}",
			department=department.name,
			**{INSTITUTION_FIELD: institution.name},
		)
		source_offering = self._insert(
			"EduEdge Program Offering",
			school_branch=branch.name,
			program=program.name,
			academic_year=source_year.name,
			offering_title=f"QA Source Intake {self.suffix}",
			offering_code=f"QA-SRC-{self.suffix}",
			study_mode="Full-Time",
			delivery_mode="Onsite",
			is_active=1,
			admission_enabled=1,
			enrollment_enabled=1,
		)
		destination_offering = self._insert(
			"EduEdge Program Offering",
			school_branch=branch.name,
			program=program.name,
			academic_year=destination_year.name,
			offering_title=f"QA Destination Intake {self.suffix}",
			offering_code=f"QA-DST-{self.suffix}",
			study_mode="Full-Time",
			delivery_mode="Onsite",
			is_active=1,
			admission_enabled=1,
			enrollment_enabled=1,
		)

		source_page = get_programme_offerings_page_with_sessions(
			institution=institution.name,
			branch=branch.name,
			academic_year=source_year.name,
		)
		self.assertEqual(source_page["filters"]["academic_year"], source_year.name)
		self.assertEqual({row["name"] for row in source_page["offerings"]}, {source_offering.name})
		self.assertTrue(all(row["academic_year"] == source_year.name for row in source_page["offerings"]))

		destination_page = get_programme_offerings_page_with_sessions(
			institution=institution.name,
			branch=branch.name,
			academic_year=destination_year.name,
		)
		self.assertEqual(destination_page["filters"]["academic_year"], destination_year.name)
		self.assertEqual(
			{row["name"] for row in destination_page["offerings"]},
			{destination_offering.name},
		)
		self.assertTrue(
			all(row["academic_year"] == destination_year.name for row in destination_page["offerings"])
		)
