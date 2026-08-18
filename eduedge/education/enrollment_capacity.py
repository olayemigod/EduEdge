from __future__ import annotations

import frappe
from frappe import _

from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.services.enrollment_lifecycle import count_capacity_consuming_enrollments


def before_submit_program_enrollment(doc, method=None) -> None:
	if not doc.meta.has_field(OFFERING_FIELD) or not doc.get(OFFERING_FIELD):
		return
	# Lock the Offering row for the remainder of the transaction so simultaneous
	# submissions cannot both pass the same duplicate/capacity count.
	frappe.db.sql(
		"select name from `tabEduEdge Program Offering` where name = %s for update",
		(doc.get(OFFERING_FIELD),),
	)
	duplicate = frappe.db.exists(
		"Program Enrollment",
		{
			"student": doc.student,
			OFFERING_FIELD: doc.get(OFFERING_FIELD),
			"docstatus": 1,
			"name": ["!=", doc.name],
		},
	)
	if duplicate:
		frappe.throw(
			_("Student {0} already has a submitted enrollment for this Programme Offering.").format(doc.student),
			frappe.DuplicateEntryError,
		)
	capacity = frappe.db.get_value("EduEdge Program Offering", doc.get(OFFERING_FIELD), "capacity") or 0
	if int(capacity) <= 0:
		return
	enrolled = count_capacity_consuming_enrollments(
		doc.get(OFFERING_FIELD),
		exclude_enrollment=doc.name,
	)
	if enrolled >= int(capacity):
		frappe.throw(
			_("This Programme Offering has reached its capacity of {0}.").format(capacity),
			frappe.ValidationError,
		)
