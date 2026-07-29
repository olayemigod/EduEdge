from __future__ import annotations

from mimetypes import guess_type
from pathlib import Path

import filetype
import frappe
from frappe import _
from frappe.utils.file_manager import save_file

from eduedge.api.profiles import _resolve_institution


MAX_INSTITUTION_LOGO_BYTES = 2 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_MIMETYPES = {"image/jpeg", "image/png", "image/webp"}


def _uploaded_logo() -> tuple[str, bytes]:
	filename = str(getattr(frappe.local, "uploaded_filename", "") or "").strip()
	content = getattr(frappe.local, "uploaded_file", None)
	if not filename or content is None:
		frappe.throw(_("Select an Institution logo to upload."), frappe.ValidationError)
	if isinstance(content, str):
		content = content.encode("utf-8")
	if not isinstance(content, bytes | bytearray):
		frappe.throw(_("The uploaded Institution logo could not be read."), frappe.ValidationError)
	content = bytes(content)
	if len(content) > MAX_INSTITUTION_LOGO_BYTES:
		frappe.throw(_("Institution logos must not exceed 2 MB."), frappe.ValidationError)

	extension = Path(filename).suffix.lower()
	declared_mimetype = (guess_type(filename)[0] or "").lower()
	detected_kind = filetype.guess(content)
	detected_mimetype = (detected_kind.mime if detected_kind else "").lower()
	if (
		extension not in ALLOWED_IMAGE_EXTENSIONS
		or declared_mimetype not in ALLOWED_IMAGE_MIMETYPES
		or detected_mimetype not in ALLOWED_IMAGE_MIMETYPES
	):
		frappe.throw(_("Only JPG, PNG, and WebP images are allowed."), frappe.ValidationError)
	return filename, content


@frappe.whitelist(methods=["POST"])
def upload_institution_logo():
	"""Save one public logo for a permitted Institution.

	Frappe's upload handler supplies the uploaded bytes. The Institution target is
	resolved from the submitted DocType/document context and revalidated through
	EduEdge Institution access before the public File and logo field are saved.
	"""
	if str(frappe.form_dict.get("doctype") or "") != "EduEdge Institution":
		frappe.throw(_("Invalid Institution logo target."), frappe.ValidationError)

	name = _resolve_institution(frappe.form_dict.get("docname"))
	institution_doc = frappe.get_doc("EduEdge Institution", name)
	institution_doc.check_permission("write")
	filename, content = _uploaded_logo()

	file_doc = save_file(
		filename,
		content,
		"EduEdge Institution",
		name,
		folder="Home/Attachments",
		is_private=0,
		df="logo",
	)
	if file_doc.is_private:
		frappe.throw(_("Institution logos must be uploaded as public images."), frappe.ValidationError)

	institution_doc.logo = file_doc.file_url
	institution_doc.save()
	frappe.clear_cache(doctype="EduEdge Institution")
	return file_doc
