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
	if (
		not file_doc
		or not file_doc.is_private
		or file_doc.attached_to_doctype != ISSUE_DOCTYPE
		or file_doc.attached_to_name != issue.name
	):
		frappe.throw(_("Official Report Card PDF archive could not be created."), frappe.ValidationError)
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
	actual_hash = hashlib.sha256((row.payload_json or "").encode("utf-8")).hexdigest()
	if actual_hash != row.payload_hash:
		frappe.throw(_("Issued Report Card integrity check failed."), frappe.ValidationError)
	payload = json.loads(row.payload_json)
	payload["issue_record"] = {
		"name": row.name,
		"issue_version": int(row.issue_version or 1),
		"payload_hash": row.payload_hash,
		"pdf_sha256": row.get("pdf_sha256"),
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
			["pdf_sha256", "pdf_size_bytes"],
			as_dict=True,
		)
		if not archive:
			frappe.throw(_("Issued Report Card archive record does not exist."), frappe.DoesNotExistError)
		if archive.pdf_sha256:
			return get_archived_report_card_pdf(issue_name)
	# Legacy Issues created before PDF archival, plus draft previews, retain dynamic rendering.
	return render_report_card_pdf(payload)


def get_archived_report_card_pdf(issue_name: str) -> bytes:
	archive = frappe.db.get_value(
		ISSUE_DOCTYPE,
		issue_name,
		["pdf_sha256", "pdf_filename", "pdf_size_bytes"],
		as_dict=True,
	)
	if not archive or not archive.pdf_sha256:
		frappe.throw(_("Official Report Card PDF archive is unavailable."), frappe.ValidationError)

	files = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": ISSUE_DOCTYPE,
			"attached_to_name": issue_name,
			"is_private": 1,
		},
		fields=["name", "file_name", "file_type"],
		order_by="creation asc",
	)
	pdf_files = [
		row for row in files
		if str(row.file_type or "").upper() == "PDF"
		or str(row.file_name or "").lower().endswith(".pdf")
	]
	if len(pdf_files) != 1:
		frappe.throw(_("Official Report Card PDF archive is missing or ambiguous."), frappe.ValidationError)

	file_doc = frappe.get_doc("File", pdf_files[0].name)
	content = file_doc.get_content(encodings=[])
	if not isinstance(content, (bytes, bytearray)):
		frappe.throw(_("Official Report Card PDF archive is unreadable."), frappe.ValidationError)
	pdf_bytes = bytes(content)
	actual_hash = hashlib.sha256(pdf_bytes).hexdigest()
	if not hmac.compare_digest(actual_hash, str(archive.pdf_sha256 or "")):
		frappe.throw(_("Official Report Card PDF integrity check failed."), frappe.ValidationError)
	if archive.pdf_size_bytes and len(pdf_bytes) != int(archive.pdf_size_bytes):
		frappe.throw(_("Official Report Card PDF size check failed."), frappe.ValidationError)
	return pdf_bytes


def has_archived_report_card_file_permission(doc, ptype=None, user=None, debug=False):
	"""Archived Issue PDF attachments may be read normally but never changed or deleted."""
	if not doc or not getattr(doc, "name", None):
		return True
	current = frappe.db.get_value(
		"File",
		doc.name,
		["attached_to_doctype", "attached_to_name"],
		as_dict=True,
	)
	attached_to_issue = (
		getattr(doc, "attached_to_doctype", None) == ISSUE_DOCTYPE
		or (current and current.attached_to_doctype == ISSUE_DOCTYPE)
	)
	if attached_to_issue and ptype in {"write", "delete"}:
		return False
	return True


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
	rows = frappe.get_all(
		ISSUE_DOCTYPE,
		filters={"result_publication": publication, "student": student},
		fields=[
			"name",
			"issue_version",
			"publication_version",
			"supersedes_issue",
			"payload_hash",
			"issued_by",
			"issued_on",
		],
		order_by="issue_version desc, creation desc",
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
