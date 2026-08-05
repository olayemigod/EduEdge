from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestClassAwareAcademicContentContract(unittest.TestCase):
	def test_cbt_question_records_store_branch_class_arm_and_subject_context(self):
		metadata = json.loads((APP / "eduedge" / "doctype" / "eduedge_cbt_question" / "eduedge_cbt_question.json").read_text(encoding="utf-8"))
		fields = {row.get("fieldname") for row in metadata["fields"]}
		for fieldname in ("school_branch", "institution", "program_offering", "student_group", "course", "topic"):
			self.assertIn(fieldname, fields)
		self.assertIn("program_offering", metadata["search_fields"])
		self.assertIn("student_group", metadata["search_fields"])

	def test_question_builder_exposes_and_filters_the_assigned_class_context(self):
		component = (APP / "public" / "js" / "eduedge_question_builder" / "EduEdgeQuestionBuilder.vue").read_text(encoding="utf-8")
		api = (APP / "api" / "question_builder.py").read_text(encoding="utf-8")
		for token in (
			"Class / Programme Offering",
			"Class Arm / Student Group",
			"Select assigned Class",
			"Subject choices are limited to your active Teacher Assignment",
			"get_question_academic_options",
		):
			self.assertIn(token, component)
		for token in (
			"get_question_academic_options",
			"assigned_courses",
			"program_offering",
			"student_group",
			"_program_courses",
		):
			self.assertIn(token, api)

	def test_question_doctype_rejects_unassigned_or_cross_context_content(self):
		controller = (APP / "eduedge" / "doctype" / "eduedge_cbt_question" / "eduedge_cbt_question.py").read_text(encoding="utf-8")
		for token in (
			"Assigned teachers must select the Class / Programme Offering for a CBT question.",
			"Subject / Course is not configured for the selected Class / Programme.",
			"require_course_assignment",
			"Class Arm must belong to the selected Class / Programme Offering.",
			"Topic is not available in the selected Class.",
			"Topic is not available in the selected Class Arm.",
			"same Question Bank, Branch, Class context, and Subject / Course",
		):
			self.assertIn(token, controller)

	def test_assessment_plan_native_validation_uses_same_teacher_assignment_scope(self):
		assessment = (APP / "education" / "assessment_operations.py").read_text(encoding="utf-8")
		for token in (
			"is_teacher_user",
			"require_course_assignment",
			"program_offering=program_offering",
			"student_group=doc.student_group",
			"_resolve_group_offering",
		):
			self.assertIn(token, assessment)
		self.assertNotIn("ignore_permissions", assessment)

	def test_course_schedule_uses_the_same_class_or_class_arm_scope(self):
		schedule = (APP / "education" / "instructor_assignments.py").read_text(encoding="utf-8")
		self.assertIn("CLASS_SCOPE", schedule)
		self.assertIn("CLASS_ARM_SCOPE", schedule)
		self.assertIn("_group_offering", schedule)
		self.assertIn("program_offering", schedule)


if __name__ == "__main__":
	unittest.main()
