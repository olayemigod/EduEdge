import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class TestPublicExamAccessContract(unittest.TestCase):
	def test_public_capabilities_are_action_specific(self):
		text = (ROOT / "eduedge" / "cbt" / "public_access.py").read_text()
		self.assertIn('PUBLIC_EXAM_FEATURE = "cbt_public_exam"', text)
		for action in ("catalog", "assign", "host", "launch", "results", "author"):
			self.assertIn(f'"{action}"', text)
		self.assertIn("PUBLIC_EXAM_ACCESS_NOT_ACTIVATED", text)
		self.assertIn("eduedge_public_exam_authority", text)
		self.assertIn("get_eduedge_capability_decision", text)
		self.assertNotIn("get_eduedge_access_decision", text)

	def test_public_authoring_does_not_come_from_system_manager(self):
		text = (ROOT / "eduedge" / "cbt" / "public_access.py").read_text()
		role_block = text.split("PUBLIC_EXAM_AUTHOR_ROLES =", 1)[1].split("}", 1)[0]
		self.assertIn("EduEdge Super Administrator", role_block)
		self.assertIn("EduEdge Public Exam Administrator", role_block)
		self.assertNotIn("System Manager", role_block)
		self.assertIn("has_public_exam_author_role", text)
		self.assertIn("has_public_exam_capability", text)

	def test_native_forms_hide_public_authoring_without_server_grant(self):
		files = [
			ROOT / "eduedge" / "eduedge" / "doctype" / "eduedge_examination_centre" / "eduedge_examination_centre.js",
			ROOT / "eduedge" / "eduedge" / "doctype" / "eduedge_cbt_question" / "eduedge_cbt_question.js",
			ROOT / "eduedge" / "eduedge" / "doctype" / "eduedge_cbt_exam_template" / "eduedge_cbt_exam_template.js",
		]
		for path in files:
			text = path.read_text()
			self.assertIn("get_public_exam_access_context", text)
			self.assertIn("capabilities?.author?.allowed", text)
			self.assertIn("set_df_property", text)

	def test_remote_adapter_is_bound_to_exact_site_and_frappe_token_auth(self):
		config = (ROOT / "eduedge" / "platform" / "config.py").read_text()
		client = (ROOT / "eduedge" / "platform" / "remote_client.py").read_text()
		self.assertIn("site_identifier", config)
		self.assertIn("coreedge_site_identifier", config)
		self.assertIn("coreedge_feature_access_decision_path", config)
		self.assertIn("feature_access_decision_path", config)
		self.assertIn('"site_identifier": self.config.site_identifier', client)
		self.assertIn('"Authorization": f"token {self.config.client_id}:{self.config.client_secret}"', client)
		self.assertIn("def get_feature_access_decision", client)
		self.assertIn("self.config.feature_access_decision_path", client)
		self.assertNotIn('"Authorization": f"Bearer {self.config.client_secret}"', client)

	def test_service_capabilities_fail_closed_without_affecting_runtime_guards(self):
		access = (ROOT / "eduedge" / "platform" / "access.py").read_text()
		self.assertIn("def get_eduedge_access_decision", access)
		self.assertIn("def get_eduedge_capability_decision", access)
		self.assertIn('decision_type="runtime"', access)
		self.assertIn('decision_type="capability"', access)
		self.assertIn("client.get_feature_access_decision", access)
		self.assertIn("Capabilities always fail closed", access)
		self.assertIn("guard_eduedge_action", access)
		guard_block = access.split("def guard_eduedge_action", 1)[1]
		self.assertIn("require_eduedge_access", guard_block)
		self.assertNotIn("get_eduedge_capability_decision", guard_block)

	def test_centre_lifecycle_is_non_submittable_and_status_governed(self):
		doctype = json.loads(
			(
				ROOT
				/ "eduedge"
				/ "eduedge"
				/ "doctype"
				/ "eduedge_examination_centre"
				/ "eduedge_examination_centre.json"
			).read_text()
		)
		controller = (
			ROOT
			/ "eduedge"
			/ "eduedge"
			/ "doctype"
			/ "eduedge_examination_centre"
			/ "eduedge_examination_centre.py"
		).read_text()
		self.assertEqual(doctype["is_submittable"], 0)
		self.assertIn("ALLOWED_STATUS_TRANSITIONS", controller)
		self.assertIn('"Draft": {"Draft", "Active"}', controller)
		self.assertIn('"Active": {"Active", "Suspended", "Retired"}', controller)
		self.assertIn("Only a Draft examination centre can be deleted", controller)
		self.assertIn('self.enabled = 1 if self.centre_status == "Active" else 0', controller)
		self.assertIn("def before_submit", controller)
		self.assertIn("def before_cancel", controller)
		self.assertIn("non-submittable master records", controller)

	def test_cbt_operations_lists_only_active_centres_but_counts_all(self):
		api = (ROOT / "eduedge" / "api" / "cbt.py").read_text()
		self.assertIn("all_centres = frappe.get_list", api)
		self.assertIn('row.centre_status == "Active" or cint(row.enabled)', api)
		self.assertIn('"centres": len(all_centres)', api)
		self.assertIn('"non_active_centres": len(all_centres) - len(centres)', api)
		self.assertIn('"centres": centres[:12]', api)

	def test_cbt_operations_uses_visible_header_create_launcher(self):
		loader = (
			ROOT
			/ "eduedge"
			/ "eduedge"
			/ "page"
			/ "eduedge_cbt_operations"
			/ "eduedge_cbt_operations.js"
		).read_text()
		self.assertIn("installHeaderCreateLauncher", loader)
		self.assertIn("showCreateDialog", loader)
		self.assertIn("page.clear_inner_toolbar()", loader)
		self.assertNotIn("page.add_inner_button", loader)
		self.assertIn('doctype: "EduEdge Examination Centre"', loader)
		self.assertIn('doctype: "EduEdge CBT Question"', loader)
		self.assertIn('doctype: "EduEdge CBT Exam Template"', loader)
		self.assertIn('button.textContent = __("Create New")', loader)
		self.assertIn("event.stopImmediatePropagation()", loader)

	def test_public_hosting_approval_is_platform_controlled(self):
		controller = (
			ROOT
			/ "eduedge"
			/ "eduedge"
			/ "doctype"
			/ "eduedge_examination_centre"
			/ "eduedge_examination_centre.py"
		).read_text()
		self.assertIn("public_hosting_status", controller)
		self.assertIn("from_public_exam_sync", controller)
		self.assertIn("require_public_exam_authoring", controller)


if __name__ == "__main__":
	unittest.main()
