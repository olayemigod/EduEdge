from __future__ import annotations

import hashlib
import re
from copy import deepcopy

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

COMPANY_INSTITUTION_TYPE_FIELD = "eduedge_institution_type"
DEFAULT_INSTITUTION_TYPE = "SECONDARY"
SEED_UPDATE_FLAG = "eduedge_institution_type_seed_update"

TERM_KEYS = (
	"academic_year",
	"academic_term",
	"programme",
	"programme_offering",
	"course",
	"student_batch",
	"student_group",
	"class_level",
	"class_session",
	"instructor",
	"room",
)

INSTITUTION_TYPE_SEEDS = {
	"PRIMARY": {
		"name": "Primary School",
		"description": "Primary education institution using sessions, terms, subjects, classes, class arms, lessons, teachers, and classrooms.",
		"sequence": 10,
		"terms": {
			"academic_year": ("Academic Session", "Academic Sessions"),
			"academic_term": ("Term", "Terms"),
			"programme": ("School Section", "School Sections"),
			"programme_offering": ("Class Intake", "Class Intakes"),
			"course": ("Subject", "Subjects"),
			"student_batch": ("Admission Set", "Admission Sets"),
			"student_group": ("Class Arm", "Class Arms"),
			"class_level": ("Class", "Classes"),
			"class_session": ("Lesson", "Lessons"),
			"instructor": ("Teacher", "Teachers"),
			"room": ("Classroom", "Classrooms"),
		},
	},
	"SECONDARY": {
		"name": "Secondary School",
		"description": "Secondary education institution using sessions, terms, subjects, classes, class arms, lessons, teachers, and classrooms.",
		"sequence": 20,
		"terms": {
			"academic_year": ("Academic Session", "Academic Sessions"),
			"academic_term": ("Term", "Terms"),
			"programme": ("School Section", "School Sections"),
			"programme_offering": ("Class Intake", "Class Intakes"),
			"course": ("Subject", "Subjects"),
			"student_batch": ("Admission Set", "Admission Sets"),
			"student_group": ("Class Arm", "Class Arms"),
			"class_level": ("Class", "Classes"),
			"class_session": ("Lesson", "Lessons"),
			"instructor": ("Teacher", "Teachers"),
			"room": ("Classroom", "Classrooms"),
		},
	},
	"TERTIARY": {
		"name": "Tertiary Institution",
		"description": "University, polytechnic, college, or similar higher institution using sessions, semesters, programmes, courses, levels, lectures, and lecturers.",
		"sequence": 30,
		"terms": {
			"academic_year": ("Academic Session", "Academic Sessions"),
			"academic_term": ("Semester", "Semesters"),
			"programme": ("Programme", "Programmes"),
			"programme_offering": ("Programme Intake", "Programme Intakes"),
			"course": ("Course", "Courses"),
			"student_batch": ("Entry Cohort", "Entry Cohorts"),
			"student_group": ("Lecture Group", "Lecture Groups"),
			"class_level": ("Level", "Levels"),
			"class_session": ("Lecture", "Lectures"),
			"instructor": ("Lecturer", "Lecturers"),
			"room": ("Lecture Hall", "Lecture Halls"),
		},
	},
	"TRAINING_CENTRE": {
		"name": "Training Centre",
		"description": "Professional, tutorial, vocational, or skills training institution using training years, sessions, programmes, intakes, modules, classes, and trainers.",
		"sequence": 40,
		"terms": {
			"academic_year": ("Training Year", "Training Years"),
			"academic_term": ("Training Session", "Training Sessions"),
			"programme": ("Programme", "Programmes"),
			"programme_offering": ("Intake", "Intakes"),
			"course": ("Module", "Modules"),
			"student_batch": ("Batch", "Batches"),
			"student_group": ("Class", "Classes"),
			"class_level": ("Training Level", "Training Levels"),
			"class_session": ("Class Session", "Class Sessions"),
			"instructor": ("Trainer", "Trainers"),
			"room": ("Training Room", "Training Rooms"),
		},
	},
}

COMPANY_CUSTOM_FIELDS = {
	"Company": [
		{
			"fieldname": COMPANY_INSTITUTION_TYPE_FIELD,
			"fieldtype": "Link",
			"label": "EduEdge Institution Type",
			"options": "EduEdge Institution Type",
			"insert_after": "company_name",
			"default": DEFAULT_INSTITUTION_TYPE,
			"in_standard_filter": 1,
			"description": "Optional fallback used only when no EduEdge Institution or School Branch context is available. Blank values resolve to Secondary School.",
		},
	],
}


def normalize_institution_type_code(value: str | None) -> str:
	return re.sub(r"[^A-Z0-9]+", "_", str(value or "").strip().upper()).strip("_")


def ensure_institution_type_foundation() -> None:
	"""Create the controlled registry, Company fallback, Institutions, and safe branch links."""
	if not frappe.db.exists("DocType", "EduEdge Institution Type"):
		return
	ensure_institution_types()
	ensure_company_institution_type_field()
	backfill_institutions_and_branches()


def ensure_institution_types() -> None:
	setattr(frappe.flags, SEED_UPDATE_FLAG, True)
	try:
		for code, definition in INSTITUTION_TYPE_SEEDS.items():
			desired_terms = _term_rows(definition["terms"])
			if frappe.db.exists("EduEdge Institution Type", code):
				doc = frappe.get_doc("EduEdge Institution Type", code)
				before = _registry_snapshot(doc)
				doc.institution_type_code = code
				doc.institution_type_name = definition["name"]
				doc.description = definition["description"]
				doc.enabled = 1
				doc.sequence = definition["sequence"]
				doc.is_system_managed = 1
				doc.set("terms", deepcopy(desired_terms))
				if before != _registry_snapshot(doc):
					doc.save(ignore_permissions=True)
			else:
				frappe.get_doc(
					{
						"doctype": "EduEdge Institution Type",
						"institution_type_code": code,
						"institution_type_name": definition["name"],
						"description": definition["description"],
						"enabled": 1,
						"sequence": definition["sequence"],
						"is_system_managed": 1,
						"terms": deepcopy(desired_terms),
					}
				).insert(ignore_permissions=True)
	finally:
		setattr(frappe.flags, SEED_UPDATE_FLAG, False)
	frappe.clear_cache(doctype="EduEdge Institution Type")


def ensure_company_institution_type_field() -> None:
	create_custom_fields(COMPANY_CUSTOM_FIELDS, update=True)


def backfill_institutions_and_branches() -> None:
	"""Create one reviewable Institution per Company/type group and link legacy branches.

	The migration deliberately groups only by existing Company and Institution Type. It
	does not infer institution identity from Branch names, addresses, or academic data.
	"""
	if not frappe.db.exists("DocType", "EduEdge Institution") or not frappe.db.exists(
		"DocType", "EduEdge School Branch"
	):
		return
	branch_meta = frappe.get_meta("EduEdge School Branch")
	company_meta = frappe.get_meta("Company")
	if not branch_meta.has_field("institution") or not branch_meta.has_field("institution_type"):
		return
	if not company_meta.has_field(COMPANY_INSTITUTION_TYPE_FIELD):
		return

	rows = frappe.get_all(
		"EduEdge School Branch",
		filters={"institution": ["is", "not set"]},
		fields=["name", "company", "institution_type"],
		order_by="company asc, name asc",
	)
	groups: dict[tuple[str, str], list[str]] = {}
	for row in rows:
		code = normalize_institution_type_code(row.institution_type)
		if not code:
			code = normalize_institution_type_code(
				frappe.db.get_value("Company", row.company, COMPANY_INSTITUTION_TYPE_FIELD)
			) or DEFAULT_INSTITUTION_TYPE
		groups.setdefault((row.company, code), []).append(row.name)

	company_group_counts: dict[str, int] = {}
	for company, _code in groups:
		company_group_counts[company] = company_group_counts.get(company, 0) + 1

	for (company, code), branches in groups.items():
		institution = _get_or_create_migrated_institution(
			company=company,
			institution_type=code,
			is_default=company_group_counts.get(company) == 1,
		)
		frappe.db.sql(
			"""
			update `tabEduEdge School Branch`
			set institution = %(institution)s, institution_type = %(institution_type)s
			where name in %(branches)s and coalesce(institution, '') = ''
			""",
			{"branches": tuple(branches), "institution": institution, "institution_type": code},
		)

	_sync_branch_institution_types()
	frappe.clear_cache(doctype="EduEdge Institution")
	frappe.clear_cache(doctype="EduEdge School Branch")


def _get_or_create_migrated_institution(*, company: str, institution_type: str, is_default: bool) -> str:
	reference = f"{company}::{institution_type}"
	existing = frappe.db.get_value("EduEdge Institution", {"migration_reference": reference}, "name")
	if existing:
		return existing
	definition = get_seed_definition(institution_type)
	code = _migration_institution_code(company, institution_type)
	if frappe.db.exists("EduEdge Institution", code):
		return code
	name = f"{company} — {definition['name']}"
	doc = frappe.get_doc(
		{
			"doctype": "EduEdge Institution",
			"institution_name": name,
			"official_name": name,
			"institution_code": code,
			"company": company,
			"institution_type": institution_type,
			"is_default": int(bool(is_default)),
			"enabled": 1,
			"generated_from_legacy": 1,
			"requires_review": 1,
			"migration_reference": reference,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _migration_institution_code(company: str, institution_type: str) -> str:
	slug = re.sub(r"[^A-Z0-9]+", "-", company.upper()).strip("-")[:36] or "COMPANY"
	digest = hashlib.sha1(f"{company}::{institution_type}".encode()).hexdigest()[:8].upper()
	return f"LEGACY-{slug}-{institution_type[:16]}-{digest}"[:80]


def _sync_branch_institution_types() -> None:
	frappe.db.sql(
		"""
		update `tabEduEdge School Branch` branch
		inner join `tabEduEdge Institution` institution on institution.name = branch.institution
		set branch.institution_type = institution.institution_type
		where branch.company = institution.company
			and coalesce(branch.institution_type, '') != institution.institution_type
		"""
	)


def get_seed_definition(code: str | None) -> dict:
	resolved = normalize_institution_type_code(code) or DEFAULT_INSTITUTION_TYPE
	return deepcopy(INSTITUTION_TYPE_SEEDS.get(resolved) or INSTITUTION_TYPE_SEEDS[DEFAULT_INSTITUTION_TYPE])


def _term_rows(terms: dict[str, tuple[str, str]]) -> list[dict]:
	rows = []
	for sequence, key in enumerate(TERM_KEYS, start=1):
		singular, plural = terms[key]
		rows.append(
			{
				"canonical_key": key,
				"singular_label": singular,
				"plural_label": plural,
				"short_label": singular,
				"help_text": "",
				"show_feature": 1,
				"sequence": sequence * 10,
			}
		)
	return rows


def _registry_snapshot(doc) -> dict:
	return {
		"institution_type_code": doc.get("institution_type_code"),
		"institution_type_name": doc.get("institution_type_name"),
		"description": doc.get("description"),
		"enabled": int(doc.get("enabled") or 0),
		"sequence": int(doc.get("sequence") or 0),
		"is_system_managed": int(doc.get("is_system_managed") or 0),
		"terms": [
			{
				"canonical_key": row.get("canonical_key"),
				"singular_label": row.get("singular_label"),
				"plural_label": row.get("plural_label"),
				"short_label": row.get("short_label"),
				"help_text": row.get("help_text") or "",
				"show_feature": int(row.get("show_feature") or 0),
				"sequence": int(row.get("sequence") or 0),
			}
			for row in doc.get("terms") or []
		],
	}


def before_validate_company(doc, method=None) -> None:
	"""Keep the optional Company fallback inside the EduEdge-controlled registry."""
	if not doc.meta.has_field(COMPANY_INSTITUTION_TYPE_FIELD):
		return
	value = normalize_institution_type_code(doc.get(COMPANY_INSTITUTION_TYPE_FIELD))
	if not value:
		doc.set(COMPANY_INSTITUTION_TYPE_FIELD, None)
		return
	if not frappe.db.exists("EduEdge Institution Type", {"name": value, "enabled": 1}):
		frappe.throw("Select an enabled EduEdge Institution Type for this Company.", frappe.ValidationError)
	doc.set(COMPANY_INSTITUTION_TYPE_FIELD, value)
