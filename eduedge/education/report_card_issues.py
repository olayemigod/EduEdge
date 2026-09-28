from __future__ import annotations

import hashlib
import hmac
import json
from copy import deepcopy

import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe.utils.pdf import get_pdf

from eduedge.services.institution_branding import get_report_identity
from eduedge.education.result_verification import build_issue_verification

ISSUE_DOCTYPE = "EduEdge Report Card Issue"


def generate_verification_token() -> str:
	while True:
		token = frappe.generate_hash(length=32)
		if not frappe.db.exists(ISSUE_DOCTYPE, {"verification_token": token}):
			return token


def ensure_issue_verification_token(issue_name: str, current_token: str | None = None) -> str:
	if current_token:
		return current_token
	token = generate_verification_token()
	frappe.db.set_value(
		ISSUE_DOCTYPE,
		issue_name,
		"verification_token",
		token,
		update_modified=False,
	)
	return token


def create_report_card_issue(review: str) -> str:
	review_doc = frappe.get_doc("EduEdge Report Card Review", review)
	if review_doc.progression_status != "Approved":
		frappe.throw(_("Approve the Report Card Review before issuing the official report card."), frappe.ValidationError)

	from eduedge.education.report_cards import get_student_report_card_payload

	payload = get_student_report_card_payload(
		review_doc.result_publication,
		review_doc.student,
		_prefer_issued=False,
	)
	payload = _freeze_institution_identity(payload)
	payload = _freeze_issue_render_settings(payload)
	publication = payload.get("publication") or {}
	issue_version = _next_issue_version(review_doc.result_publication, review_doc.student)
	issued_on = now_datetime()
	verification_token = generate_verification_token()
	payload["issue"] = {
		"issue_version": issue_version,
		"issued_by": frappe.session.user,
		"issued_on": str(issued_on),
		"report_card_review": review_doc.name,
	}
	previous = _latest_issue_row(review_doc.result_publication, review_doc.student)
	if previous:
		payload["issue"]["supersedes_issue"] = previous.name

	payload_json = _canonical_json(payload)
	payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
	issue = frappe.get_doc(
		{
			"doctype": ISSUE_DOCTYPE,
			"result_publication": review_doc.result_publication,
			"publication_version": int(publication.get("publication_version") or 1),
			"report_card_review": review_doc.name,
			"issue_version": issue_version,
			"supersedes_issue": previous.name if previous else None,
			"student": review_doc.student,
			"student_name": payload.get("student", {}).get("student_name"),
			"school_branch": review_doc.school_branch,
			"student_group": review_doc.student_group,
			"academic_year": review_doc.academic_year,
			"academic_term": review_doc.academic_term,
			"result_mode": publication.get("result_mode") or "Terminal",
			"result_profile": publication.get("result_profile"),
			"payload_hash": payload_hash,
			"verification_token": verification_token,
			"issued_by": frappe.session.user,
			"issued_on": issued_on,
			"payload_json": payload_json,
		}
	)
	# The exact Issue identity must exist in the PDF before the immutable row is inserted.
	issue.set_new_name()
	render_payload = deepcopy(payload)
	render_payload["issue_record"] = {
		"name": issue.name,
		"issue_version": issue_version,
		"payload_hash": payload_hash,
	}
	render_payload["verification"] = build_issue_verification(issue.name, verification_token)
	pdf_bytes = render_report_card_pdf(render_payload)
	pdf_filename = f"Report Card {issue.name}.pdf"
	issue.pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
	issue.pdf_filename = pdf_filename
	issue.pdf_size_bytes = len(pdf_bytes)
	issue.insert(ignore_permissions=True)
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": pdf_filename,
			"content": pdf_bytes,
			"is_private": 1,
			"attached_to_doctype": ISSUE_DOCTYPE,
			"attached_to_name": issue.name,
		}
	)
	file_doc.insert(ignore_permissions=True)
	# Generated official artifacts must not inherit the issuing operator as File owner,
	# because Frappe allows a private File owner before checking the attached document.
	frappe.db.set_value("File", file_doc.name, "owner", "Administrator", update_modified=False)
	file_doc.owner = "Administrator"
	if (
		not file_doc
		or not file_doc.is_private
		or file_doc.owner != "Administrator"
		or file_doc.attached_to_doctype != ISSUE_DOCTYPE
		or file_doc.attached_to_name != issue.name
		or file_doc.file_name != pdf_filename
	):
		frappe.throw(_("Official Report Card PDF archive could not be created."), frappe.ValidationError)
	# Verify the persisted private artifact before the issuance transaction can succeed.
	get_archived_report_card_pdf(issue.name)
	return issue.name


def get_effective_issued_payload(publication: str, student: str) -> dict | None:
	review = frappe.db.get_value(
		"EduEdge Report Card Review",
		{"result_publication": publication, "student": student},
		["name", "progression_status"],
		as_dict=True,
	)
	if not review or review.progression_status != "Approved":
		return None
	row = _latest_issue_row(publication, student)
	if not row:
		return None
	return get_issued_payload_by_name(row.name, row=row)


def get_issued_payload_by_name(issue_name: str, *, row=None) -> dict:
	"""Load one immutable Issue version regardless of whether it is current, superseded, or reopened."""
	row = row or frappe.db.get_value(
		ISSUE_DOCTYPE,
		issue_name,
		[
			"name",
			"issue_version",
			"payload_hash",
			"payload_json",
			"verification_token",
			"pdf_sha256",
			"pdf_filename",
			"pdf_size_bytes",
		],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Issued Report Card does not exist."), frappe.DoesNotExistError)
	actual_hash = hashlib.sha256((row.payload_json or "").encode("utf-8")).hexdigest()
	if not hmac.compare_digest(actual_hash, str(row.payload_hash or "")):
		frappe.throw(_("Issued Report Card integrity check failed."), frappe.ValidationError)
	try:
		payload = json.loads(row.payload_json or "{}")
	except (TypeError, ValueError):
		frappe.throw(_("Issued Report Card payload is unreadable."), frappe.ValidationError)
	if not isinstance(payload, dict):
		frappe.throw(_("Issued Report Card payload is unreadable."), frappe.ValidationError)
	payload["issue_record"] = {
		"name": row.name,
		"issue_version": int(row.issue_version or 1),
		"payload_hash": row.payload_hash,
		"pdf_sha256": row.get("pdf_sha256"),
		"pdf_filename": row.get("pdf_filename"),
		"pdf_size_bytes": row.get("pdf_size_bytes"),
	}
	verification_token = ensure_issue_verification_token(row.name, row.get("verification_token"))
	payload["verification"] = build_issue_verification(row.name, verification_token)
	return payload


def _freeze_institution_identity(payload: dict) -> dict:
	branch = payload.get("branch") or {}
	identity = get_report_identity(branch=branch.get("name"))
	payload["institution"] = identity["institution"]
	payload["branding"] = identity["branding"]
	payload["terminology"] = identity["terminology"]
	if identity.get("address"):
		payload["address"] = identity["address"]
	return payload


def _freeze_issue_render_settings(payload: dict) -> dict:
	payload["render_settings"] = _current_report_card_render_settings(payload)
	return payload


def resolve_report_card_render_settings(payload: dict) -> dict:
	"""Use immutable render settings for issued reports, with legacy fallback."""
	if payload.get("issue") or payload.get("issue_record"):
		frozen = payload.get("render_settings")
		if isinstance(frozen, dict):
			return {
				"letterhead": frozen.get("letterhead") or "",
				"show_marks": bool(frozen.get("show_marks")),
			}
	return _current_report_card_render_settings(payload)


def render_report_card_pdf(payload: dict) -> bytes:
	render_settings = resolve_report_card_render_settings(payload)
	html = frappe.render_template(
		"eduedge/templates/report_card.html",
		{
			**payload,
			"letterhead": render_settings["letterhead"],
			"show_marks": render_settings["show_marks"],
		},
	)
	final_html = frappe.render_template(
		"frappe/www/printview.html",
		{"body": html, "title": _("Student Report Card")},
	)
	pdf_bytes = get_pdf(final_html)
	if not isinstance(pdf_bytes, (bytes, bytearray)) or not pdf_bytes:
		frappe.throw(_("Official Report Card PDF generation failed."), frappe.ValidationError)
	return bytes(pdf_bytes)


def resolve_report_card_pdf(payload: dict) -> bytes:
	"""Serve archived bytes for new Issues and render dynamically only for legacy/unissued reports."""
	issue_record = payload.get("issue_record") or {}
	issue_name = str(issue_record.get("name") or "").strip()
	if issue_name:
		archive = frappe.db.get_value(
			ISSUE_DOCTYPE,
			issue_name,
			["pdf_sha256", "pdf_filename", "pdf_size_bytes"],
			as_dict=True,
		)
		if not archive:
			frappe.throw(_("Issued Report Card archive record does not exist."), frappe.DoesNotExistError)
		archive_values = (
			str(archive.pdf_sha256 or "").strip(),
			str(archive.pdf_filename or "").strip(),
			int(archive.pdf_size_bytes or 0),
		)
		if any(archive_values):
			if not all(archive_values):
				frappe.throw(_("Official Report Card PDF archive metadata is incomplete."), frappe.ValidationError)
			return get_archived_report_card_pdf(issue_name)
	# Only true legacy Issues with no archive metadata may render dynamically.
	return render_report_card_pdf(payload)


def inspect_report_card_pdf_archive(issue_name: str, *, include_content: bool = False) -> dict:
	"""Inspect one Issue's official PDF without exposing a private File URL."""
	archive = frappe.db.get_value(
		ISSUE_DOCTYPE,
		issue_name,
		["pdf_sha256", "pdf_filename", "pdf_size_bytes"],
		as_dict=True,
	)
	if not archive:
		return {
			"issue": issue_name,
			"status": "Missing Issue",
			"ok": False,
			"legacy": False,
			"detail": _("The Report Card Issue record does not exist."),
		}

	expected_hash = str(archive.pdf_sha256 or "").strip().lower()
	filename = str(archive.pdf_filename or "").strip()
	expected_size = int(archive.pdf_size_bytes or 0)
	metadata_values = (expected_hash, filename, expected_size)
	base = {
		"issue": issue_name,
		"pdf_filename": filename,
		"expected_size_bytes": expected_size or None,
		"actual_size_bytes": None,
		"pdf_fingerprint": expected_hash[:16].upper() if expected_hash else "",
	}
	if not any(metadata_values):
		return {
			**base,
			"status": "Legacy",
			"ok": True,
			"legacy": True,
			"detail": _("This Issue predates immutable PDF archival."),
		}
	if not all(metadata_values):
		return {
			**base,
			"status": "Incomplete Metadata",
			"ok": False,
			"legacy": False,
			"detail": _("PDF archive metadata is incomplete."),
		}

	files = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": ISSUE_DOCTYPE,
			"attached_to_name": issue_name,
			"is_private": 1,
			"file_name": filename,
		},
		fields=["name", "file_name", "file_type", "owner"],
		order_by="creation asc",
	)
	if not files:
		return {
			**base,
			"status": "Missing File",
			"ok": False,
			"legacy": False,
			"detail": _("The private archived PDF File is missing."),
		}
	if len(files) > 1:
		return {
			**base,
			"status": "Ambiguous File",
			"ok": False,
			"legacy": False,
			"detail": _("Multiple private archived PDF Files match this Issue."),
		}

	file_row = files[0]
	if file_row.owner != "Administrator":
		return {
			**base,
			"status": "Invalid Owner",
			"ok": False,
			"legacy": False,
			"detail": _("The archived PDF File owner is invalid."),
		}
	if str(file_row.file_type or "").upper() != "PDF" and not str(file_row.file_name or "").lower().endswith(".pdf"):
		return {
			**base,
			"status": "Invalid File Type",
			"ok": False,
			"legacy": False,
			"detail": _("The archived artifact is not a PDF."),
		}

	try:
		content = frappe.get_doc("File", file_row.name).get_content(encodings=[])
	except Exception:
		return {
			**base,
			"status": "Unreadable File",
			"ok": False,
			"legacy": False,
			"detail": _("The archived PDF bytes could not be read."),
		}
	if not isinstance(content, (bytes, bytearray)):
		return {
			**base,
			"status": "Unreadable File",
			"ok": False,
			"legacy": False,
			"detail": _("The archived PDF bytes could not be read."),
		}

	pdf_bytes = bytes(content)
	actual_size = len(pdf_bytes)
	if actual_size != expected_size:
		return {
			**base,
			"actual_size_bytes": actual_size,
			"status": "Size Mismatch",
			"ok": False,
			"legacy": False,
			"detail": _("The archived PDF byte size does not match the Issue metadata."),
		}

	actual_hash = hashlib.sha256(pdf_bytes).hexdigest()
	if not hmac.compare_digest(actual_hash, expected_hash):
		return {
			**base,
			"actual_size_bytes": actual_size,
			"status": "Hash Mismatch",
			"ok": False,
			"legacy": False,
			"detail": _("The archived PDF SHA-256 does not match the Issue metadata."),
		}

	result = {
		**base,
		"actual_size_bytes": actual_size,
		"status": "Healthy",
		"ok": True,
		"legacy": False,
		"detail": _("The immutable archived PDF passed filename, ownership, size and SHA-256 checks."),
	}
	if include_content:
		result["_content"] = pdf_bytes
	return result


def inspect_report_card_issue_integrity(issue_name: str) -> dict:
	"""Inspect immutable payload and official PDF integrity for one issued Report Card."""
	row = frappe.db.get_value(
		ISSUE_DOCTYPE,
		issue_name,
		["payload_hash", "payload_json"],
		as_dict=True,
	)
	if not row:
		return {
			"issue": issue_name,
			"status": "Missing Issue",
			"ok": False,
			"legacy": False,
			"detail": _("The Report Card Issue record does not exist."),
			"payload_status": "Missing Issue",
			"payload_ok": False,
			"payload_fingerprint": "",
			"pdf_status": "Not Checked",
			"pdf_ok": False,
		}

	expected_payload_hash = str(row.payload_hash or "").strip().lower()
	payload_json = row.payload_json or ""
	actual_payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
	payload_base = {
		"payload_fingerprint": expected_payload_hash[:16].upper() if expected_payload_hash else "",
		"payload_ok": False,
	}

	if not expected_payload_hash:
		return {
			"issue": issue_name,
			"status": "Missing Payload Hash",
			"ok": False,
			"legacy": False,
			"detail": _("Immutable Report Card payload hash is missing."),
			"payload_status": "Missing Payload Hash",
			"pdf_status": "Not Checked",
			"pdf_ok": False,
			**payload_base,
		}
	if not hmac.compare_digest(actual_payload_hash, expected_payload_hash):
		return {
			"issue": issue_name,
			"status": "Payload Hash Mismatch",
			"ok": False,
			"legacy": False,
			"detail": _("Immutable Report Card payload SHA-256 does not match the Issue metadata."),
			"payload_status": "Hash Mismatch",
			"pdf_status": "Not Checked",
			"pdf_ok": False,
			**payload_base,
		}
	try:
		payload = json.loads(payload_json or "{}")
	except (TypeError, ValueError):
		return {
			"issue": issue_name,
			"status": "Unreadable Payload",
			"ok": False,
			"legacy": False,
			"detail": _("Immutable Report Card payload JSON is unreadable."),
			"payload_status": "Unreadable",
			"pdf_status": "Not Checked",
			"pdf_ok": False,
			**payload_base,
		}
	if not isinstance(payload, dict):
		return {
			"issue": issue_name,
			"status": "Invalid Payload",
			"ok": False,
			"legacy": False,
			"detail": _("Immutable Report Card payload JSON has an invalid shape."),
			"payload_status": "Invalid",
			"pdf_status": "Not Checked",
			"pdf_ok": False,
			**payload_base,
		}

	pdf = inspect_report_card_pdf_archive(issue_name)
	return {
		**pdf,
		"status": pdf.get("status") or "Unknown",
		"ok": bool(pdf.get("ok")),
		"legacy": bool(pdf.get("legacy")),
		"detail": pdf.get("detail") or "",
		"payload_status": "Healthy",
		"payload_ok": True,
		"payload_fingerprint": expected_payload_hash[:16].upper(),
		"pdf_status": pdf.get("status") or "Unknown",
		"pdf_ok": bool(pdf.get("ok")),
	}


def get_archived_report_card_pdf(issue_name: str) -> bytes:
	audit = inspect_report_card_pdf_archive(issue_name, include_content=True)
	if audit.get("status") != "Healthy":
		frappe.throw(
			_("Official Report Card PDF archive failed integrity validation: {0}.").format(
				audit.get("status") or _("Unknown")
			),
			frappe.ValidationError,
		)
	content = audit.get("_content")
	if not isinstance(content, (bytes, bytearray)):
		frappe.throw(_("Official Report Card PDF archive is unreadable."), frappe.ValidationError)
	return bytes(content)


def has_archived_report_card_file_permission(doc, ptype=None, user=None, debug=False):
	"""Keep archived Issue files immutable and bind reads to current Issue permission."""
	if not doc:
		return True

	attached_doctype = getattr(doc, "attached_to_doctype", None)
	attached_name = getattr(doc, "attached_to_name", None)
	if getattr(doc, "name", None) and not doc.is_new():
		current = frappe.db.get_value(
			"File",
			doc.name,
			["attached_to_doctype", "attached_to_name"],
			as_dict=True,
		)
		if current and current.attached_to_doctype == ISSUE_DOCTYPE:
			attached_doctype = current.attached_to_doctype
			attached_name = current.attached_to_name

	if attached_doctype != ISSUE_DOCTYPE:
		return True
	if ptype in {"create", "write", "delete", "share"}:
		return False
	if ptype in {"read", "select", "print", "email"}:
		if not attached_name:
			return False
		return bool(
			frappe.has_permission(
				ISSUE_DOCTYPE,
				ptype="read",
				doc=attached_name,
				user=user,
				print_logs=False,
			)
		)
	return False


def _current_report_card_render_settings(payload: dict) -> dict:
	settings = frappe.get_single("EduEdge Settings")
	letter_head_name = (
		(payload.get("branding") or {}).get("report_card_letter_head")
		or settings.report_card_letter_head
	)
	letterhead = ""
	if letter_head_name:
		letterhead = frappe.db.get_value("Letter Head", letter_head_name, "content") or ""
	return {
		"letterhead": letterhead,
		"show_marks": bool(settings.report_card_show_marks),
	}

def _latest_issue_row(publication: str, student: str):
	rows = frappe.get_all(
		ISSUE_DOCTYPE,
		filters={"result_publication": publication, "student": student},
		fields=["name", "issue_version", "payload_hash", "payload_json", "verification_token", "issued_on", "supersedes_issue", "pdf_sha256", "pdf_filename", "pdf_size_bytes"],
		order_by="issue_version desc, creation desc",
		limit=1,
	)
	return rows[0] if rows else None


def get_report_card_issue_history(publication: str, student: str) -> list[dict]:
	return get_report_card_issue_history_for_publications([publication], student)


def get_report_card_issue_history_for_publications(
	publications: list[str],
	student: str,
) -> list[dict]:
	publication_names = [name for name in publications if name]
	if not publication_names:
		return []
	rows = frappe.get_all(
		ISSUE_DOCTYPE,
		filters={
			"result_publication": ["in", publication_names],
			"student": student,
		},
		fields=[
			"name",
			"result_publication",
			"issue_version",
			"publication_version",
			"supersedes_issue",
			"payload_hash",
			"issued_by",
			"issued_on",
		],
		order_by="publication_version desc, issue_version desc, creation desc",
		page_length=0,
	)
	return [
		{
			**dict(row),
			"fingerprint": str(row.payload_hash or "")[:16].upper(),
		}
		for row in rows
	]


def _next_issue_version(publication: str, student: str) -> int:
	previous = _latest_issue_row(publication, student)
	return int(previous.issue_version or 0) + 1 if previous else 1


def _canonical_json(value: dict) -> str:
	return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
