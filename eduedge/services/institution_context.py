from __future__ import annotations

from typing import Any

import frappe

from eduedge.education.institution_types import (
	COMPANY_INSTITUTION_TYPE_FIELD,
	DEFAULT_INSTITUTION_TYPE,
	INSTITUTION_TYPE_SEEDS,
	get_seed_definition,
	normalize_institution_type_code,
)
from eduedge.services.branch_context import get_current_school_branch

DOCUMENT_BRANCH_FIELDS = ("eduedge_school_branch", "school_branch")
DOCUMENT_INSTITUTION_FIELDS = ("eduedge_institution", "institution")


def get_effective_institution_context(
	*,
	company: str | None = None,
	institution: str | None = None,
	branch: str | None = None,
	document: Any | None = None,
	user: str | None = None,
) -> dict:
	"""Resolve Branch → Institution → Company terminology without renaming Frappe metadata."""
	document_branch = _get_document_value(document, DOCUMENT_BRANCH_FIELDS)
	document_institution = _get_document_value(document, DOCUMENT_INSTITUTION_FIELDS)
	resolved_branch = branch or document_branch
	branch_source = "document_branch" if document_branch else "branch"
	branch_row = _get_branch_row(resolved_branch) if resolved_branch else None

	if not branch_row and not resolved_branch:
		current_branch = get_current_school_branch(user=user)
		if current_branch and current_branch.get("name"):
			branch_row = _get_branch_row(current_branch.get("name")) or frappe._dict(current_branch)
			branch_source = "active_branch"
		elif current_branch and current_branch.get("company"):
			company = company or current_branch.get("company")

	resolved_institution = (
		(branch_row or {}).get("institution")
		or institution
		or document_institution
	)
	institution_source = "branch_institution" if (branch_row or {}).get("institution") else (
		"document_institution" if document_institution else "institution"
	)
	institution_row = _get_institution_row(resolved_institution) if resolved_institution else None
	resolved_company = (
		(institution_row or {}).get("company")
		or (branch_row or {}).get("company")
		or company
		or _get_default_company(user=user)
	)

	institution_type = normalize_institution_type_code((institution_row or {}).get("institution_type"))
	source = institution_source if institution_type else ""
	if institution_type and (branch_row or {}).get("institution"):
		source = f"{branch_source}_institution"

	# Transitional compatibility for a branch saved before the Institution-layer migration.
	if not institution_type:
		institution_type = normalize_institution_type_code((branch_row or {}).get("institution_type"))
		if institution_type:
			source = f"{branch_source}_legacy_type"

	company_type = _get_company_institution_type(resolved_company)
	if not institution_type and company_type:
		institution_type = company_type
		source = "company"
	if not institution_type:
		institution_type = DEFAULT_INSTITUTION_TYPE
		source = "system_fallback"

	registry = _get_registry_row(institution_type)
	if not registry or not registry.get("enabled"):
		institution_type = DEFAULT_INSTITUTION_TYPE
		registry = _get_registry_row(institution_type)
		source = "system_fallback"

	definition = get_seed_definition(institution_type)
	return {
		"institution_type": institution_type,
		"institution_type_name": (registry or {}).get("institution_type_name") or definition["name"],
		"source": source,
		"company": resolved_company or "",
		"institution": (institution_row or {}).get("name") or "",
		"institution_name": (institution_row or {}).get("institution_name") or "",
		"branch": (branch_row or {}).get("name") or "",
		"branch_name": (branch_row or {}).get("branch_name") or "",
		"terms": get_terminology_map(institution_type),
		"uses_secondary_fallback": int(source == "system_fallback"),
	}


def get_terminology_map(institution_type: str | None) -> dict[str, dict]:
	code = normalize_institution_type_code(institution_type) or DEFAULT_INSTITUTION_TYPE
	if frappe.db.exists("DocType", "EduEdge Institution Type Term") and frappe.db.exists(
		"EduEdge Institution Type", code
	):
		rows = frappe.get_all(
			"EduEdge Institution Type Term",
			filters={
				"parent": code,
				"parenttype": "EduEdge Institution Type",
				"parentfield": "terms",
			},
			fields=[
				"canonical_key",
				"singular_label",
				"plural_label",
				"short_label",
				"help_text",
				"show_feature",
				"sequence",
			],
			order_by="sequence asc, idx asc",
		)
		if rows:
			return _augment_academic_hierarchy_terms(
				code,
				{
					row.canonical_key: {
						"singular": row.singular_label,
						"plural": row.plural_label,
						"short": row.short_label or row.singular_label,
						"help_text": row.help_text or "",
						"show_feature": int(row.show_feature or 0),
						"sequence": int(row.sequence or 0),
					}
					for row in rows
				},
			)
	return _augment_academic_hierarchy_terms(code, _seed_terminology_map(code))


def get_term(
	canonical_key: str,
	*,
	plural: bool = False,
	company: str | None = None,
	institution: str | None = None,
	branch: str | None = None,
	document: Any | None = None,
	fallback: str | None = None,
) -> str:
	context = get_effective_institution_context(
		company=company,
		institution=institution,
		branch=branch,
		document=document,
	)
	term = context["terms"].get(canonical_key) or {}
	return term.get("plural" if plural else "singular") or fallback or canonical_key.replace("_", " ").title()


def get_institution_type_options() -> list[dict]:
	if frappe.db.exists("DocType", "EduEdge Institution Type"):
		rows = frappe.get_all(
			"EduEdge Institution Type",
			filters={"enabled": 1},
			fields=["name", "institution_type_name", "description", "sequence"],
			order_by="sequence asc, institution_type_name asc",
		)
		if rows:
			return [
				{
					"value": row.name,
					"label": row.institution_type_name or row.name,
					"description": row.description or "",
					"terms": get_terminology_map(row.name),
				}
				for row in rows
			]
	return [
		{
			"value": code,
			"label": definition["name"],
			"description": definition["description"],
			"terms": _augment_academic_hierarchy_terms(code, _seed_terminology_map(code)),
		}
		for code, definition in sorted(INSTITUTION_TYPE_SEEDS.items(), key=lambda item: item[1]["sequence"])
	]


def _get_document_value(document: Any | None, fields: tuple[str, ...]) -> str | None:
	if not document:
		return None
	for fieldname in fields:
		value = document.get(fieldname) if hasattr(document, "get") else getattr(document, fieldname, None)
		if value:
			return value
	return None


def _get_branch_row(branch: str | None) -> frappe._dict | None:
	if not branch or not frappe.db.exists("EduEdge School Branch", branch):
		return None
	fields = ["name", "branch_name", "company"]
	meta = frappe.get_meta("EduEdge School Branch")
	for fieldname in ("institution", "institution_type"):
		if meta.has_field(fieldname):
			fields.append(fieldname)
	return frappe.db.get_value("EduEdge School Branch", branch, fields, as_dict=True)


def _get_institution_row(institution: str | None) -> frappe._dict | None:
	if not institution or not frappe.db.exists("EduEdge Institution", institution):
		return None
	return frappe.db.get_value(
		"EduEdge Institution",
		institution,
		["name", "institution_name", "company", "institution_type", "enabled"],
		as_dict=True,
	)


def _get_default_company(*, user: str | None = None) -> str | None:
	resolved_user = user or frappe.session.user
	company = frappe.defaults.get_user_default("company", user=resolved_user)
	if company:
		return company
	if frappe.db.exists("DocType", "EduEdge Settings"):
		return frappe.db.get_single_value("EduEdge Settings", "default_company")
	return None


def _get_company_institution_type(company: str | None) -> str:
	if not company or not frappe.db.exists("Company", company):
		return ""
	if not frappe.get_meta("Company").has_field(COMPANY_INSTITUTION_TYPE_FIELD):
		return ""
	return normalize_institution_type_code(
		frappe.db.get_value("Company", company, COMPANY_INSTITUTION_TYPE_FIELD)
	)


def _get_registry_row(code: str) -> frappe._dict | None:
	if not frappe.db.exists("DocType", "EduEdge Institution Type"):
		return None
	return frappe.db.get_value(
		"EduEdge Institution Type",
		code,
		["name", "institution_type_name", "description", "enabled", "sequence"],
		as_dict=True,
	)


def _seed_terminology_map(code: str) -> dict[str, dict]:
	definition = get_seed_definition(code)
	return {
		key: {
			"singular": singular,
			"plural": plural,
			"short": singular,
			"help_text": "",
			"show_feature": 1,
			"sequence": sequence * 10,
		}
		for sequence, (key, (singular, plural)) in enumerate(definition["terms"].items(), start=1)
	}


def _term_row(singular: str, plural: str, *, sequence: int) -> dict:
	return {
		"singular": singular,
		"plural": plural,
		"short": singular,
		"help_text": "",
		"show_feature": 1,
		"sequence": sequence,
	}


def _augment_academic_hierarchy_terms(code: str, terms: dict[str, dict]) -> dict[str, dict]:
	"""Expose distinct labels for Section → Level/Class → Student Group/Class Arm.

	The database DocTypes retain their stable technical identities. These aliases keep
	all EdgeSuite pages aligned and prevent the ERPNext Program record from being
	mislabelled as the same School Section represented by EduEdge Academic Section.
	"""
	resolved = {key: dict(value) for key, value in (terms or {}).items()}
	if code in {"PRIMARY", "SECONDARY"}:
		resolved["academic_section"] = _term_row("School Section", "School Sections", sequence=35)
		resolved["academic_level"] = _term_row("Class", "Classes", sequence=75)
		resolved["programme"] = _term_row("Programme", "Programmes", sequence=30)
	elif code == "TERTIARY":
		resolved["academic_section"] = _term_row("Faculty / School", "Faculties / Schools", sequence=35)
		resolved["academic_level"] = _term_row("Level", "Levels", sequence=75)
	elif code == "TRAINING_CENTRE":
		resolved["academic_section"] = _term_row("Training Category", "Training Categories", sequence=35)
		resolved["academic_level"] = _term_row("Training Level", "Training Levels", sequence=75)
	else:
		resolved["academic_section"] = _term_row("Academic Section", "Academic Sections", sequence=35)
		resolved["academic_level"] = dict(
			resolved.get("class_level") or _term_row("Academic Level", "Academic Levels", sequence=75)
		)
	resolved.setdefault("class_level", dict(resolved["academic_level"]))
	return resolved
