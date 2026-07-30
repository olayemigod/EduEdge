from __future__ import annotations

import frappe

from eduedge.education.institution_types import SEED_UPDATE_FLAG

PROGRESSION_TERMS = {
	"PRIMARY": {
		"academic_level": ("Class", "Classes", 0),
		"student_group": ("Class Arm", "Class Arms", 1),
	},
	"SECONDARY": {
		"academic_level": ("Class", "Classes", 0),
		"student_group": ("Class Arm", "Class Arms", 1),
	},
	"TERTIARY": {
		"academic_level": ("Academic Level", "Academic Levels", 1),
		"student_group": ("Lecture Group", "Lecture Groups", 1),
	},
	"TRAINING_CENTRE": {
		"academic_level": ("Training Stage", "Training Stages", 1),
		"student_group": ("Training Group", "Training Groups", 1),
	},
}


def ensure_progression_terminology() -> None:
	if not frappe.db.exists("DocType", "EduEdge Institution Type"):
		return
	setattr(frappe.flags, SEED_UPDATE_FLAG, True)
	try:
		for code, terms in PROGRESSION_TERMS.items():
			if not frappe.db.exists("EduEdge Institution Type", code):
				continue
			doc = frappe.get_doc("EduEdge Institution Type", code)
			rows = {row.canonical_key: row for row in doc.get("terms") or []}
			changed = False
			for key, (singular, plural, show_feature) in terms.items():
				row = rows.get(key)
				if not row:
					row = doc.append("terms", {"canonical_key": key})
					changed = True
				for fieldname, value in {
					"singular_label": singular,
					"plural_label": plural,
					"short_label": singular,
					"show_feature": show_feature,
				}.items():
					if row.get(fieldname) != value:
						row.set(fieldname, value)
						changed = True
			if changed:
				doc.save(ignore_permissions=True)
	finally:
		setattr(frappe.flags, SEED_UPDATE_FLAG, False)
	frappe.clear_cache(doctype="EduEdge Institution Type")
