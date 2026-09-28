from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from eduedge.eduedge.doctype.eduedge_institution_academic_calendar.eduedge_institution_academic_calendar import (
	EduEdgeInstitutionAcademicCalendar,
)


class TestEduEdgeInstitutionAcademicCalendar(FrappeTestCase):
	def _calendar(self, first_sequence: int, second_sequence: int):
		return frappe._dict(
			{
				"academic_year": "2094-2095",
				"start_date": "2094-09-01",
				"end_date": "2095-08-31",
				"periods": [
					frappe._dict(
						{
							"academic_term": "TERM-1",
							"start_date": "2094-09-01",
							"end_date": "2094-12-20",
							"sequence": first_sequence,
							"result_publication_date": None,
						}
					),
					frappe._dict(
						{
							"academic_term": "TERM-2",
							"start_date": "2095-01-10",
							"end_date": "2095-04-10",
							"sequence": second_sequence,
							"result_publication_date": None,
						}
					),
				],
			}
		)

	def test_period_sequence_must_follow_chronological_dates(self):
		calendar = self._calendar(20, 10)
		with patch(
			"eduedge.eduedge.doctype.eduedge_institution_academic_calendar.eduedge_institution_academic_calendar.frappe.db.get_value",
			return_value="2094-2095",
		):
			with self.assertRaises(frappe.ValidationError):
				EduEdgeInstitutionAcademicCalendar._validate_periods(calendar)

	def test_positive_chronological_period_sequences_are_valid(self):
		calendar = self._calendar(10, 20)
		with patch(
			"eduedge.eduedge.doctype.eduedge_institution_academic_calendar.eduedge_institution_academic_calendar.frappe.db.get_value",
			return_value="2094-2095",
		):
			EduEdgeInstitutionAcademicCalendar._validate_periods(calendar)


if __name__ == "__main__":
	import unittest

	unittest.main()
