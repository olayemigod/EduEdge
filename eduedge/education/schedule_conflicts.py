from __future__ import annotations

import frappe
from frappe import _


COURSE_SCHEDULE_FIELDS = (
	("student_group", "Class Arm / Student Group"),
	("instructor", "Instructor"),
	("room", "Room"),
)


def _find_overlap(
	*,
	doctype: str,
	fieldname: str,
	value: str | None,
	schedule_date,
	from_time,
	to_time,
	exclude_name: str | None = None,
):
	if not value or not schedule_date or from_time is None or to_time is None:
		return None
	if doctype not in {"Course Schedule", "Assessment Plan"}:
		raise ValueError(f"Unsupported schedule doctype: {doctype}")
	if fieldname not in {"student_group", "instructor", "room", "supervisor"}:
		raise ValueError(f"Unsupported schedule conflict field: {fieldname}")

	rows = frappe.db.sql(
		f"""
		select name, from_time, to_time
		from `tab{doctype}`
		where `{fieldname}` = %(value)s
		  and schedule_date = %(schedule_date)s
		  and name != %(exclude_name)s
		  and docstatus != 2
		  and from_time < %(to_time)s
		  and to_time > %(from_time)s
		order by from_time asc, to_time asc, name asc
		limit 1
		""",
		{
			"value": value,
			"schedule_date": schedule_date,
			"from_time": from_time,
			"to_time": to_time,
			"exclude_name": exclude_name or "",
		},
		as_dict=True,
	)
	return rows[0] if rows else None


def _throw_conflict(*, existing_doctype: str, existing, field_label: str, value: str) -> None:
	frappe.throw(
		_("Teaching Schedule conflicts with {0} {1} for {2} {3} ({4}–{5}).").format(
			existing_doctype,
			existing.name,
			field_label,
			value,
			existing.from_time,
			existing.to_time,
		),
		frappe.ValidationError,
	)


def validate_course_schedule_conflicts(doc) -> None:
	"""Close Frappe Education overlap gaps without replacing its native model.

	Frappe Education's current overlap SQL misses intervals that start at exactly
	the same time but end at different times. The standard interval rule is:
	existing_start < new_end AND existing_end > new_start. Back-to-back periods
	remain valid because equality at the boundary is not an overlap.
	"""
	for fieldname, field_label in COURSE_SCHEDULE_FIELDS:
		value = doc.get(fieldname)
		existing = _find_overlap(
			doctype="Course Schedule",
			fieldname=fieldname,
			value=value,
			schedule_date=doc.schedule_date,
			from_time=doc.from_time,
			to_time=doc.to_time,
			exclude_name=doc.name,
		)
		if existing:
			_throw_conflict(
				existing_doctype=_("Teaching Schedule"),
				existing=existing,
				field_label=_(field_label),
				value=value,
			)

	assessment_checks = (
		("student_group", doc.get("student_group"), _("Class Arm / Student Group")),
		("room", doc.get("room"), _("Room")),
		("supervisor", doc.get("instructor"), _("Assessment Supervisor")),
	)
	for fieldname, value, field_label in assessment_checks:
		existing = _find_overlap(
			doctype="Assessment Plan",
			fieldname=fieldname,
			value=value,
			schedule_date=doc.schedule_date,
			from_time=doc.from_time,
			to_time=doc.to_time,
		)
		if existing:
			_throw_conflict(
				existing_doctype=_("Assessment Plan"),
				existing=existing,
				field_label=field_label,
				value=value,
			)
