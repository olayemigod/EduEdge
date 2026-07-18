from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.education.academic_operations import assert_instructor_assignment
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access

PUBLICATION_DOCTYPE = "EduEdge Result Publication"
PUBLICATION_LOG_DOCTYPE = "EduEdge Result Publication Log"
PUBLICATION_STATUSES = {
	"Draft",
	"Pending Approval",
	"Approved",
	"Rejected",
	"Published",
}


def before_validate_assessment_plan(doc, method=None) -> None:
	group = _get_student_group(doc.student_group)
	_assign_branch(doc, group.get(BRANCH_FIELD))
	_validate_branch(doc)
	_validate_linked_context(doc, group)

	if doc.room:
		room_branch = frappe.db.get_value("Room", doc.room, BRANCH_FIELD)
		if room_branch != doc.get(BRANCH_FIELD):
			frappe.throw(
				_("Assessment room must belong to the selected School Branch / Campus."),
				frappe.ValidationError,
			)

	reference_date = doc.schedule_date or nowdate()
	for fieldname, label in (("examiner", _("Examiner")), ("supervisor", _("Supervisor"))):
		instructor = doc.get(fieldname)
		if not instructor:
			continue
		try:
			assert_instructor_assignment(
				instructor,
				doc.get(BRANCH_FIELD),
				reference_date=reference_date,
			)
		except frappe.ValidationError:
			frappe.throw(
				_("{0} {1} is not assigned to School Branch / Campus {2}.").format(
					label, instructor, doc.get(BRANCH_FIELD)
				),
				frappe.ValidationError,
			)


def before_validate_assessment_result(doc, method=None) -> None:
	plan = _get_assessment_plan(doc.assessment_plan)
	student_branch = frappe.db.get_value("Student", doc.student, BRANCH_FIELD)
	plan_branch = plan.get(BRANCH_FIELD)
	resolved_branch = plan_branch or student_branch
	_assign_branch(doc, resolved_branch)
	_validate_branch(doc)

	if plan_branch and doc.get(BRANCH_FIELD) != plan_branch:
		frappe.throw(
			_("Assessment Result Branch must match the selected Assessment Plan Branch."),
			frappe.ValidationError,
		)
	if student_branch and doc.get(BRANCH_FIELD) != student_branch:
		frappe.throw(
			_("Assessment Result Branch must match the selected Student Branch."),
			frappe.ValidationError,
		)
	if plan.student_group and not frappe.db.exists(
		"Student Group Student",
		{"parent": plan.student_group, "student": doc.student, "active": 1},
	):
		frappe.throw(
			_("Student {0} is not an active member of Student Group {1}.").format(
				doc.student, plan.student_group
			),
			frappe.ValidationError,
		)


def validate_publication_scope(doc) -> None:
	if doc.status not in PUBLICATION_STATUSES:
		frappe.throw(_("Invalid result publication status."), frappe.ValidationError)
	group = _get_student_group(doc.student_group)
	branch = group.get(BRANCH_FIELD)
	if branch != doc.school_branch:
		frappe.throw(
			_("Result Publication Branch must match the selected Student Group Branch."),
			frappe.ValidationError,
		)
	assert_branch_access(doc.school_branch)
	if group.academic_year != doc.academic_year:
		frappe.throw(
			_("Result Publication Academic Year must match the Student Group."),
			frappe.ValidationError,
		)
	if doc.academic_term and group.academic_term and doc.academic_term != group.academic_term:
		frappe.throw(
			_("Result Publication Academic Term must match the Student Group."),
			frappe.ValidationError,
		)
	if doc.academic_term:
		actual_year = frappe.db.get_value("Academic Term", doc.academic_term, "academic_year")
		if actual_year != doc.academic_year:
			frappe.throw(
				_("Academic Term {0} does not belong to Academic Year {1}.").format(
					doc.academic_term, doc.academic_year
				),
				frappe.ValidationError,
			)

	if doc.is_new():
		return
	if doc.has_value_changed("status") and not getattr(
		frappe.flags, "in_eduedge_result_publication_transition", False
	):
		frappe.throw(
			_("Use the EduEdge Result Publication actions to change status."),
			frappe.ValidationError,
		)


def get_publication_readiness(
	*,
	school_branch: str,
	student_group: str,
	academic_year: str,
	assessment_group: str,
	academic_term: str | None = None,
) -> dict:
	assert_branch_access(school_branch)
	group = _get_student_group(student_group)
	if group.get(BRANCH_FIELD) != school_branch:
		frappe.throw(_("Student Group belongs to another branch."), frappe.PermissionError)

	plan_filters: dict = {
		BRANCH_FIELD: school_branch,
		"student_group": student_group,
		"academic_year": academic_year,
		"assessment_group": assessment_group,
		"docstatus": 1,
	}
	if academic_term:
		plan_filters["academic_term"] = academic_term
	plans = frappe.get_all(
		"Assessment Plan",
		filters=plan_filters,
		fields=["name", "assessment_name", "course", "maximum_assessment_score"],
		order_by="schedule_date asc, course asc",
	)
	students = frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group, "active": 1},
		fields=["student", "student_name", "group_roll_number"],
		order_by="group_roll_number asc, student_name asc",
	)
	plan_names = [row.name for row in plans]
	student_names = [row.student for row in students]

	results = []
	if plan_names and student_names:
		results = frappe.get_all(
			"Assessment Result",
			filters={
				BRANCH_FIELD: school_branch,
				"assessment_plan": ["in", plan_names],
				"student": ["in", student_names],
				"docstatus": ["!=", 2],
			},
			fields=["name", "assessment_plan", "student", "docstatus", "total_score", "grade"],
			page_length=0,
		)

	result_pairs = {(row.assessment_plan, row.student) for row in results}
	expected = len(plans) * len(students)
	submitted = sum(1 for row in results if row.docstatus == 1)
	drafts = sum(1 for row in results if row.docstatus == 0)
	missing = max(expected - len(result_pairs), 0)
	ready = bool(plans and students and submitted == expected and drafts == 0 and missing == 0)

	return {
		"ready": ready,
		"school_branch": school_branch,
		"student_group": student_group,
		"academic_year": academic_year,
		"academic_term": academic_term,
		"assessment_group": assessment_group,
		"expected_results": expected,
		"submitted_results": submitted,
		"draft_results": drafts,
		"missing_results": missing,
		"assessment_plan_count": len(plans),
		"student_count": len(students),
		"plans": plans,
		"students": students,
	}


def append_publication_log(
	publication: str,
	*,
	action: str,
	from_status: str | None,
	to_status: str,
	remarks: str | None = None,
) -> str:
	log = frappe.get_doc(
		{
			"doctype": PUBLICATION_LOG_DOCTYPE,
			"result_publication": publication,
			"action": action,
			"from_status": from_status,
			"to_status": to_status,
			"acted_by": frappe.session.user,
			"acted_on": frappe.utils.now_datetime(),
			"remarks": remarks,
		}
	)
	log.insert(ignore_permissions=True)
	return log.name


def _assign_branch(doc, branch: str | None) -> None:
	if branch and not doc.get(BRANCH_FIELD):
		doc.set(BRANCH_FIELD, branch)


def _validate_branch(doc) -> None:
	branch = doc.get(BRANCH_FIELD)
	if not branch:
		frappe.throw(
			_("Select a School Branch / Campus before saving this record."),
			frappe.ValidationError,
		)
	assert_branch_access(branch)


def _validate_linked_context(doc, group) -> None:
	for fieldname in ("program", "course", "academic_year", "academic_term"):
		plan_value = doc.get(fieldname)
		group_value = group.get(fieldname)
		if plan_value and group_value and plan_value != group_value:
			frappe.throw(
				_("Assessment Plan {0} must match the selected Student Group.").format(fieldname),
				frappe.ValidationError,
			)
	if doc.schedule_date:
		date = getdate(doc.schedule_date)
		if group.academic_term:
			start_date, end_date = frappe.db.get_value(
				"Academic Term", group.academic_term, ["term_start_date", "term_end_date"]
			)
		else:
			start_date, end_date = frappe.db.get_value(
				"Academic Year", group.academic_year, ["year_start_date", "year_end_date"]
			)
		if start_date and end_date and not (getdate(start_date) <= date <= getdate(end_date)):
			frappe.throw(
				_("Assessment date must lie within the Student Group academic period."),
				frappe.ValidationError,
			)


def _get_student_group(name: str):
	row = frappe.db.get_value(
		"Student Group",
		name,
		["name", "academic_year", "academic_term", "program", "course", BRANCH_FIELD],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Student Group does not exist."), frappe.DoesNotExistError)
	return row


def _get_assessment_plan(name: str):
	row = frappe.db.get_value(
		"Assessment Plan",
		name,
		[
			"name",
			"student_group",
			"academic_year",
			"academic_term",
			"assessment_group",
			BRANCH_FIELD,
		],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Assessment Plan does not exist."), frappe.DoesNotExistError)
	return row
