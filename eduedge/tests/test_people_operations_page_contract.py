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

	def test_instructor_profile_api_is_institution_scoped_and_branch_optional(self):
		api = (APP / "api" / "instructor_profiles.py").read_text(encoding="utf-8")
		for token in (
			'ALL_INSTITUTIONS_KEY = "__all__"',
			"GLOBAL_INSTRUCTOR_ROLES",
			"can_view_all_institutions",
			"Home Institution is required for the Instructor profile.",
			"branch = str(data.get(INSTRUCTOR_PRIMARY_BRANCH_FIELD) or \"\").strip()",
			"if branch:",
			'frappe.new_doc("Instructor")',
			"_ensure_branch_eligibility",
		):
			self.assertIn(token, api)
		self.assertNotIn("Primary School Branch / Campus is required", api)
		self.assertNotIn("ignore_permissions", api)

	def test_instructor_governance_allows_safe_home_institution_transfer(self):
		governance = (APP / "education" / "people_governance.py").read_text(encoding="utf-8")
		self.assertIn("validate_master_institution(doc, required=doc.is_new())", governance)
		self.assertIn("Primary Branch / Campus must belong to the Instructor's Home Institution", governance)
		self.assertIn("Department / School Section must belong to the Instructor's Home Institution", governance)
		self.assertNotIn("before_validate_institution_owned_master", governance)

	def test_instructor_and_assignment_pages_are_edgesuite_surfaces(self):
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
			"All Institutions",
			"Home Institution",
			"Institution-wide / no Primary Branch",
			"cross-Institution operational assignments",
			"Instructor Assignments",
			"set_instructor_photo",
		):
			self.assertIn(token, instructors)
		self.assertNotIn("Primary Branch / Campus *", instructors)

		assignments = (APP / "public" / "js" / "eduedge_instructor_assignments" / "EduEdgeInstructorAssignments.vue").read_text(encoding="utf-8")
		for token in (
			"Instructor Assignments",
			"Institutions and Branches / Campuses",
			"Classes / Programme Offerings",
			"Class Arms",
			"Preview Assignment Batch",
			"preview_instructor_assignment_batch",
			"save_instructor_assignment_batch",
			"Branch Eligibility",
			"Current Instructor Assignments",
		):
			self.assertIn(token, assignments)
		self.assertNotIn("Teacher Assignments", assignments)

	def test_assignment_doctype_allows_cross_institution_instructor_identity(self):
		doctype_json = json.loads((APP / "eduedge" / "doctype" / "eduedge_instructor_assignment" / "eduedge_instructor_assignment.json").read_text(encoding="utf-8"))
		controller = (APP / "eduedge" / "doctype" / "eduedge_instructor_assignment" / "eduedge_instructor_assignment.py").read_text(encoding="utf-8")
		self.assertEqual(doctype_json["name"], "EduEdge Instructor Assignment")
		fieldnames = {row.get("fieldname") for row in doctype_json["fields"]}
		for fieldname in ("instructor", "school_branch", "program_offering", "student_group", "course", "assignment_type", "assignment_scope"):
			self.assertIn(fieldname, fieldnames)
		for token in (
			"_apply_offering_context",
			"_validate_group_context",
			"_validate_instructor_context",
			"_validate_course_context",
			"_validate_duplicate",
			"Save through Instructor Assignments or add Branch eligibility first.",
			"An overlapping active Instructor Assignment already exists.",
		):
			self.assertIn(token, controller)
		self.assertNotIn("Instructor must belong to the selected Institution", controller)

	def test_cross_institution_bulk_api_creates_branch_access_and_assignments(self):
		api = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
		for token in (
			"get_instructor_assignments_page",
			"preview_instructor_assignment_batch",
			"save_instructor_assignment_batch",
			"assignment_institutions",
			"institutions_covered",
			"_ensure_branch_assignment",
			'frappe.new_doc("EduEdge Instructor Assignment")',
			'frappe.new_doc("EduEdge Instructor Branch Assignment")',
		):
			self.assertIn(token, api)
		self.assertNotIn("can be assigned only within their Institution", api)
		self.assertNotIn("ignore_permissions", api)
		self.assertNotIn("frappe.db.set_value", api)

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
		self.assertIn("ensure_teaching_assignment_foundation()", install)

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
