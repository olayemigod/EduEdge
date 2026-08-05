from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestTeacherAssignmentBulkContract(unittest.TestCase):
	def test_unified_page_supports_multi_branch_class_arm_and_subject_selection(self):
		component = (APP / "public" / "js" / "eduedge_instructor_assignments" / "EduEdgeInstructorAssignments.vue").read_text(encoding="utf-8")
		for token in (
			"Teacher Assignments",
			"Assign one teacher to multiple Branches, Classes, Class Arms and Subjects",
			"Branches / Campuses",
			"Classes / Programme Offerings",
			"Class Arms",
			"form.branches.includes",
			"form.program_offerings.includes",
			"form.student_groups.includes",
			"form.courses.includes",
			"Preview Assignment Batch",
		):
			self.assertIn(token, component)

	def test_batch_planner_builds_one_document_per_valid_combination(self):
		api = (APP / "api" / "teacher_assignments.py").read_text(encoding="utf-8")
		for token in (
			"class PlannedAssignment",
			"for offering, group in targets:",
			"for course in candidate_courses:",
			"Subject is not configured for this Class",
			"valid_combinations",
			"create_count",
			"existing_count",
			"conflict_count",
			"frappe.new_doc(\"EduEdge Instructor Assignment\")",
		):
			self.assertIn(token, api)

	def test_exact_existing_records_are_skipped_and_overlaps_block_save(self):
		api = (APP / "api" / "teacher_assignments.py").read_text(encoding="utf-8")
		self.assertIn("_classify_existing", api)
		self.assertIn("existing.append", api)
		self.assertIn("Overlapping active assignment", api)
		self.assertIn("if conflicts:", api)
		self.assertIn("Resolve the existing assignments before saving", api)
		self.assertNotIn("ignore_permissions", api)

	def test_same_page_maintains_background_branch_eligibility(self):
		api = (APP / "api" / "teacher_assignments.py").read_text(encoding="utf-8")
		component = (APP / "public" / "js" / "eduedge_instructor_assignments" / "EduEdgeInstructorAssignments.vue").read_text(encoding="utf-8")
		for token in (
			"BRANCH_ONLY_SCOPE",
			"_ensure_branch_assignment",
			'frappe.new_doc("EduEdge Instructor Branch Assignment")',
			"branches_created_or_updated",
		):
			self.assertIn(token, api)
		self.assertIn("Branch Access Only", component)
		self.assertIn("Branch Access", component)
		self.assertNotIn("/app/eduedge-instructor-branch-assignment", component)

	def test_assignment_scope_is_migrated_and_class_arm_is_conditional(self):
		metadata = json.loads((APP / "eduedge" / "doctype" / "eduedge_instructor_assignment" / "eduedge_instructor_assignment.json").read_text(encoding="utf-8"))
		service = (APP / "education" / "teaching_assignments.py").read_text(encoding="utf-8")
		install = (APP / "install.py").read_text(encoding="utf-8")
		fields = {row.get("fieldname"): row for row in metadata["fields"]}
		self.assertIn("assignment_scope", fields)
		self.assertIn("Class / Programme Offering", fields["assignment_scope"]["options"])
		self.assertIn("Class Arm", fields["assignment_scope"]["options"])
		self.assertIn("mandatory_depends_on", fields["student_group"])
		self.assertIn("ensure_teaching_assignment_foundation", service)
		self.assertIn("when ifnull(student_group, '') != ''", service)
		self.assertIn("ensure_teaching_assignment_foundation()", install)

	def test_class_wide_assignment_is_reused_by_schedule_validation(self):
		helper = (APP / "education" / "instructor_assignments.py").read_text(encoding="utf-8")
		self.assertIn("scope == CLASS_SCOPE", helper)
		self.assertIn("row.program_offering != program_offering", helper)
		self.assertIn("row.student_group != doc.student_group", helper)
		self.assertIn("row.course != doc.get(\"course\")", helper)


if __name__ == "__main__":
	unittest.main()
