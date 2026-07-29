from pathlib import Path
import json
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
		wrapper = (APP / "api/cbt_schedule_operations.py").read_text(encoding="utf-8")
		api = (APP / "api/cbt_schedule_operations_hardened.py").read_text(encoding="utf-8")
		self.assertIn("from eduedge.api.cbt_schedule_operations_hardened import (", wrapper)
		self.assertIn("__all__", wrapper)
		for method in (
			"get_context",
			"get_schedule",
			"get_candidate",
			"get_template_context",
			"save_schedule",
			"set_schedule_status",
			"save_candidate",
			"set_candidate_status",
			"assign_template_student_group",
			"record_intervention",
			"search_options",
		):
			self.assertIn(method, wrapper)
		for expected in (
			"get_allowed_school_branches",
			"assert_branch_access",
			"assert_user_branch_access",
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
			'"template_mode": MODE_FIXED',
			"status_change_reason",
			"student_group",
			"lifecycle",
		):
			self.assertIn(expected, api)
		for forbidden in (
			"ignore_permissions=True",
			"ignore_permissions = True",
			'frappe.new_doc("Sales Invoice")',
			'frappe.new_doc("Payment Entry")',
			'frappe.new_doc("Journal Entry")',
			'"previous_value", "new_value", "attempt_reference", "outcome"',
		):
			self.assertNotIn(forbidden, api)

	def test_bulk_assignment_retries_database_uniqueness_races(self):
		wrapper = (APP / "api/cbt_schedule_operations.py").read_text(encoding="utf-8")
		self.assertIn("@frappe.whitelist()", wrapper)
		self.assertIn("frappe.DuplicateEntryError", wrapper)
		self.assertIn("frappe.UniqueValidationError", wrapper)
		self.assertGreaterEqual(wrapper.count("_assign_template_student_group(schedule)"), 2)

	def test_public_capability_does_not_remove_school_branch_isolation(self):
		permissions = (APP / "cbt/permissions.py").read_text(encoding="utf-8")
		self.assertIn("public_allowed = _has_public_record_access", permissions)
		self.assertIn('conditions.append(f"{branch_column} in ({values})")', permissions)
		self.assertIn('conditions.append(f"{branch_column} is null")', permissions)
		self.assertNotIn("if _has_public_record_access(doctype, resolved_user):\n\t\treturn \"\"", permissions)
		self.assertIn("def _lifecycle_log_condition", permissions)
		self.assertIn("def _has_lifecycle_public_access", permissions)
		self.assertIn("can_author_public_exams", permissions)
		self.assertIn("can_assign_public_exams", permissions)

	def test_schedule_controller_enforces_readiness_and_candidate_locking(self):
		controller = (
			APP / "eduedge/doctype/eduedge_cbt_exam_schedule/eduedge_cbt_exam_schedule.py"
		).read_text(encoding="utf-8")
		governance = (APP / "cbt/schedule_governance.py").read_text(encoding="utf-8")
		for expected in (
			"validate_activation_readiness",
			"assert_fields_mutable_after_candidate_confirmation",
			"validate_course_scope",
			"assert_user_branch_access",
			"Policy Blueprint scheduling is disabled",
			"A Retired Template may be retained only",
			"status_change_reason",
			"write_lifecycle_log",
			"student_group",
		):
			self.assertIn(expected, controller)
		for expected in (
			"Assign at least one candidate before activating",
			"Resolve all Draft candidate assignments",
			"Examination Centre capacity",
			"_assert_no_schedule_overlap",
			"_assert_no_candidate_overlap",
			"public_candidate_reference",
			"has_confirmed_candidates",
			"initial_activation",
			"Candidates cannot be released before the Scheduled Start",
			"if actual != expected",
		):
			self.assertIn(expected, governance)

	def test_candidate_timing_and_intervention_truth_are_enforced(self):
		candidate = (
			APP / "eduedge/doctype/eduedge_cbt_candidate_assignment/eduedge_cbt_candidate_assignment.py"
		).read_text(encoding="utf-8")
		intervention = (
			APP / "eduedge/doctype/eduedge_cbt_intervention_log/eduedge_cbt_intervention_log.py"
		).read_text(encoding="utf-8")
		for expected in (
			"assert_check_in_window",
			"assert_manual_release_window",
			"Schedule Student Group",
			"eduedge_time_extension",
			"status_change_reason",
			"write_lifecycle_log",
			"def after_insert",
			"Candidate Assignment Created",
		):
			self.assertIn(expected, candidate)
		for expected in (
			"Recorded for Review",
			"Cumulative extra time exceeds",
			"after_insert",
			"eduedge_time_extension",
			"for_update=self.intervention_type == \"Time Extension\"",
			"self.previous_value = None",
			"self.attempt_reference = None",
		):
			self.assertIn(expected, intervention)

	def test_composite_uniqueness_patch_is_registered_and_frappe_compatible(self):
		patches = (APP / "patches.txt").read_text(encoding="utf-8")
		patch = (APP / "patches/v0_8/add_cbt_candidate_assignment_unique_indexes.py").read_text(encoding="utf-8")
		self.assertIn("add_cbt_candidate_assignment_unique_indexes", patches)
		self.assertIn("uniq_cbt_schedule_student", patch)
		self.assertIn("uniq_cbt_schedule_public_candidate", patch)
		self.assertIn("frappe.db.add_unique", patch)
		self.assertIn("_assert_no_duplicates", patch)
		self.assertIn("group_by=", patch)
		self.assertIn("cint(row.total) > 1", patch)
		self.assertNotIn("having=", patch)

	def test_lifecycle_log_is_server_created_append_only_and_branch_isolated(self):
		meta_path = APP / "eduedge/doctype/eduedge_cbt_lifecycle_log/eduedge_cbt_lifecycle_log.json"
		controller_path = APP / "eduedge/doctype/eduedge_cbt_lifecycle_log/eduedge_cbt_lifecycle_log.py"
		self.assertTrue(meta_path.exists())
		self.assertTrue(controller_path.exists())
		meta = json.loads(meta_path.read_text(encoding="utf-8"))
		fields = {row["fieldname"] for row in meta["fields"]}
		for fieldname in ("exam_schedule", "candidate_assignment", "school_branch", "from_status", "to_status", "reason", "acted_by", "acted_on"):
			self.assertIn(fieldname, fields)
		self.assertTrue(all(not row.get("create") for row in meta["permissions"]))
		controller = controller_path.read_text(encoding="utf-8")
		self.assertIn("append-only and cannot be edited", controller)
		self.assertIn("append-only and cannot be deleted", controller)
		self.assertIn("eduedge_internal_lifecycle_log", controller)
		self.assertIn("created only by authorised Schedule and Candidate lifecycle actions", controller)
		governance = (APP / "cbt/schedule_governance.py").read_text(encoding="utf-8")
		self.assertIn("doc.flags.eduedge_internal_lifecycle_log = True", governance)
		self.assertIn("doc.insert(ignore_permissions=True)", governance)
		hooks = (APP / "hooks.py").read_text(encoding="utf-8")
		self.assertIn('"EduEdge CBT Lifecycle Log": "eduedge.cbt.permissions.cbt_lifecycle_log_query"', hooks)

	def test_lifecycle_reason_fields_are_read_only_outside_controlled_actions(self):
		for path in (
			APP / "eduedge/doctype/eduedge_cbt_exam_schedule/eduedge_cbt_exam_schedule.json",
			APP / "eduedge/doctype/eduedge_cbt_candidate_assignment/eduedge_cbt_candidate_assignment.json",
		):
			meta = json.loads(path.read_text(encoding="utf-8"))
			field = next(row for row in meta["fields"] if row["fieldname"] == "status_change_reason")
			self.assertEqual(field.get("read_only"), 1)

	def test_edgesuite_workbench_exposes_hardened_behaviour(self):
		component = (APP / "public/js/eduedge_cbt_schedules/EduEdgeCBTSchedules.vue").read_text(encoding="utf-8")
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
			"Lifecycle History",
			"Approved Fixed Question Set",
			"Actual Student Group / Class",
			"Recorded for Review",
			"requiresReason",
			"reason: this.confirmDialog.reason",
			"set_schedule_status",
			"set_candidate_status",
			"assign_template_student_group",
			"record_intervention",
		):
			self.assertIn(expected, component)
		self.assertNotIn('options: ["Applied", "Rejected"]', component)
		self.assertNotIn('fieldname: "previous_value"', component)
		self.assertNotIn('fieldname: "attempt_reference"', component)

	def test_page_retains_advanced_native_record_without_using_it_as_primary_ui(self):
		component = (APP / "public/js/eduedge_cbt_schedules/EduEdgeCBTSchedules.vue").read_text(encoding="utf-8")
		self.assertIn("Open Full Record", component)
		self.assertIn("/app/eduedge-cbt-exam-schedule/", component)
		self.assertNotIn("window.location.href = `/app/eduedge-cbt-exam-schedule/new", component)


if __name__ == "__main__":
	unittest.main()
