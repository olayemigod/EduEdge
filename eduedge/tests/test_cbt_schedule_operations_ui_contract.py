from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestCBTScheduleOperationsUIContract(unittest.TestCase):
	def test_page_bundle_loader_navigation_and_workspace_are_registered(self):
		page = APP / "eduedge/page/eduedge_cbt_schedules"
		loader = (page / "eduedge_cbt_schedules.js").read_text(encoding="utf-8")
		definition = (page / "eduedge_cbt_schedules.json").read_text(encoding="utf-8")
		bundle = (APP / "public/js/eduedge_cbt_schedules.bundle.js").read_text(encoding="utf-8")
		navigation = (APP / "public/js/eduedge_ui/navigation.js").read_text(encoding="utf-8")
		workspace = (APP / "eduedge/workspace/eduedge/eduedge.json").read_text(encoding="utf-8")
		workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
		self.assertTrue((page / "__init__.py").exists())
		self.assertIn('"name": "eduedge-cbt-schedules"', definition)
		self.assertIn('frappe.pages["eduedge-cbt-schedules"]', loader)
		self.assertIn('frappe.require("edgesuite_ui.bundle.js"', loader)
		self.assertIn('frappe.require("eduedge_cbt_schedules.bundle.js"', loader)
		self.assertIn("createEduEdgeCBTSchedulesApp", bundle)
		self.assertIn('route: "/app/eduedge-cbt-schedules"', navigation)
		self.assertIn('"/app/eduedge-cbt-schedules"', navigation)
		self.assertIn('"label":"CBT Schedules"', workspace)
		self.assertIn("eduedge_cbt_schedules.bundle.js", workflow)
		self.assertIn("eduedge_cbt_schedules/eduedge_cbt_schedules.js", workflow)

	def test_access_manifest_uses_schedule_candidate_and_intervention_permissions(self):
		access = (APP / "access_control.py").read_text(encoding="utf-8")
		for expected in (
			'"cbt_schedule": "EduEdge CBT Exam Schedule"',
			'"cbt_candidate_assignment": "EduEdge CBT Candidate Assignment"',
			'"cbt_intervention_log": "EduEdge CBT Intervention Log"',
			'"/app/eduedge-cbt-schedules"',
			'("cbt_schedule", "read")',
			'("cbt_candidate_assignment", "read")',
			'("cbt_intervention_log", "read")',
		):
			self.assertIn(expected, access)

	def test_operations_api_is_permission_branch_and_platform_guarded(self):
		api = (APP / "api/cbt_schedule_operations.py").read_text(encoding="utf-8")
		for expected in (
			"get_allowed_school_branches",
			"assert_branch_access",
			"doc.check_permission",
			"frappe.has_permission",
			"frappe.get_list",
			"require_eduedge_access",
			"require_public_exam_authoring",
			"require_public_exam_assignment",
			"get_context",
			"save_schedule",
			"set_schedule_status",
			"save_candidate",
			"set_candidate_status",
			"assign_template_student_group",
			"record_intervention",
			"search_options",
		):
			self.assertIn(expected, api)
		for forbidden in (
			"ignore_permissions=True",
			"ignore_permissions = True",
			"frappe.db.sql(",
			'frappe.new_doc("Sales Invoice")',
			'frappe.new_doc("Payment Entry")',
			'frappe.new_doc("Journal Entry")',
		):
			self.assertNotIn(forbidden, api)

	def test_edgesuite_workbench_covers_schedules_candidates_and_interventions(self):
		component = (
			APP / "public/js/eduedge_cbt_schedules/EduEdgeCBTSchedules.vue"
		).read_text(encoding="utf-8")
		for expected in (
			"<EdgeAppShell",
			"<EdgePageHeader",
			"<EdgeFilterBar",
			"<EdgeDashboardLayout",
			"<EdgeFormDialog",
			"<EdgeModal",
			"CBT Schedules and Candidates",
			"Candidate Assignments",
			"Intervention History",
			"openScheduleDialog",
			"openCandidateDialog",
			"openInterventionDialog",
			"set_schedule_status",
			"set_candidate_status",
			"assign_template_student_group",
			"record_intervention",
			"get_template_context",
			"search_options",
		):
			self.assertIn(expected, component)
		self.assertIn("Activated schedules are immutable", component)
		self.assertIn("append-only", component)
		self.assertIn("do not edit candidate answers, marks or submitted academic records", component)

	def test_page_retains_advanced_native_record_without_using_it_as_primary_ui(self):
		component = (
			APP / "public/js/eduedge_cbt_schedules/EduEdgeCBTSchedules.vue"
		).read_text(encoding="utf-8")
		self.assertIn("Open Full Record", component)
		self.assertIn("/app/eduedge-cbt-exam-schedule/", component)
		self.assertNotIn("window.location.href = `/app/eduedge-cbt-exam-schedule/new", component)


if __name__ == "__main__":
	unittest.main()
