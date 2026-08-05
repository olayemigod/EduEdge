from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorSubjectVisibilityAndBranchSummaryContract(unittest.TestCase):
	def test_assignment_page_exposes_institution_subjects_and_exact_curriculum_membership(self):
		api = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
		bundle = (APP / "public" / "js" / "eduedge_instructor_assignments.bundle.js").read_text(encoding="utf-8")
		for token in (
			"_course_options",
			"Institution subjects",
			"configured_course_map",
			"course_map",
			"curriculum_change_count",
			"curriculum_changes",
			"Institution Subject will be added to the selected Class curriculum",
			"add to Class curriculum",
		):
			self.assertIn(token, api)
		for token in (
			"labelInstitutionSubjectsByClassMembership",
			"configured_course_map",
			"eduedge_configured_in_class",
			"Add to Class curriculum",
		):
			self.assertIn(token, bundle)

	def test_missing_class_subject_is_added_through_native_program_courses(self):
		api = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
		for token in (
			"_apply_curriculum_additions",
			'frappe.get_doc("Program", program)',
			'doc.append("courses", {"course": course, "required": 1})',
			"doc.check_permission(\"write\")",
			"class_curriculum_subjects_added",
		):
			self.assertIn(token, api)
		self.assertNotIn("ignore_permissions", api)
		self.assertNotIn("frappe.db.set_value", api)

	def test_instructor_profile_summarises_distinct_branches_without_deleting_periods(self):
		api = (APP / "api" / "instructor_profiles.py").read_text(encoding="utf-8")
		for token in (
			"_summarise_branch_eligibility",
			"one profile card per Branch",
			'grouped.setdefault(branch, []).append(row)',
			'"branch_eligibility_periods"',
			'"period_count"',
			'"periods": periods',
		):
			self.assertIn(token, api)
		self.assertNotIn("delete_doc", api)


if __name__ == "__main__":
	unittest.main()
