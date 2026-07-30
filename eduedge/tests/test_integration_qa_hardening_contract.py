from __future__ import annotations

import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]


class IntegrationQAHardeningContractTest(unittest.TestCase):
	def read(self, relative: str) -> str:
		return (APP_ROOT / relative).read_text(encoding="utf-8")

	def test_academic_foundation_calendar_uses_mapping_access(self):
		content = self.read("api/integration_qa_hardening.py")
		self.assertIn('getdate(row["start_date"])', content)
		self.assertIn('getdate(row["end_date"])', content)
		self.assertNotIn("getdate(row.start_date)", content)
		self.assertIn("Institution-wide Academic Foundation", content)

	def test_branch_scoped_operations_resolve_only_permitted_defaults(self):
		content = self.read("api/integration_qa_hardening.py")
		self.assertIn("get_allowed_school_branches(institution=active_institution)", content)
		self.assertIn('row.get("is_default")', content)
		self.assertIn("len(allowed) == 1", content)
		self.assertIn("assert_branch_access(resolved)", content)
		self.assertIn("Set up a School Branch / Campus", content)
		self.assertIn("Select a School Branch / Campus", content)

	def test_resource_center_create_and_edit_use_edgesuite_dialog(self):
		content = self.read("public/js/eduedge_ui/resource_modal.js")
		self.assertIn('from "vue"', content)
		self.assertIn("EdgeFormDialogFallback", content)
		self.assertIn("mountEdgeResourceDialog", content)
		self.assertNotIn("openNativeSchemaDialog", content)
		resource_center = self.read("public/js/eduedge_resource_center/EduEdgeResourceCenter.vue")
		self.assertIn("openNativeResourceDialog", resource_center)
		self.assertIn("resource: this.resourceKey", resource_center)

	def test_school_branch_page_uses_shared_edgesuite_resource_center(self):
		content = self.read("eduedge/page/eduedge_school_branches/eduedge_school_branches.js")
		self.assertIn("registerEduEdgeResourcePage", content)
		self.assertIn('resourceKey: "school_branches"', content)

	def test_friendly_name_pipeline_covers_sidebar_waffle_workspace_and_branch_action(self):
		navigation = self.read("public/js/eduedge_ui/navigation.js")
		product_menu = self.read("public/js/eduedge_product_menu.bundle.js")
		workspace = self.read("eduedge/workspace/eduedge/eduedge.json")
		self.assertIn('term("student"', navigation)
		self.assertIn('term("student_applicant"', navigation)
		self.assertIn("refreshEduEdgeMenuItems", navigation)
		self.assertIn('window.addEventListener("eduedge:institution-context-changed"', navigation)
		self.assertIn('term("programme"', product_menu)
		self.assertIn('term("student_group"', product_menu)
		self.assertIn('path === "/app/eduedge"', product_menu)
		self.assertIn('["Add School Branche", "Add School Branch"]', product_menu)
		self.assertIn('"label":"Student Groups"', workspace)
		self.assertNotIn("Student Groups / Classes", workspace)

	def test_attempt_review_loader_has_edgesuite_runtime_and_visible_timeout(self):
		content = self.read("eduedge/page/eduedge_cbt_review_workbench/eduedge_cbt_review_workbench.js")
		self.assertIn('frappe.require("edgesuite_ui.bundle.js"', content)
		self.assertIn('frappe.require("eduedge_cbt_attempt_review.bundle.js"', content)
		self.assertIn("createEduEdgeCBTAttemptReviewApp", content)
		self.assertIn("setTimeout", content)
		self.assertIn("failed to load", content)
		self.assertIn("eduedge-cbt-review-workbench", content)

	def test_cbt_branch_filters_fail_closed(self):
		content = self.read("cbt/integration_hardening.py")
		self.assertIn("get_allowed_school_branches", content)
		self.assertIn("branch not in _allowed_branch_names()", content)
		self.assertIn("_assert_permitted_branch(schedule.school_branch)", content)
		self.assertIn("_assert_permitted_branch(attempt.school_branch)", content)

	def test_hooks_route_qa_endpoints_through_hardened_services(self):
		content = self.read("hooks.py")
		self.assertIn(
			'"eduedge.api.academic_foundation.get_academic_foundation": "eduedge.api.integration_qa_hardening.get_academic_foundation"',
			content,
		)
		self.assertIn(
			'"eduedge.api.academic_operations.get_operations_context": "eduedge.api.integration_qa_hardening.get_operations_context"',
			content,
		)
		self.assertIn(
			'"eduedge.cbt.attempt_review.get_attempt_review_queue": "eduedge.cbt.integration_hardening.get_attempt_review_queue"',
			content,
		)

	def test_edgesuite_ui_audit_is_documented(self):
		content = self.read("../docs/eduedge_edgesuite_ui_and_security_audit.md")
		self.assertIn("School Branches", content)
		self.assertIn("Admissions", content)
		self.assertIn("Native Frappe full forms", content)
		self.assertIn("fails closed", content.lower())


if __name__ == "__main__":
	unittest.main()
