from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class TestPublicExamAccessContract(unittest.TestCase):
	def test_public_capabilities_are_action_specific(self):
		text = (ROOT / "eduedge" / "cbt" / "public_access.py").read_text()
		self.assertIn('PUBLIC_EXAM_FEATURE = "cbt_public_exam"', text)
		for action in ("catalog", "assign", "host", "launch", "results", "author"):
			self.assertIn(f'"{action}"', text)
		self.assertIn("PUBLIC_EXAM_ACCESS_NOT_ACTIVATED", text)
		self.assertIn("eduedge_public_exam_authority", text)

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
		self.assertIn('"site_identifier": self.config.site_identifier', client)
		self.assertIn('"Authorization": f"token {self.config.client_id}:{self.config.client_secret}"', client)
		self.assertNotIn('"Authorization": f"Bearer {self.config.client_secret}"', client)

	def test_centre_lifecycle_is_non_submittable_and_status_governed(self):
		controller = (
			ROOT
			/ "eduedge"
			/ "eduedge"
			/ "doctype"
			/ "eduedge_examination_centre"
			/ "eduedge_examination_centre.py"
		).read_text()
		self.assertIn("ALLOWED_STATUS_TRANSITIONS", controller)
		self.assertIn('"Draft": {"Draft", "Active"}', controller)
		self.assertIn('"Active": {"Active", "Suspended", "Retired"}', controller)
		self.assertIn("Only a Draft examination centre can be deleted", controller)
		self.assertIn('self.enabled = 1 if self.centre_status == "Active" else 0', controller)

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
