from __future__ import annotations

import os
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, validate_email_address

from eduedge.services.branch_context import get_allowed_institutions, get_branch_access_profile
from eduedge.services.institution_branding import (
	get_active_communication_identity,
	get_institution_branding,
)
from eduedge.services.institution_context import get_effective_institution_context


PROFILE_DOCTYPE = "EduEdge User Profile"
MAX_PROFILE_IMAGE_BYTES = 2 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
STANDARD_USER_FIELDS = (
	"first_name",
	"middle_name",
	"last_name",
	"phone",
	"mobile_no",
	"location",
	"bio",
)
PROFILE_EDITABLE_FIELDS = (
	"preferred_name",
	"professional_title",
	"whatsapp_number",
	"preferred_communication",
	"address_line_1",
	"address_line_2",
	"city",
	"state",
	"postal_code",
	"country",
	"emergency_contact_name",
	"emergency_contact_relationship",
	"emergency_contact_phone",
)
INSTITUTION_EDITABLE_FIELDS = (
	"institution_name",
	"official_name",
	"short_name",
	"motto",
	"phone",
	"whatsapp_number",
	"email",
	"website",
	"report_card_letter_head",
	"report_footer",
)


def _require_login() -> str:
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	return user


def _parse_payload(value: str | dict | None) -> dict:
	if not value:
		return {}
	if isinstance(value, dict):
		return value
	parsed = frappe.parse_json(value)
	if not isinstance(parsed, dict):
		frappe.throw(_("Profile payload must be an object."), frappe.ValidationError)
	return parsed


def _clean(value: Any, *, limit: int = 500) -> str:
	text = str(value or "").strip()
	if len(text) > limit:
		frappe.throw(_("A profile value is longer than the allowed limit."), frappe.ValidationError)
	return text


def _validate_country(country: str | None, *, required: bool = False) -> str:
	country = _clean(country, limit=140)
	if required and not country:
		frappe.throw(_("Country is required."), frappe.ValidationError)
	if country and not frappe.db.exists("Country", country):
		frappe.throw(_("Select a valid Country."), frappe.ValidationError)
	return country


def _user_fields() -> list[str]:
	meta = frappe.get_meta("User")
	return [
		fieldname
		for fieldname in (
			"name",
			"email",
			"full_name",
			"user_image",
			"enabled",
			*STANDARD_USER_FIELDS,
		)
		if fieldname == "name" or meta.has_field(fieldname)
	]


def _profile_fields() -> list[str]:
	meta = frappe.get_meta(PROFILE_DOCTYPE)
	return [
		fieldname
		for fieldname in ("name", "user", *PROFILE_EDITABLE_FIELDS)
		if fieldname == "name" or meta.has_field(fieldname)
	]


def _employee_rows(user: str) -> list[dict]:
	if not frappe.db.exists("DocType", "Employee"):
		return []
	meta = frappe.get_meta("Employee")
	fields = [
		field
		for field in (
			"name",
			"employee_name",
			"status",
			"company",
			"department",
			"designation",
			"branch",
			"image",
		)
		if field == "name" or meta.has_field(field)
	]
	return frappe.get_all(
		"Employee",
		filters={"user_id": user, "status": "Active"},
		fields=fields,
		order_by="modified desc",
		limit_page_length=20,
	)


def _instructor_rows(employees: list[dict]) -> list[dict]:
	if not employees or not frappe.db.exists("DocType", "Instructor"):
		return []
	employee_names = [row["name"] for row in employees if row.get("name")]
	if not employee_names:
		return []
	meta = frappe.get_meta("Instructor")
	fields = [
		field
		for field in ("name", "instructor_name", "employee", "status", "department")
		if field == "name" or meta.has_field(field)
	]
	return frappe.get_all(
		"Instructor",
		filters={"employee": ["in", employee_names], "status": "Active"},
		fields=fields,
		order_by="modified desc",
		limit_page_length=20,
	)


def _get_profile_doc(user: str):
	name = frappe.db.exists(PROFILE_DOCTYPE, {"user": user})
	return frappe.get_doc(PROFILE_DOCTYPE, name) if name else None


def _profile_payload(user: str) -> dict:
	name = frappe.db.exists(PROFILE_DOCTYPE, {"user": user})
	if not name:
		return {"user": user}
	return dict(frappe.db.get_value(PROFILE_DOCTYPE, name, _profile_fields(), as_dict=True) or {})


def _profile_completeness(user_row: dict, profile_row: dict) -> dict:
	checks = {
		"first_name": user_row.get("first_name"),
		"mobile_no": user_row.get("mobile_no"),
		"profile_photo": user_row.get("user_image"),
		"address_line_1": profile_row.get("address_line_1"),
		"city": profile_row.get("city"),
		"country": profile_row.get("country"),
		"emergency_contact_name": profile_row.get("emergency_contact_name"),
		"emergency_contact_phone": profile_row.get("emergency_contact_phone"),
	}
	completed = [key for key, value in checks.items() if _clean(value)]
	return {
		"percent": round((len(completed) / len(checks)) * 100),
		"completed": len(completed),
		"total": len(checks),
		"missing": [key for key in checks if key not in completed],
	}


@frappe.whitelist()
def get_my_profile() -> dict:
	user = _require_login()
	user_doc = frappe.get_doc("User", user)
	user_doc.check_permission("read")
	row = dict(frappe.db.get_value("User", user, _user_fields(), as_dict=True) or {})
	profile = _profile_payload(user)
	employees = _employee_rows(user)
	instructors = _instructor_rows(employees)
	branch_access = get_branch_access_profile(user=user)
	context = get_effective_institution_context(user=user)
	roles = [role for role in frappe.get_roles(user) if role not in {"All", "Guest"}]
	profile_doc = _get_profile_doc(user)
	can_write_profile = (
		bool(profile_doc.has_permission("write"))
		if profile_doc
		else bool(frappe.has_permission(PROFILE_DOCTYPE, "create"))
	)
	return {
		"profile": row,
		"education_profile": profile,
		"employees": employees,
		"instructors": instructors,
		"roles": sorted(roles),
		"branch_access": branch_access,
		"active_context": context,
		"completeness": _profile_completeness(row, profile),
		"permissions": {
			"can_edit_user": bool(user_doc.has_permission("write")),
			"can_edit_profile": can_write_profile,
			"email_is_managed": True,
		},
	}


@frappe.whitelist(methods=["POST"])
def save_my_profile(profile: str | dict) -> dict:
	user = _require_login()
	data = _parse_payload(profile)
	user_data = _parse_payload(data.get("user"))
	education_data = _parse_payload(data.get("education_profile"))

	user_doc = frappe.get_doc("User", user)
	user_doc.check_permission("write")
	first_name = _clean(user_data.get("first_name"), limit=140)
	if not first_name:
		frappe.throw(_("First Name is required."), frappe.ValidationError)

	user_updates = {
		"first_name": first_name,
		"middle_name": _clean(user_data.get("middle_name"), limit=140),
		"last_name": _clean(user_data.get("last_name"), limit=140),
		"phone": _clean(user_data.get("phone"), limit=40),
		"mobile_no": _clean(user_data.get("mobile_no"), limit=40),
		"location": _clean(user_data.get("location"), limit=140),
		"bio": _clean(user_data.get("bio"), limit=1000),
	}
	for fieldname, value in user_updates.items():
		if user_doc.meta.has_field(fieldname):
			user_doc.set(fieldname, value or None)

	profile_doc = _get_profile_doc(user)
	if profile_doc:
		profile_doc.check_permission("write")
	else:
		if not frappe.has_permission(PROFILE_DOCTYPE, "create"):
			frappe.throw(_("You cannot create an EduEdge Profile."), frappe.PermissionError)
		profile_doc = frappe.new_doc(PROFILE_DOCTYPE)
		profile_doc.user = user

	for fieldname in PROFILE_EDITABLE_FIELDS:
		if not profile_doc.meta.has_field(fieldname):
			continue
		limit = 240 if fieldname.startswith("address_line") else 140
		if fieldname in {"whatsapp_number", "postal_code", "emergency_contact_phone"}:
			limit = 40
		value = _clean(education_data.get(fieldname), limit=limit)
		if fieldname == "country":
			value = _validate_country(value)
		profile_doc.set(fieldname, value or None)

	user_doc.save()
	profile_doc.save()
	frappe.clear_cache(user=user)
	return get_my_profile()


def _file_doc_for_image(
	file_url: str,
	*,
	target_doctype: str,
	target_name: str,
	require_public: bool,
) -> frappe._dict:
	file_url = _clean(file_url, limit=500)
	file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if not file_name:
		frappe.throw(_("Uploaded image could not be found."), frappe.DoesNotExistError)
	file_doc = frappe.db.get_value(
		"File",
		file_name,
		[
			"name",
			"file_name",
			"file_url",
			"file_type",
			"file_size",
			"is_private",
			"owner",
			"attached_to_doctype",
			"attached_to_name",
		],
		as_dict=True,
	)
	extension = os.path.splitext((file_doc.file_name or file_doc.file_url or "").lower())[1]
	if extension not in ALLOWED_IMAGE_EXTENSIONS:
		frappe.throw(_("Only JPG, PNG, and WebP images are allowed."), frappe.ValidationError)
	if cint(file_doc.file_size or 0) > MAX_PROFILE_IMAGE_BYTES:
		frappe.throw(_("Profile images and Institution logos must not exceed 2 MB."), frappe.ValidationError)
	if require_public and cint(file_doc.is_private):
		frappe.throw(_("Institution logos must be uploaded as public images."), frappe.ValidationError)
	attached_to_target = (
		file_doc.attached_to_doctype == target_doctype
		and file_doc.attached_to_name == target_name
	)
	if file_doc.owner != frappe.session.user and not attached_to_target:
		frappe.throw(_("You cannot use another user's uploaded file."), frappe.PermissionError)
	return file_doc


@frappe.whitelist(methods=["POST"])
def set_my_profile_photo(file_url: str | None = None) -> dict:
	user = _require_login()
	doc = frappe.get_doc("User", user)
	doc.check_permission("write")
	if file_url:
		file_doc = _file_doc_for_image(
			file_url,
			target_doctype="User",
			target_name=user,
			require_public=False,
		)
		doc.user_image = file_doc.file_url
	else:
		doc.user_image = None
	doc.save()
	frappe.clear_cache(user=user)
	return get_my_profile()


def _allowed_institution_names() -> set[str]:
	return {row.get("name") for row in get_allowed_institutions() if row.get("name")}


def _resolve_institution(institution: str | None = None) -> str:
	_require_login()
	name = _clean(institution, limit=140)
	if not name:
		name = get_effective_institution_context().get("institution") or ""
	if not name:
		frappe.throw(_("Select an Institution first."), frappe.ValidationError)
	if name not in _allowed_institution_names():
		frappe.throw(_("You do not have access to this Institution."), frappe.PermissionError)
	return name


def _address_payload(name: str | None) -> dict:
	if not name or not frappe.db.exists("Address", name):
		return {}
	return dict(
		frappe.db.get_value(
			"Address",
			name,
			[
				"name",
				"address_title",
				"address_type",
				"address_line1",
				"address_line2",
				"city",
				"county",
				"state",
				"country",
				"pincode",
				"phone",
				"email_id",
			],
			as_dict=True,
		)
		or {}
	)


@frappe.whitelist()
def get_institution_profile(institution: str | None = None) -> dict:
	name = _resolve_institution(institution)
	doc = frappe.get_doc("EduEdge Institution", name)
	doc.check_permission("read")
	branding = get_institution_branding(name)
	return {
		"institution": {
			fieldname: doc.get(fieldname)
			for fieldname in (
				"name",
				"institution_name",
				"institution_code",
				"official_name",
				"short_name",
				"company",
				"institution_type",
				"logo",
				"motto",
				"address",
				"phone",
				"whatsapp_number",
				"email",
				"website",
				"report_card_letter_head",
				"report_footer",
				"registration_number",
				"regulatory_authority",
				"accreditation_status",
				"enabled",
			)
			if fieldname == "name" or doc.meta.has_field(fieldname)
		},
		"address": _address_payload(doc.address),
		"branding": branding,
		"allowed_institutions": get_allowed_institutions(),
		"active_context": get_effective_institution_context(institution=name),
		"permissions": {
			"can_write": bool(doc.has_permission("write")),
			"can_manage_address": bool(
				frappe.has_permission("Address", "write")
				or frappe.has_permission("Address", "create")
			),
		},
	}


@frappe.whitelist()
def get_active_institution_identity() -> dict:
	_require_login()
	context = get_effective_institution_context()
	institution = context.get("institution") or ""
	if institution:
		_resolve_institution(institution)
	return get_active_communication_identity(
		institution=institution or None,
		branch=context.get("branch") or None,
	)


@frappe.whitelist(methods=["POST"])
def save_institution_profile(institution: str, profile: str | dict) -> dict:
	name = _resolve_institution(institution)
	data = _parse_payload(profile)
	doc = frappe.get_doc("EduEdge Institution", name)
	doc.check_permission("write")
	for fieldname in INSTITUTION_EDITABLE_FIELDS:
		if not doc.meta.has_field(fieldname):
			continue
		limit = 1000 if fieldname == "report_footer" else 240
		value = _clean(data.get(fieldname), limit=limit)
		if fieldname == "email" and value and not validate_email_address(value):
			frappe.throw(_("Enter a valid institution email address."), frappe.ValidationError)
		if fieldname == "report_card_letter_head" and value:
			letter_head = frappe.get_doc("Letter Head", value)
			letter_head.check_permission("read")
		doc.set(fieldname, value or None)
	doc.save()
	frappe.clear_cache(doctype="EduEdge Institution")
	return get_institution_profile(name)


def _address_is_exclusive_to_institution(address_name: str, institution: str) -> bool:
	if frappe.db.count(
		"EduEdge Institution",
		{"address": address_name, "name": ["!=", institution]},
	):
		return False
	if frappe.db.count("EduEdge School Branch", {"address": address_name}):
		return False
	if not frappe.db.exists("DocType", "Dynamic Link"):
		return True
	links = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Address", "parent": address_name},
		fields=["link_doctype", "link_name"],
		limit_page_length=0,
	)
	return all(
		row.link_doctype == "EduEdge Institution" and row.link_name == institution
		for row in links
	)


@frappe.whitelist(methods=["POST"])
def save_institution_address(institution: str, address: str | dict) -> dict:
	name = _resolve_institution(institution)
	data = _parse_payload(address)
	institution_doc = frappe.get_doc("EduEdge Institution", name)
	institution_doc.check_permission("write")

	address_line1 = _clean(data.get("address_line1"), limit=240)
	if not address_line1:
		frappe.throw(_("Address Line 1 is required."), frappe.ValidationError)
	country = _validate_country(data.get("country"), required=True)
	email_id = _clean(data.get("email_id"), limit=140)
	if email_id and not validate_email_address(email_id):
		frappe.throw(_("Enter a valid Address email."), frappe.ValidationError)
	values = {
		"address_title": _clean(data.get("address_title"), limit=140)
		or institution_doc.short_name
		or institution_doc.institution_name,
		"address_type": _clean(data.get("address_type"), limit=40) or "Office",
		"address_line1": address_line1,
		"address_line2": _clean(data.get("address_line2"), limit=240),
		"city": _clean(data.get("city"), limit=140),
		"county": _clean(data.get("county"), limit=140),
		"state": _clean(data.get("state"), limit=140),
		"country": country,
		"pincode": _clean(data.get("pincode"), limit=40),
		"phone": _clean(data.get("phone"), limit=40),
		"email_id": email_id,
	}

	if institution_doc.address:
		address_doc = frappe.get_doc("Address", institution_doc.address)
		address_doc.check_permission("write")
		if not _address_is_exclusive_to_institution(address_doc.name, name):
			frappe.throw(
				_(
					"The linked Address is shared with another record. Create a separate Institution Address before editing it here."
				),
				frappe.ValidationError,
			)
	else:
		if not frappe.has_permission("Address", "create"):
			frappe.throw(_("You cannot create an Institution Address."), frappe.PermissionError)
		address_doc = frappe.new_doc("Address")

	if not any(
		row.link_doctype == "EduEdge Institution" and row.link_name == name
		for row in (address_doc.get("links") or [])
	):
		address_doc.append("links", {"link_doctype": "EduEdge Institution", "link_name": name})
	for fieldname, value in values.items():
		address_doc.set(fieldname, value or None)
	address_doc.save()
	if institution_doc.address != address_doc.name:
		institution_doc.address = address_doc.name
		institution_doc.save()
	frappe.clear_cache(doctype="EduEdge Institution")
	return get_institution_profile(name)


@frappe.whitelist(methods=["POST"])
def set_institution_logo(institution: str, file_url: str | None = None) -> dict:
	name = _resolve_institution(institution)
	doc = frappe.get_doc("EduEdge Institution", name)
	doc.check_permission("write")
	if file_url:
		file_doc = _file_doc_for_image(
			file_url,
			target_doctype="EduEdge Institution",
			target_name=name,
			require_public=True,
		)
		doc.logo = file_doc.file_url
	else:
		doc.logo = None
	doc.save()
	frappe.clear_cache(doctype="EduEdge Institution")
	return get_institution_profile(name)


@frappe.whitelist()
def search_letter_heads(txt: str | None = None) -> list[dict]:
	_require_login()
	if not frappe.has_permission("Letter Head", "read"):
		return []
	txt = _clean(txt, limit=100)
	filters = {"disabled": 0} if frappe.get_meta("Letter Head").has_field("disabled") else {}
	rows = frappe.get_list(
		"Letter Head",
		filters=filters,
		or_filters={"name": ["like", f"%{txt}%"]} if txt else None,
		fields=["name"],
		order_by="name asc",
		page_length=30,
	)
	return [{"value": row.name, "label": row.name} for row in rows]


@frappe.whitelist()
def search_countries(txt: str | None = None) -> list[dict]:
	_require_login()
	txt = _clean(txt, limit=100)
	or_filters = None
	if txt:
		like = f"%{txt}%"
		or_filters = {"name": ["like", like], "country_name": ["like", like]}
	rows = frappe.get_list(
		"Country",
		or_filters=or_filters,
		fields=["name", "country_name"],
		order_by="country_name asc, name asc",
		page_length=30,
	)
	return [{"value": row.name, "label": row.country_name or row.name} for row in rows]
