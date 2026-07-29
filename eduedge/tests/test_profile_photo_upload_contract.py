from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestProfilePhotoUploadContract(unittest.TestCase):
	def test_upload_target_is_session_fixed_and_private(self):
		upload = (APP / "api" / "profile_uploads.py").read_text()
		self.assertIn('@frappe.whitelist(methods=["POST"])', upload)
		self.assertIn('user = _require_login()', upload)
		self.assertIn('frappe.get_doc("User", user)', upload)
		self.assertIn('user_doc.check_permission("write")', upload)
		self.assertIn('getattr(frappe.local, "uploaded_file", None)', upload)
		self.assertIn('getattr(frappe.local, "uploaded_filename", "")', upload)
		self.assertIn('MAX_PROFILE_IMAGE_BYTES = 2 * 1024 * 1024', upload)
		self.assertIn('ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}', upload)
		self.assertIn('ALLOWED_IMAGE_MIMETYPES = {"image/jpeg", "image/png", "image/webp"}', upload)
		self.assertIn('"User",\n\t\tuser,', upload)
		self.assertIn('is_private=1', upload)
		self.assertIn('df="user_image"', upload)
		self.assertNotIn('target_user', upload)
		self.assertNotIn('ignore_permissions', upload)

	def test_uploader_uses_custom_method_without_direct_user_attachment(self):
		bundle = (APP / "public" / "js" / "eduedge_profile_identity.bundle.js").read_text()
		self.assertIn('PROFILE_PHOTO_UPLOAD_METHOD = "eduedge.api.profile_uploads.upload_my_profile_photo"', bundle)
		self.assertIn('method: PROFILE_PHOTO_UPLOAD_METHOD', bundle)
		self.assertIn('make_attachments_public: false', bundle)
		self.assertIn('allow_toggle_private: false', bundle)
		self.assertIn('disable_file_browser: true', bundle)
		self.assertIn('allow_web_link: false', bundle)
		self.assertIn('allow_google_drive: false', bundle)
		self.assertIn('installProfilePhotoUploader();', bundle)
		self.assertNotIn('doctype: "User"', bundle)
		self.assertNotIn('docname: frappe.session.user', bundle)


if __name__ == "__main__":
	unittest.main()
