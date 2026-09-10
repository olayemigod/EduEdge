from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, getdate

from eduedge.api import teacher_assignments as core


def _overlap(start_a=None, end_a=None, start_b=None, end_b=None) -> bool:
	minimum = getdate("1900-01-01")
	maximum = getdate("2999-12-31")
	a_start = getdate(start_a) if start_a else minimum
	a_end = getdate(end_a) if end_a else maximum
	b_start = getdate(start_b) if start_b else minimum
	b_end = getdate(end_b) if end_b else maximum
	return a_start <= b_end and b_start <= a_end


def _allowed_branch_names() -> set[str]:
	return {str(row.get("name") or "").strip() for row in core._allowed_branches() if row.get("name")}


def _supporting_assignments(instructor: str, school_branch: str, valid_from=None, valid_to=None) -> list[dict]:
	rows = frappe.get_all(
		"EduEdge Instructor Assignment",
		filters={"instructor": instructor, "school_branch": school_branch},
		fields=[
			"name",
			"assignment_type",
			"program_offering",
			"student_group",
			"course",
			"valid_from",
			"valid_to",
			"enabled",
			"ended_on",
		],
		order_by="valid_from asc, creation asc",
		limit_page_length=0,
	)
	return [
		dict(row)
		for row in rows
		if _overlap(valid_from, valid_to, row.get("valid_from"), row.get("valid_to"))
	]


@frappe.whitelist()
def get_instructor_branch_eligibility_review(instructor: str) -> dict:
	"""Return permission-scoped eligibility support without mutating history.

	Branch Eligibility may legitimately exist before an exact academic assignment, so
	an enabled row with no supporting assignment is flagged for review rather than
	being treated as invalid or removed automatically.
	"""
	core._require_read()
	instructor = str(instructor or "").strip()
	if not instructor or not frappe.db.exists("Instructor", instructor):
		frappe.throw(_("Select a valid Instructor."), frappe.ValidationError)

	allowed = _allowed_branch_names()
	rows = frappe.get_list(
		"EduEdge Instructor Branch Assignment",
		filters={"instructor": instructor, "school_branch": ["in", sorted(allowed)]},
		fields=[
			"name",
			"school_branch",
			"branch_name",
			"enabled",
			"is_primary",
			"valid_from",
			"valid_to",
			"creation",
			"modified",
		],
		order_by="is_primary desc, school_branch asc, valid_from asc",
		limit_page_length=0,
	)

	review_rows = []
	active_branches: set[str] = set()
	for row in rows:
		support = _supporting_assignments(
			instructor,
			row.school_branch,
			row.valid_from,
			row.valid_to,
		)
		enabled = bool(cint(row.enabled))
		if enabled:
			active_branches.add(row.school_branch)
		review_required = bool(enabled and not support)
		review_rows.append(
			{
				**dict(row),
				"supporting_assignment_count": len(support),
				"supporting_assignments": support[:20],
				"review_required": review_required,
				"review_reason": _(
					"No academic assignment supports this eligibility period. Confirm that it is intentional explicit eligibility or disable it as legacy/stale history."
				) if review_required else "",
			}
		)

	return {
		"instructor": instructor,
		"active_branch_count": len(active_branches),
		"period_count": len(rows),
		"review_required_count": sum(1 for row in review_rows if row["review_required"]),
		"rows": review_rows,
	}


@frappe.whitelist(methods=["POST"])
def disable_unused_instructor_branch_eligibility(name: str, reason: str) -> dict:
	"""Disable a no-support eligibility row while preserving history and audit trail."""
	core._require_read()
	name = str(name or "").strip()
	reason = str(reason or "").strip()
	if not name or not reason:
		frappe.throw(_("Eligibility record and reason are required."), frappe.ValidationError)

	doc = frappe.get_doc("EduEdge Instructor Branch Assignment", name)
	doc.check_permission("write")
	if doc.school_branch not in _allowed_branch_names():
		frappe.throw(_("This Branch / Campus is not available to your user."), frappe.PermissionError)
	if not cint(doc.enabled):
		return {"name": doc.name, "status": "already-disabled"}
	if cint(doc.is_primary):
		frappe.throw(
			_("Primary Instructor Branch Eligibility cannot be disabled through stale-record cleanup. Review the Instructor's primary Branch first."),
			frappe.ValidationError,
		)

	support = _supporting_assignments(doc.instructor, doc.school_branch, doc.valid_from, doc.valid_to)
	if support:
		frappe.throw(
			_("This Branch Eligibility is still supported by {0} Instructor Assignment record(s) and cannot be disabled as unused.").format(len(support)),
			frappe.ValidationError,
		)

	doc.enabled = 0
	doc.is_primary = 0
	doc.save()
	doc.add_comment(
		"Info",
		_("Branch Eligibility disabled during governance reconciliation. Reason: {0}").format(reason),
	)
	return {
		"name": doc.name,
		"school_branch": doc.school_branch,
		"status": "disabled",
		"reason": reason,
	}
