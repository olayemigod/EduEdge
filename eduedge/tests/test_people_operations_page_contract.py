from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestPeopleOperationsPageContract(unittest.TestCase):
	def test_student_page_replaces_generic_resource_wrapper(self):
		loader = (APP / "eduedge" / "page" / "eduedge_students" / "eduedge_students.js").read_text(encoding="utf-8")
		component = (APP / "public" / "js" / "eduedge_students" / "EduEdgeStudents.vue").read_text(encoding="utf-8")
		self.assertIn("edgesuite_ui.bundle.js", loader)
		self.assertIn("eduedge_students.bundle.js", loader)
		self.assertNotIn("registerEduEdgeResourcePage", loader)
		for token in (
			"Official photograph",
			"Parents and guardians",
			"Submitted enrolments",
			"Active Class Arms",
			"set_student_photo",
			"review_student_photo",
			"canManagePhoto",
		):
			self.assertIn(token, component)

	def test_student_photo_governance_is_locked_audited_and_type_checked(self):
		fields = (APP / "education" / "people_fields.py").read_text(encoding="utf-8")
		governance = (APP / "education" / "people_governance.py").read_text(encoding="utf-8")
		api = (APP / "api" / "people_operations.py").read_text(encoding="utf-8")
		log_json = json.loads((APP / "eduedge" / "doctype" / "eduedge_student_photo_review_log" / "eduedge_student_photo_review_log.json").read_text(encoding="utf-8"))
		log_controller = (APP / "eduedge" / "doctype" / "eduedge_student_photo_review_log" / "eduedge_student_photo_review_log.py").read_text(encoding="utf-8")
		for token in (
			"eduedge_photo_status",
			"eduedge_photo_locked",
			"eduedge_photo_approved_by",
			"eduedge_photo_approved_on",
		):
			self.assertIn(token, fields)
		self.assertIn("Students cannot replace or remove the official Student photo", governance)
		self.assertIn("_inherit_approved_applicant_photo", governance)
		self.assertIn("Only genuine JPG, PNG, and WebP images are allowed", api)
		self.assertIn("MAX_IMAGE_BYTES = 2 * 1024 * 1024", api)
		self.assertIn('doc.set(PHOTO_LOCKED_FIELD, 1 if decision == "Approved" else 0)', api)
		self.assertIn("EduEdge Student Photo Review Log", api)
		self.assertEqual(log_json["name"], "EduEdge Student Photo Review Log")
		self.assertIn("append-only", log_controller)

	def test_student_and_instructor_saves_use_native_documents(self):
		api = (APP / "api" / "people_operations.py").read_text(encoding="utf-8")
		for token in (
			'frappe.new_doc("Student")',
			'frappe.new_doc("Instructor")',
			'doc.set("guardians", [])',
			'doc.append("guardians"',
			"doc.save()",
			"_ensure_branch_eligibility",
		):
			self.assertIn(token, api)
		self.assertNotIn("ignore_permissions", api)

	def test_instructor_page_and_assignment_page_are_edgesuite_surfaces(self):
		for page_name, bundle_name in (
			("eduedge_instructors", "eduedge_instructors.bundle.js"),
			("eduedge_instructor_assignments", "eduedge_instructor_assignments.bundle.js"),
		):
			page_dir = APP / "eduedge" / "page" / page_name
			page_json = json.loads((page_dir / f"{page_name}.json").read_text(encoding="utf-8"))
			loader = (page_dir / f"{page_name}.js").read_text(encoding="utf-8")
			self.assertEqual(page_json["roles"], [])
			self.assertLess(loader.index("edgesuite_ui.bundle.js"), loader.index(bundle_name))

		instructors = (APP / "public" / "js" / "eduedge_instructors" / "EduEdgeInstructors.vue").read_text(encoding="utf-8")
		for token in (
			"Qualification",
			"Specialisation",
			"Employment type",
			"Instructor Assignments",
			"set_instructor_photo",
		):
			self.assertIn(token, instructors)

		assignments = (APP / "public" / "js" / "eduedge_instructor_assignments" / "EduEdgeInstructorAssignments.vue").read_text(encoding="utf-8")
		for token in (
			"Programme Offering",
			"Class Arm / Student Group",
			"Assignment type",
			"get_instructor_assignment_options",
			"save_instructor_assignment",
			"Branch eligibility remains a background governance rule",
		):
			self.assertIn(token, assignments)

	def test_assignment_doctype_validates_academic_truth(self):
		doctype_json = json.loads((APP / "eduedge" / "doctype" / "eduedge_instructor_assignment" / "eduedge_instructor_assignment.json").read_text(encoding="utf-8"))
		controller = (APP / "eduedge" / "doctype" / "eduedge_instructor_assignment" / "eduedge_instructor_assignment.py").read_text(encoding="utf-8")
		self.assertEqual(doctype_json["name"], "EduEdge Instructor Assignment")
		for fieldname in ("instructor", "school_branch", "program_offering", "student_group", "course", "assignment_type"):
			self.assertIn(fieldname, {row.get("fieldname") for row in doctype_json["fields"]})
		for token in (
			"_apply_offering_context",
			"_validate_group_context",
			"_validate_instructor_context",
			"_validate_course_context",
			"_validate_duplicate",
			"Instructor is not eligible for the selected Branch",
			"An overlapping active Instructor Assignment already exists",
		):
			self.assertIn(token, controller)

	def test_schedule_enforcement_is_backward_compatible_until_branch_activation(self):
		helper = (APP / "education" / "instructor_assignments.py").read_text(encoding="utf-8")
		branching = (APP / "education" / "branching.py").read_text(encoding="utf-8")
		self.assertIn('if not frappe.db.exists(ASSIGNMENT_DOCTYPE, {"school_branch": branch, "enabled": 1})', helper)
		self.assertIn("Instructor {0} has no active Instructor Assignment", helper)
		self.assertIn("assert_schedule_instructor_assignment(doc)", branching)
		self.assertLess(branching.index("_before_validate_course_schedule(doc, method)"), branching.index("assert_schedule_instructor_assignment(doc)"))

	def test_permissions_navigation_and_install_are_connected(self):
		hooks = (APP / "hooks.py").read_text(encoding="utf-8")
		access = (APP / "access_control.py").read_text(encoding="utf-8")
		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text(encoding="utf-8")
		install = (APP / "install.py").read_text(encoding="utf-8")
		for token in (
			'"EduEdge Instructor Assignment": "eduedge.education.people_permissions.instructor_assignment_query"',
			'"EduEdge Student Photo Review Log": "eduedge.education.people_permissions.student_photo_review_log_query"',
			'"Student": {"before_validate": "eduedge.education.people_governance.before_validate_student"}',
		):
			self.assertIn(token, hooks)
		self.assertIn('"/app/eduedge-instructors": (("instructor", "read"),)', access)
		self.assertIn('"/app/eduedge-instructor-assignments": (("instructor_assignment", "read"),)', access)
		self.assertIn('"/app/eduedge-instructor-branch-assignment": "/app/eduedge-instructor-assignments"', navigation)
		self.assertIn("ensure_people_operations_foundation()", install)

	def test_ci_checks_people_operations_entries(self):
		workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
		for token in (
			"node --check eduedge/public/js/eduedge_students.bundle.js",
			"node --check eduedge/public/js/eduedge_instructors.bundle.js",
			"node --check eduedge/public/js/eduedge_instructor_assignments.bundle.js",
			"node --check eduedge/eduedge/page/eduedge_students/eduedge_students.js",
			"node --check eduedge/eduedge/page/eduedge_instructors/eduedge_instructors.js",
			"node --check eduedge/eduedge/page/eduedge_instructor_assignments/eduedge_instructor_assignments.js",
		):
			self.assertIn(token, workflow)


if __name__ == "__main__":
	unittest.main()
