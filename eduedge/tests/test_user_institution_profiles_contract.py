from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestUserInstitutionProfilesContract(unittest.TestCase):
	def test_user_profile_is_separate_self_scoped_record(self):
		profile = json.loads(
			(APP / "eduedge" / "doctype" / "eduedge_user_profile" / "eduedge_user_profile.json").read_text()
		)
		fields = {field["fieldname"]: field for field in profile["fields"]}
		self.assertEqual(profile["autoname"], "field:user")
		self.assertEqual(fields["user"]["options"], "User")
		self.assertEqual(fields["user"]["unique"], 1)
		for fieldname in (
			"professional_title",
			"whatsapp_number",
			"address_line_1",
			"country",
			"emergency_contact_name",
			"emergency_contact_relationship",
			"emergency_contact_phone",
		):
			self.assertIn(fieldname, fields)
		self.assertTrue(any(row["role"] == "All" and row.get("create") and row.get("write") for row in profile["permissions"]))

		controller = (
			APP / "eduedge" / "doctype" / "eduedge_user_profile" / "eduedge_user_profile.py"
		).read_text()
		self.assertIn("You can only maintain your own EduEdge Profile", controller)
		self.assertIn("for update", controller)
		self.assertIn("The Profile User cannot be changed", controller)
		self.assertIn("sanitize_html", controller)

		permissions = (APP / "education" / "profile_permissions.py").read_text()
		self.assertIn("user_profile_query", permissions)
		self.assertIn("profile_user == resolved_user", permissions)
		self.assertIn('resolved_user == "Administrator"', permissions)

	def test_profile_api_fixes_target_to_session_user_and_preserves_hr_truth(self):
		api = (APP / "api" / "profiles.py").read_text()
		self.assertIn("user = _require_login()", api)
		self.assertIn('frappe.get_doc("User", user)', api)
		self.assertIn('profile_doc.user = user', api)
		self.assertNotIn("ignore_permissions", api)
		self.assertNotIn('frappe.get_doc("User", data', api)
		self.assertIn('filters={"user_id": user, "status": "Active"}', api)
		self.assertIn('filters={"employee": ["in", employee_names], "status": "Active"}', api)
		self.assertNotIn('doc.set("roles"', api)
		self.assertNotIn("Employee\", employee", api)

	def test_image_upload_rules_keep_user_photo_private_capable_and_logo_public(self):
		api = (APP / "api" / "profiles.py").read_text()
		self.assertIn("MAX_PROFILE_IMAGE_BYTES = 2 * 1024 * 1024", api)
		self.assertIn('ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}', api)
		self.assertIn('file_type.startswith("image/")', api)
		self.assertIn("require_public=False", api)
		self.assertIn("require_public=True", api)
		self.assertIn("Institution logos must be uploaded as public images", api)
		self.assertIn("You cannot use another user's uploaded file", api)

		component = (APP / "public" / "js" / "eduedge_my_profile" / "EduEdgeMyProfile.vue").read_text()
		self.assertIn("Upload passport photo", component)
		self.assertIn("is_private: 1", component)
		self.assertIn("User → active Employee → active Instructor", component)

	def test_institution_branding_is_access_controlled_and_report_ready(self):
		institution = json.loads(
			(APP / "eduedge" / "doctype" / "eduedge_institution" / "eduedge_institution.json").read_text()
		)
		fields = {field["fieldname"]: field for field in institution["fields"]}
		for fieldname in (
			"logo",
			"motto",
			"address",
			"phone",
			"whatsapp_number",
			"email",
			"website",
			"report_card_letter_head",
			"report_footer",
		):
			self.assertIn(fieldname, fields)
		self.assertEqual(fields["report_card_letter_head"]["options"], "Letter Head")

		api = (APP / "api" / "profiles.py").read_text()
		self.assertIn("get_allowed_institutions", api)
		self.assertIn("You do not have access to this Institution", api)
		self.assertIn("_address_is_exclusive_to_institution", api)
		self.assertIn('frappe.db.count("EduEdge School Branch", {"address": address_name})', api)
		self.assertIn('address_doc.has_permission("write")', api)
		self.assertIn('frappe.has_permission("Address", "create")', api)
		self.assertIn("search_letter_heads", api)
		self.assertIn('letter_head.check_permission("read")', api)

	def test_branch_switch_shell_report_card_and_navigation_use_institution_identity(self):
		branch_api = (APP / "api" / "branch_context.py").read_text()
		self.assertIn("get_institution_branding", branch_api)
		self.assertIn('context["branding"] = branding', branch_api)
		self.assertIn('"logo",', branch_api)

		bridge = (APP / "public" / "js" / "eduedge_profile_identity.bundle.js").read_text()
		self.assertIn("eduedge:institution-context-changed", bridge)
		self.assertIn("identity.tenant_logo = context.logo", bridge)
		self.assertIn("contact_identity", bridge)

		report_api = (APP / "api" / "report_cards_profiled.py").read_text()
		self.assertIn("_attach_institution_identity", report_api)
		self.assertIn("report_card_letter_head", report_api)
		template = (APP / "templates" / "report_card.html").read_text()
		self.assertIn("branding.official_name", template)
		self.assertIn("branding.formatted_address", template)
		self.assertIn("branding.report_footer", template)

		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text()
		access = (APP / "access_control.py").read_text()
		for route in ("/app/eduedge-my-profile", "/app/eduedge-institution-profile"):
			self.assertIn(route, navigation)
			self.assertIn(route, access)

	def test_hooks_pages_and_ci_are_wired(self):
		hooks = (APP / "hooks.py").read_text()
		self.assertIn('"eduedge_profile_identity.bundle.js"', hooks)
		self.assertIn('"EduEdge User Profile": "eduedge.education.profile_permissions.user_profile_query"', hooks)
		self.assertIn('"EduEdge User Profile": "eduedge.education.profile_permissions.has_user_profile_permission"', hooks)
		self.assertIn('"eduedge.api.report_cards.get_report_card": "eduedge.api.report_cards_profiled.get_report_card"', hooks)

		workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
		for path in (
			"eduedge/public/js/eduedge_profile_identity.bundle.js",
			"eduedge/public/js/eduedge_my_profile.bundle.js",
			"eduedge/public/js/eduedge_institution_profile.bundle.js",
			"eduedge/eduedge/page/eduedge_my_profile/eduedge_my_profile.js",
			"eduedge/eduedge/page/eduedge_institution_profile/eduedge_institution_profile.js",
		):
			self.assertIn(f"node --check {path}", workflow)


if __name__ == "__main__":
	unittest.main()
