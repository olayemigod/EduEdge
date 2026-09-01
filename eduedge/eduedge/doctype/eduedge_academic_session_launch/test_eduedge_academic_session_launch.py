from __future__ import annotations

import frappe
from education.education.test_utils import before_tests
from frappe.tests.utils import FrappeTestCase

from eduedge.api.session_launch import (
	get_session_launch_context,
	prepare_session_foundation,
	save_session_launch_progress,
	start_or_resume_session_launch,
)

# Frappe v16 recursively creates test records for Link dependencies of a DocType.
# This test creates its Institution, Academic Sessions and users/context explicitly;
# recursively following Institution -> Company pulls unrelated ERPNext/Education
# masters (for example Grading Scale) through production institution-governance
# hooks before this test can run. Keep the test dependency graph bounded instead of
# weakening production validation or adding CI-only business masters.
IGNORE_TEST_RECORD_DEPENDENCIES = ["EduEdge Institution", "Academic Year", "User"]


class TestEduEdgeAcademicSessionLaunch(FrappeTestCase):
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

	def _make_institution(self):
		return self._insert(
			"EduEdge Institution",
			institution_name=f"QA Session Launch School {self.suffix}",
			institution_code=f"QASL{self.suffix}",
			company="_Test Company",
			institution_type="SECONDARY",
			enabled=1,
		)

	def test_launch_persists_current_step_and_resumes_same_record(self):
		source = self._make_year("LAUNCH SOURCE", "2090-09-01", "2091-08-31")
		target = self._make_year("LAUNCH TARGET", "2091-09-01", "2092-08-31")
		institution = self._make_institution()
		for label, start, end in (
			("First", "2091-09-01", "2091-12-15"),
			("Second", "2092-01-10", "2092-04-15"),
			("Third", "2092-05-01", "2092-08-15"),
		):
			self._insert(
				"Academic Term",
				academic_year=target.name,
				term_name=f"QA {label} Term {self.suffix}",
				term_start_date=start,
				term_end_date=end,
			)

		started = start_or_resume_session_launch(
			academic_year=target.name,
			institution=institution.name,
			source_academic_year=source.name,
		)
		launch = started["launch"]
		self.assertTrue(launch["name"])
		self.assertEqual(launch["status"], "Preparing")
		self.assertEqual(launch["current_step_key"], "session_terms")
		self.assertEqual(launch["source_academic_year"], source.name)
		self.assertFalse(
			frappe.db.exists(
				"EduEdge Institution Academic Calendar",
				{"institution": institution.name, "academic_year": target.name},
			)
		)

		prepared = prepare_session_foundation(launch["name"])
		self.assertTrue(prepared["calendar"]["name"])
		self.assertEqual(prepared["launch"]["current_step_key"], "class_structure")
		step_one = next(row for row in prepared["readiness"]["steps"] if row["key"] == "session_terms")
		self.assertTrue(step_one["ready"])

		saved = save_session_launch_progress(
			launch=launch["name"],
			current_step="class_intakes",
			source_academic_year=source.name,
			notes="Paused after reviewing the Class structure.",
		)
		self.assertEqual(saved["launch"]["current_step_key"], "class_intakes")
		self.assertEqual(saved["launch"]["notes"], "Paused after reviewing the Class structure.")

		resumed = start_or_resume_session_launch(
			academic_year=target.name,
			institution=institution.name,
			source_academic_year=source.name,
		)
		self.assertEqual(resumed["launch"]["name"], launch["name"])
		self.assertEqual(resumed["launch"]["current_step_key"], "class_intakes")
		self.assertEqual(
			frappe.db.count(
				"EduEdge Academic Session Launch",
				{"institution": institution.name, "academic_year": target.name},
			),
			1,
		)

		loaded = get_session_launch_context(academic_year=target.name, institution=institution.name)
		self.assertEqual(loaded["launch"]["name"], launch["name"])
		self.assertEqual(loaded["launch"]["current_step_key"], "class_intakes")
		self.assertEqual(loaded["launch"]["source_academic_year"], source.name)
