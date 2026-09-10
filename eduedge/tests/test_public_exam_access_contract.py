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

	def test_question_and_template_are_non_submittable_server_guarded_masters(self):
		for doctype_folder, json_name in (
			("eduedge_cbt_question", "eduedge_cbt_question.json"),
			("eduedge_cbt_exam_template", "eduedge_cbt_exam_template.json"),
		):
			doctype = json.loads(
				(ROOT / "eduedge" / "eduedge" / "doctype" / doctype_folder / json_name).read_text()
			)
			self.assertEqual(doctype["is_submittable"], 0)

		hooks = (ROOT / "eduedge" / "hooks.py").read_text()
		guard = (ROOT / "eduedge" / "cbt" / "master_lifecycle.py").read_text()
		patches = (ROOT / "eduedge" / "patches.txt").read_text()
		for doctype in ("EduEdge CBT Question", "EduEdge CBT Exam Template"):
			self.assertIn(f'"{doctype}": {{', hooks)
		self.assertIn("validate_master_docstatus", hooks)
		self.assertIn("block_master_submit", hooks)
		self.assertIn("block_master_cancel", hooks)
		self.assertIn("non-submittable master record", guard)
		self.assertIn("enforce_cbt_master_lifecycle", patches)

	def test_question_options_require_answers_and_derive_labels_and_order(self):
		option_doctype = json.loads(
			(
				ROOT
				/ "eduedge"
				/ "eduedge"
				/ "doctype"
				/ "eduedge_question_option"
				/ "eduedge_question_option.json"
			).read_text()
		)
		fields = {field["fieldname"]: field for field in option_doctype["fields"]}
		self.assertTrue(fields["option_text"].get("reqd"))
		self.assertEqual(fields["option_text"]["label"], "Answer")
		self.assertTrue(fields["option_key"].get("read_only"))
		self.assertTrue(fields["display_order"].get("hidden"))
		self.assertTrue(fields["display_order"].get("read_only"))

		controller = (
			ROOT
			/ "eduedge"
			/ "eduedge"
			/ "doctype"
			/ "eduedge_cbt_question"
			/ "eduedge_cbt_question.py"
		).read_text()
		script = (
			ROOT
			/ "eduedge"
			/ "eduedge"
			/ "doctype"
			/ "eduedge_cbt_question"
			/ "eduedge_cbt_question.js"
		).read_text()
		self.assertIn("row.option_key = label", controller)
		self.assertIn("row.display_order = index", controller)
		self.assertIn("Enter an Answer for option {0}", controller)
		self.assertIn("row.option_key = optionLabel(index + 1)", script)
		self.assertIn("normaliseAnswerOptions", script)
		self.assertIn("Previous Question Version", json.dumps(json.loads((ROOT / "eduedge" / "eduedge" / "doctype" / "eduedge_cbt_question" / "eduedge_cbt_question.json").read_text())))
		self.assertIn("previousVersion + 1", script)

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
		self.assertIn('route: "/app/eduedge-examination-centre/new-eduedge-examination-centre"', loader)
		self.assertIn('route: "/app/eduedge-question-builder"', loader)
		self.assertIn('route: "/app/eduedge-cbt-exam-template/new-eduedge-cbt-exam-template"', loader)
		self.assertIn("openCreateRoute", loader)
		self.assertIn("openNativeDeskRouteInNewTab", loader)
		self.assertIn('window.open(url.toString(), "_blank", "noopener,noreferrer")', loader)
		self.assertIn('window.location.href = route', loader)
		self.assertNotIn("frappe.new_doc", loader)
		self.assertIn('button.textContent = __("Create New")', loader)
		self.assertIn("event.stopImmediatePropagation()", loader)

	def test_cbt_operations_collapses_optional_public_access_details(self):
		loader = (
			ROOT
			/ "eduedge"
			/ "eduedge"
			/ "page"
			/ "eduedge_cbt_operations"
			/ "eduedge_cbt_operations.js"
		).read_text()
		self.assertIn("installPublicAccessDisclosure", loader)
		self.assertIn("queuePublicAccessDisclosure", loader)
		self.assertIn('root.querySelector(".eduedge-cbt-access-panel")', loader)
		self.assertIn('operationallyRelevant || savedPreference === "1"', loader)
		self.assertIn('toggle.textContent = expanded ? __("Hide access details") : __("Show access details")', loader)
		self.assertIn("row.hidden = !expanded", loader)
		self.assertIn("window.localStorage.setItem", loader)

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
