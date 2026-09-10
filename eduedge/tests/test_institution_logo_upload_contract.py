from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstitutionLogoUploadContract(unittest.TestCase):
	def test_server_upload_is_public_permission_aware_and_image_validated(self):
		upload = (APP / "api" / "institution_logo_uploads.py").read_text()
		self.assertIn('frappe.form_dict.get("docname")', upload)
		self.assertIn('_resolve_institution(frappe.form_dict.get("docname"))', upload)
		self.assertIn('institution_doc.check_permission("write")', upload)
		self.assertIn('ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}', upload)
		self.assertIn('ALLOWED_IMAGE_MIMETYPES = {"image/jpeg", "image/png", "image/webp"}', upload)
		self.assertIn("filetype.guess(content)", upload)
		self.assertIn("MAX_INSTITUTION_LOGO_BYTES = 2 * 1024 * 1024", upload)
		self.assertIn("is_private=0", upload)
		self.assertIn('df="logo"', upload)
		self.assertIn("institution_doc.logo = file_doc.file_url", upload)

	def test_ui_uses_dedicated_public_logo_uploader(self):
		bridge = (APP / "public" / "js" / "eduedge_profile_identity.bundle.js").read_text()
		self.assertIn(
			'const INSTITUTION_LOGO_UPLOAD_METHOD = "eduedge.api.institution_logo_uploads.upload_institution_logo"',
			bridge,
		)
		self.assertIn("installInstitutionLogoUploader", bridge)
		self.assertIn("method: INSTITUTION_LOGO_UPLOAD_METHOD", bridge)
		self.assertIn('doctype: "EduEdge Institution"', bridge)
		self.assertIn("docname: institution", bridge)
		self.assertIn("make_attachments_public: true", bridge)
		self.assertIn("allow_toggle_private: false", bridge)
		self.assertIn("disable_file_browser: true", bridge)
		self.assertIn("PROFILE_IMAGE_TYPES", bridge)
		self.assertIn("PROFILE_IMAGE_MAX_BYTES", bridge)


if __name__ == "__main__":
	unittest.main()
