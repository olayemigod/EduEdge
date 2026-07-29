from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestProgrammeOfferingsPageContract(unittest.TestCase):
	def test_offerings_api_is_bounded_permission_and_branch_aware(self):
		api = (APP / "api" / "programme_offerings.py").read_text(encoding="utf-8")
		for token in (
			"DEFAULT_PAGE_LENGTH = 25",
			"MAX_PAGE_LENGTH = 50",
			'frappe.has_permission("EduEdge Program Offering", "read")',
			"get_current_school_branch",
			"assert_branch_access(branch)",
			"page_length=page_length + 1",
			'fields=[{"COUNT": "name", "as": "record_count"}]',
		):
			self.assertIn(token, api)

	def test_capacity_uses_batched_enrollment_lifecycle_truth(self):
		api = (APP / "api" / "programme_offerings.py").read_text(encoding="utf-8")
		lifecycle = (APP / "services" / "enrollment_lifecycle.py").read_text(encoding="utf-8")
		self.assertIn("get_capacity_consuming_enrollment_counts(names)", api)
		self.assertIn('row["occupied_seats"]', api)
		self.assertIn('row["seats_remaining"]', api)
		self.assertNotIn("count_capacity_consuming_enrollments(row.name)", api)
		self.assertIn("group by enrollment.", lifecycle)
		self.assertIn("EduEdge Enrollment Status Log", lifecycle)

	def test_runtime_statuses_are_derived_not_stored(self):
		api = (APP / "api" / "programme_offerings.py").read_text(encoding="utf-8")
		for status in ("Disabled", "Closed", "Upcoming", "Full", "Active"):
			self.assertIn(f'"{status}"', api)
		self.assertIn('row["operational_status"] = status', api)
		self.assertNotIn('doc.operational_status', api)

	def test_identity_lock_follows_operational_references(self):
		api = (APP / "api" / "programme_offerings.py").read_text(encoding="utf-8")
		self.assertIn('for doctype in ("Student Applicant", "Student Group")', api)
		self.assertIn('"Program Enrollment"', api)
		self.assertIn('"docstatus": 1', api)
		self.assertIn('row["identity_locked"]', api)

	def test_offering_save_uses_document_validation_platform_guard_and_link_permissions(self):
		api = (APP / "api" / "programme_offerings.py").read_text(encoding="utf-8")
		self.assertIn(
			'require_eduedge_access(feature_key="academics", action="save_programme_offering")',
			api,
		)
		self.assertIn('_assert_link_read_permission("Program", program', api)
		self.assertIn('_assert_link_read_permission("Academic Year", academic_year', api)
		self.assertIn('_assert_link_read_permission("EduEdge Academic Level", academic_level', api)
		self.assertIn('_assert_link_read_permission("Academic Term", academic_term', api)
		self.assertIn('_assert_link_read_permission("Student Batch Name", student_batch', api)
		self.assertIn('doc.check_permission("write")', api)
		self.assertIn("doc.save()", api)
		self.assertNotIn("db_set(", api)
		self.assertNotIn("frappe.db.set_value", api)

	def test_dedicated_page_exposes_capacity_availability_and_identity_lock(self):
		component = (
			APP
			/ "public"
			/ "js"
			/ "eduedge_programme_offerings"
			/ "EduEdgeProgrammeOfferings.vue"
		).read_text(encoding="utf-8")
		for token in (
			"<EdgeAppShell",
			"Occupied Seats",
			"Admission availability",
			"Enrollment availability",
			"identity_locked",
			"draftBranchChanged",
			"draftYearChanged",
			"Zero means no configured limit",
			"Current active Branch",
		):
			self.assertIn(token, component)
		self.assertIn(':disabled="draft.identity_locked"', component)
		self.assertIn('this.filters.institution = ""', component)
		self.assertIn('frappe.set_route("Form", "EduEdge Program Offering", name)', component)

	def test_page_loader_uses_canonical_edgesuite_bundle(self):
		loader = (
			APP
			/ "eduedge"
			/ "page"
			/ "eduedge_program_offerings"
			/ "eduedge_program_offerings.js"
		).read_text(encoding="utf-8")
		bundle = (APP / "public" / "js" / "eduedge_programme_offerings.bundle.js").read_text(
			encoding="utf-8"
		)
		self.assertIn("createEduEdgeProgrammeOfferingsApp", bundle)
		self.assertLess(
			loader.index("edgesuite_ui.bundle.js"),
			loader.index("eduedge_programme_offerings.bundle.js"),
		)
		self.assertNotIn("registerEduEdgeResourcePage", loader)
		self.assertNotIn('frappe.require("edgeui.bundle.js"', loader)

	def test_ci_checks_programme_offerings_entries(self):
		workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
		self.assertIn("node --check eduedge/public/js/eduedge_programme_offerings.bundle.js", workflow)
		self.assertIn(
			"node --check eduedge/eduedge/page/eduedge_program_offerings/eduedge_program_offerings.js",
			workflow,
		)


if __name__ == "__main__":
	unittest.main()
