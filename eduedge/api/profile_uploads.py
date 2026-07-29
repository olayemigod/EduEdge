from __future__ import annotations

from mimetypes import guess_type
from pathlib import Path

import frappe
from frappe import _
from frappe.utils.file_manager import save_file


MAX_PROFILE_IMAGE_BYTES = 2 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_MIMETYPES = {"image/jpeg", "image/png", "image/webp"}


def _require_login() -> str:
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	return user


def _uploaded_image() -> tuple[str, bytes]:
	filename = str(getattr(frappe.local, "uploaded_filename", "") or "").strip()
	content = getattr(frappe.local, "uploaded_file", None)
	if not filename or content is None:
		frappe.throw(_("Select an image to upload."), frappe.ValidationError)
	if isinstance(content, str):
		content = content.encode("utf-8")
	if not isinstance(content, bytes | bytearray):
		frappe.throw(_("The uploaded image could not be read."), frappe.ValidationError)
	content = bytes(content)
	if len(content) > MAX_PROFILE_IMAGE_BYTES:
		frappe.throw(_("Profile photos must not exceed 2 MB."), frappe.ValidationError)

	extension = Path(filename).suffix.lower()
	mimetype = (guess_type(filename)[0] or "").lower()
	if extension not in ALLOWED_IMAGE_EXTENSIONS or mimetype not in ALLOWED_IMAGE_MIMETYPES:
		frappe.throw(_("Only JPG, PNG, and WebP images are allowed."), frappe.ValidationError)
	return filename, content


@frappe.whitelist(methods=["POST"])
def upload_my_profile_photo():
	"""Save one private profile photo for the authenticated user.

	This method is called by Frappe's upload_file handler without a client-supplied
	DocType or document name. The target User is always resolved from the session.
	"""
	user = _require_login()
	user_doc = frappe.get_doc("User", user)
	user_doc.check_permission("write")
	filename, content = _uploaded_image()

	file_doc = save_file(
		filename,
		content,
		"User",
		user,
		folder="Home/Attachments",
		is_private=1,
		df="user_image",
	)
	user_doc.user_image = file_doc.file_url
	user_doc.save()
	frappe.clear_cache(user=user)
	return file_doc
