from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]


class TestProgramOfferingContract(unittest.TestCase):
	def test_program_offering_doctype_has_required_context(self):
		path = (
			ROOT
			/ "eduedge"
			/ "eduedge"
			/ "doctype"
			/ "eduedge_program_offering"
			/ "eduedge_program_offering.json"
		)
		payload = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in payload["fields"]}
		for fieldname in (
			"school_branch",
			"program",
			"academic_year",
			"academic_term",
			"admission_enabled",
			"enrollment_enabled",
		):
			self.assertIn(fieldname, fields)

	def test_student_admission_receives_branch_context(self):
		text = (ROOT / "eduedge" / "education" / "custom_fields.py").read_text()
		self.assertIn('"Student Admission": [', text)
		self.assertIn('"eduedge_school_branch"', text)

	def test_program_queries_are_offering_backed(self):
		text = (ROOT / "eduedge" / "api" / "education.py").read_text()
		self.assertIn("tabEduEdge Program Offering", text)
		self.assertIn("admission_enabled", (ROOT / "eduedge" / "education" / "offerings.py").read_text())
		self.assertIn("enrollment_enabled", (ROOT / "eduedge" / "education" / "offerings.py").read_text())

	def test_upstream_enrollment_api_is_not_overridden(self):
		text = (ROOT / "eduedge" / "hooks.py").read_text()
		self.assertNotIn("override_whitelisted_methods", text)
		self.assertIn('"Student Admission"', text)
		self.assertIn('"EduEdge Program Offering"', text)

	def test_application_dates_are_not_forced_inside_academic_year(self):
		text = (
			ROOT
			/ "eduedge"
			/ "eduedge"
			/ "doctype"
			/ "eduedge_program_offering"
			/ "eduedge_program_offering.py"
		).read_text()
		self.assertNotIn("year_start_date", text)
		self.assertNotIn("term_start_date", text)


if __name__ == "__main__":
	unittest.main()
