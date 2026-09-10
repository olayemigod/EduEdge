from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.institution_types import SEED_UPDATE_FLAG

TOPIC_COURSE_FIELD = "eduedge_course"
TOPIC_SCOPE_FIELD = "eduedge_topic_scope"
TOPIC_OFFERING_FIELD = "eduedge_program_offering"
TOPIC_GROUP_FIELD = "eduedge_student_group"
TOPIC_SCOPE_INSTITUTION = "Institution-wide"
TOPIC_SCOPE_CLASS = "Class / Programme Offering"
TOPIC_SCOPE_CLASS_ARM = "Class Arm"
TOPIC_SCOPES = (TOPIC_SCOPE_INSTITUTION, TOPIC_SCOPE_CLASS, TOPIC_SCOPE_CLASS_ARM)

CURRICULUM_TERMINOLOGY = {
	"PRIMARY": {
		"course": ("Subject", "Subjects"),
		"topic": ("Topic", "Topics"),
	},
	"SECONDARY": {
		"course": ("Subject", "Subjects"),
		"topic": ("Topic", "Topics"),
	},
	"TERTIARY": {
		"course": ("Course", "Courses"),
		"topic": ("Topic", "Topics"),
	},
	"TRAINING_CENTRE": {
		"course": ("Training Course", "Training Courses"),
		"topic": ("Training Topic", "Training Topics"),
	},
}

TOPIC_CONTEXT_FIELDS = {
	"Topic": [
		{
			"fieldname": INSTITUTION_FIELD,
			"fieldtype": "Link",
			"label": "Institution",
			"options": "EduEdge Institution",
			"read_only": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
			"insert_after": "topic_name",
			"description": "Derived from the owning Course / Subject.",
		},
		{
			"fieldname": TOPIC_COURSE_FIELD,
			"fieldtype": "Link",
			"label": "Owning Course / Subject",
			"options": "Course",
			"in_list_view": 1,
			"in_standard_filter": 1,
			"insert_after": INSTITUTION_FIELD,
			"description": "Institution-wide Subject master that owns this Topic.",
		},
		{
			"fieldname": TOPIC_SCOPE_FIELD,
			"fieldtype": "Select",
			"label": "Teaching Scope",
			"options": "\nInstitution-wide\nClass / Programme Offering\nClass Arm",
			"default": TOPIC_SCOPE_INSTITUTION,
			"in_list_view": 1,
			"in_standard_filter": 1,
			"insert_after": TOPIC_COURSE_FIELD,
			"description": "Controls whether this Topic is general to the Institution, a Class, or one Class Arm.",
		},
		{
			"fieldname": TOPIC_OFFERING_FIELD,
			"fieldtype": "Link",
			"label": "Class / Programme Offering",
			"options": "EduEdge Program Offering",
			"in_list_view": 1,
			"in_standard_filter": 1,
			"insert_after": TOPIC_SCOPE_FIELD,
			"depends_on": f"eval:doc.{TOPIC_SCOPE_FIELD}!='{TOPIC_SCOPE_INSTITUTION}'",
			"mandatory_depends_on": f"eval:doc.{TOPIC_SCOPE_FIELD}!='{TOPIC_SCOPE_INSTITUTION}'",
		},
		{
			"fieldname": TOPIC_GROUP_FIELD,
			"fieldtype": "Link",
			"label": "Class Arm / Student Group",
			"options": "Student Group",
			"in_list_view": 1,
			"in_standard_filter": 1,
			"insert_after": TOPIC_OFFERING_FIELD,
			"depends_on": f"eval:doc.{TOPIC_SCOPE_FIELD}=='{TOPIC_SCOPE_CLASS_ARM}'",
			"mandatory_depends_on": f"eval:doc.{TOPIC_SCOPE_FIELD}=='{TOPIC_SCOPE_CLASS_ARM}'",
		},
	],
}


def ensure_curriculum_management_foundation() -> None:
	available = {
		doctype: fields
		for doctype, fields in TOPIC_CONTEXT_FIELDS.items()
		if frappe.db.exists("DocType", doctype)
	}
	if available:
		create_custom_fields(available, update=True)
	ensure_curriculum_terminology()
	backfill_topic_context()


def ensure_curriculum_terminology() -> None:
	if not frappe.db.exists("DocType", "EduEdge Institution Type"):
		return
	setattr(frappe.flags, SEED_UPDATE_FLAG, True)
	try:
		for institution_type, terms in CURRICULUM_TERMINOLOGY.items():
			if not frappe.db.exists("EduEdge Institution Type", institution_type):
				continue
			doc = frappe.get_doc("EduEdge Institution Type", institution_type)
			rows = {row.canonical_key: row for row in doc.get("terms") or []}
			changed = False
			for key, (singular, plural) in terms.items():
				row = rows.get(key)
				if not row:
					row = doc.append("terms", {"canonical_key": key})
					rows[key] = row
					changed = True
				for fieldname, value in {
					"singular_label": singular,
					"plural_label": plural,
					"short_label": singular,
					"show_feature": 1,
				}.items():
					if row.get(fieldname) != value:
						row.set(fieldname, value)
						changed = True
				if not row.sequence:
					row.sequence = (len(rows) + 1) * 10
					changed = True
			if changed:
				doc.save(ignore_permissions=True)
	finally:
		setattr(frappe.flags, SEED_UPDATE_FLAG, False)
	frappe.clear_cache(doctype="EduEdge Institution Type")


def backfill_topic_context() -> None:
	if not (
		frappe.db.exists("DocType", "Topic")
		and frappe.get_meta("Topic").has_field(TOPIC_COURSE_FIELD)
		and frappe.get_meta("Topic").has_field(INSTITUTION_FIELD)
	):
		return
	rows = frappe.db.sql(
		"""
		select ct.topic, min(ct.parent) as course, count(distinct ct.parent) as course_count
		from `tabCourse Topic` ct
		where ifnull(ct.topic, '') != ''
		group by ct.topic
		""",
		as_dict=True,
	)
	for row in rows:
		if row.course_count != 1:
			continue
		values = {}
		if not frappe.db.get_value("Topic", row.topic, TOPIC_COURSE_FIELD):
			values[TOPIC_COURSE_FIELD] = row.course
		institution = frappe.db.get_value("Course", row.course, INSTITUTION_FIELD)
		if institution and not frappe.db.get_value("Topic", row.topic, INSTITUTION_FIELD):
			values[INSTITUTION_FIELD] = institution
		if frappe.get_meta("Topic").has_field(TOPIC_SCOPE_FIELD) and not frappe.db.get_value("Topic", row.topic, TOPIC_SCOPE_FIELD):
			values[TOPIC_SCOPE_FIELD] = TOPIC_SCOPE_INSTITUTION
		if values:
			frappe.db.set_value("Topic", row.topic, values, update_modified=False)
