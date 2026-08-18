from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from hashlib import sha256
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime
from frappe.utils.synchronization import filelock

from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.branch_context import get_allowed_school_branches, is_branch_access_enforced

SCHEDULE_DOCTYPE = "EduEdge CBT Exam Schedule"
ASSIGNMENT_DOCTYPE = "EduEdge CBT Candidate Assignment"
INTERVENTION_DOCTYPE = "EduEdge CBT Intervention Log"
LIFECYCLE_DOCTYPE = "EduEdge CBT Lifecycle Log"

OPEN_SCHEDULE_STATUSES = ("Ready", "Active", "Suspended")
TERMINAL_CANDIDATE_STATUSES = ("Completed", "Withdrawn", "Disqualified")
CONFIRMED_CANDIDATE_STATUSES = ("Eligible", "Checked In", "Released", "Completed")
STARTED_CANDIDATE_STATUSES = ("Checked In", "Released")


@contextmanager
def controlled_cbt_operation(*flag_names: str) -> Iterator[None]:
	"""Mark trusted server-side CBT operations for the current request only."""
	previous = {flag_name: getattr(frappe.flags, flag_name, None) for flag_name in flag_names}
	try:
		for flag_name in flag_names:
			setattr(frappe.flags, flag_name, True)
		yield
	finally:
		for flag_name, value in previous.items():
			if value is None:
				frappe.flags.pop(flag_name, None)
			else:
				setattr(frappe.flags, flag_name, value)


def cbt_operation_flag(flag_name: str, doc=None) -> bool:
	return bool(
		(doc and getattr(getattr(doc, "flags", None), flag_name, False))
		or getattr(frappe.flags, flag_name, False)
	)


@contextmanager
def schedule_operation_lock(schedule_name: str | None, *, timeout: int = 30) -> Iterator[None]:
	"""Serialise mutations that can change one Schedule or its candidate set."""
	identity = str(schedule_name or "new-schedule").strip() or "new-schedule"
	digest = sha256(identity.encode("utf-8")).hexdigest()[:24]
	with filelock(f"eduedge-cbt-schedule-{digest}", timeout=timeout):
		yield


def user_can_access_branch(user: str, branch: str | None) -> bool:
	if not branch or user == "Administrator" or not is_branch_access_enforced():
		return True
	rows = get_allowed_school_branches(user=user)
	return branch in {row.get("name") for row in rows if row.get("name")}


def assert_user_branch_access(user: str, branch: str | None, label: str = "User") -> None:
	if user_can_access_branch(user, branch):
		return
	frappe.throw(
		_("{0} is not permitted to operate in the selected School Branch / Campus.").format(label),
		frappe.PermissionError,
	)


def validate_course_scope(course: str | None, branch: str | None) -> None:
	if not course or not branch:
		return
	branch_row = frappe.db.get_value(
		"EduEdge School Branch",
		branch,
		["institution", "company"],
		as_dict=True,
	)
	if not branch_row:
		frappe.throw(_("Select a valid School Branch / Campus."), frappe.ValidationError)
	meta = frappe.get_meta("Course")
	checks = (
		("eduedge_school_branch", branch, _("Branch / Campus")),
		("eduedge_institution", branch_row.institution, _("Institution")),
		("company", branch_row.company, _("Company")),
	)
	for fieldname, expected, label in checks:
		if not expected or not meta.has_field(fieldname):
			continue
		actual = frappe.db.get_value("Course", course, fieldname)
		if actual != expected:
			frappe.throw(
				_("The selected Subject / Course does not belong to the Schedule {0}.").format(label),
				frappe.ValidationError,
			)


def has_confirmed_candidates(schedule: str | None) -> bool:
	if not schedule:
		return False
	return bool(
		frappe.db.exists(
			ASSIGNMENT_DOCTYPE,
			{
				"exam_schedule": schedule,
				"assignment_status": ["in", list(CONFIRMED_CANDIDATE_STATUSES)],
			},
		)
	)


def assert_fields_mutable_after_candidate_confirmation(doc, before, protected_fields: Iterable[str]) -> None:
	if not before or not has_confirmed_candidates(doc.name):
		return
	for fieldname in protected_fields:
		if before.get(fieldname) != doc.get(fieldname):
			frappe.throw(
				_(
					"This Schedule already has confirmed candidates. Withdraw or resolve those assignments before changing Template, Branch, Class, Subject, Centre, timing or policy fields."
				),
				frappe.ValidationError,
			)


def candidate_rows(schedule: str) -> list[dict[str, Any]]:
	rows = frappe.get_all(
		ASSIGNMENT_DOCTYPE,
		filters={"exam_schedule": schedule},
		fields=["name", "student", "public_candidate_reference", "assignment_status"],
		order_by="creation asc",
	)
	return [dict(row) for row in rows]


def withdraw_non_started_candidates_for_cancellation(schedule: str, reason: str) -> list[str]:
	"""Withdraw Draft/Eligible candidates atomically; block candidates who already started."""
	clean_reason = str(reason or "").strip()
	if not clean_reason:
		frappe.throw(_("A reason is required to cancel an Examination Schedule."), frappe.ValidationError)
	rows = candidate_rows(schedule)
	started = [row for row in rows if row.get("assignment_status") in STARTED_CANDIDATE_STATUSES]
	if started:
		frappe.throw(
			_(
				"This Schedule has Checked In or Released candidates. Suspend and resolve those sittings before cancellation."
			),
			frappe.ValidationError,
		)

	withdrawn: list[str] = []
	for row in rows:
		if row.get("assignment_status") not in {"Draft", "Eligible"}:
			continue
		assignment = frappe.get_doc(ASSIGNMENT_DOCTYPE, row["name"], for_update=True)
		assignment.check_permission("write")
		assignment.assignment_status = "Withdrawn"
		assignment.status_change_reason = _("Schedule cancelled: {0}").format(clean_reason)
		assignment.save()
		withdrawn.append(assignment.name)
	return withdrawn


def validate_terminal_schedule_readiness(doc) -> None:
	if doc.status not in {"Completed", "Cancelled"}:
		return
	rows = candidate_rows(doc.name)
	open_rows = [
		row for row in rows if row.get("assignment_status") not in TERMINAL_CANDIDATE_STATUSES
	]
	if open_rows:
		frappe.throw(
			_("Resolve all open Candidate Assignments before completing or cancelling this Schedule."),
			frappe.ValidationError,
		)
	if doc.status == "Completed":
		if not rows:
			frappe.throw(_("A Schedule with no candidates cannot be marked Completed."), frappe.ValidationError)
		if not any(row.get("assignment_status") == "Completed" for row in rows):
			frappe.throw(
				_("At least one candidate must be Completed before the Schedule can be marked Completed."),
				frappe.ValidationError,
			)


def validate_activation_readiness(doc) -> None:
	if doc.status != "Active":
		return
	before = doc.get_doc_before_save()
	previous_status = before.status if before else "Draft"
	initial_activation = previous_status == "Ready"
	if get_datetime(doc.scheduled_end) <= now_datetime():
		frappe.throw(_("A Schedule that has already ended cannot be activated or resumed."), frappe.ValidationError)

	rows = candidate_rows(doc.name)
	if not rows:
		frappe.throw(_("Assign at least one candidate before activating this Schedule."), frappe.ValidationError)
	active_rows = [
		row
		for row in rows
		if row.get("assignment_status") not in TERMINAL_CANDIDATE_STATUSES
	]
	if not active_rows:
		frappe.throw(_("At least one non-terminal candidate is required before activation or resume."), frappe.ValidationError)
	if initial_activation:
		if any(row.get("assignment_status") == "Draft" for row in rows):
			frappe.throw(_("Resolve all Draft candidate assignments before activation."), frappe.ValidationError)
		if any(row.get("assignment_status") not in {"Eligible", "Checked In"} for row in active_rows):
			frappe.throw(_("Candidates must be Eligible or Checked In before initial activation."), frappe.ValidationError)

	centre = frappe.db.get_value(
		"EduEdge Examination Centre",
		doc.examination_centre,
		["capacity"],
		as_dict=True,
	)
	capacity = cint(centre.capacity if centre else 0)
	if capacity <= 0:
		frappe.throw(_("The Examination Centre must have a positive capacity before activation."), frappe.ValidationError)
	if len(active_rows) > capacity:
		frappe.throw(
			_("Assigned candidates ({0}) exceed the Examination Centre capacity ({1}).").format(
				len(active_rows), capacity
			),
			frappe.ValidationError,
		)

	_assert_no_schedule_overlap(doc, "examination_centre", doc.examination_centre, _("Examination Centre"))
	if doc.primary_invigilator:
		_assert_no_schedule_overlap(doc, "primary_invigilator", doc.primary_invigilator, _("Primary Invigilator"))
	_assert_no_candidate_overlap(
		doc,
		[row.get("student") for row in active_rows if row.get("student")],
		[
			row.get("public_candidate_reference")
			for row in active_rows
			if row.get("public_candidate_reference")
		],
	)


def _overlap_filters(doc) -> list[list[Any]]:
	return [
		["name", "!=", doc.name],
		["status", "in", list(OPEN_SCHEDULE_STATUSES)],
		["scheduled_start", "<", doc.scheduled_end],
		["scheduled_end", ">", doc.scheduled_start],
	]


def _assert_no_schedule_overlap(doc, fieldname: str, value: str, label: str) -> None:
	filters = _overlap_filters(doc)
	filters.append([fieldname, "=", value])
	conflict = frappe.get_all(
		SCHEDULE_DOCTYPE,
		filters=filters,
		fields=["name", "schedule_title", "scheduled_start", "scheduled_end"],
		limit_page_length=1,
	)
	if not conflict:
		return
	row = conflict[0]
	frappe.throw(
		_("{0} conflicts with {1} ({2}).").format(label, row.schedule_title or row.name, row.name),
		frappe.ValidationError,
	)


def _assert_no_candidate_overlap(doc, students: list[str], public_references: list[str]) -> None:
	_assert_no_candidate_identity_overlap(doc, "student", students, "Student")
	_assert_no_candidate_identity_overlap(
		doc,
		"public_candidate_reference",
		public_references,
		"Public Candidate Reference",
	)


def _assert_no_candidate_identity_overlap(
	doc,
	identity_field: str,
	identities: list[str],
	identity_label: str,
) -> None:
	if not identities:
		return
	assignments = frappe.get_all(
		ASSIGNMENT_DOCTYPE,
		filters={
			identity_field: ["in", identities],
			"exam_schedule": ["!=", doc.name],
			"assignment_status": ["not in", list(TERMINAL_CANDIDATE_STATUSES)],
		},
		fields=[identity_field, "exam_schedule"],
		limit_page_length=1000,
	)
	if not assignments:
		return
	other_schedule_names = sorted({row.exam_schedule for row in assignments if row.exam_schedule})
	other_schedules = frappe.get_all(
		SCHEDULE_DOCTYPE,
		filters=[
			["name", "in", other_schedule_names],
			["status", "in", list(OPEN_SCHEDULE_STATUSES)],
			["scheduled_start", "<", doc.scheduled_end],
			["scheduled_end", ">", doc.scheduled_start],
		],
		fields=["name", "schedule_title"],
	)
	conflicting_names = {row.name for row in other_schedules}
	if not conflicting_names:
		return
	assignment = next(row for row in assignments if row.exam_schedule in conflicting_names)
	other = next(row for row in other_schedules if row.name == assignment.exam_schedule)
	identity = assignment.get(identity_field)
	if identity_field == "student":
		identity = frappe.db.get_value("Student", identity, "student_name") or identity
	frappe.throw(
		_("{0} {1} has an overlapping Schedule: {2} ({3}).").format(
			identity_label, identity, other.schedule_title or other.name, other.name
		),
		frappe.ValidationError,
	)


def latest_candidate_entry_time(schedule) -> Any:
	start = get_datetime(schedule.scheduled_start)
	if cint(schedule.allow_late_entry):
		from datetime import timedelta

		return start + timedelta(minutes=cint(schedule.late_entry_grace_minutes))
	return start


def assert_check_in_window(schedule) -> None:
	if not cint(schedule.require_candidate_check_in):
		frappe.throw(_("Candidate check-in is disabled for this Schedule."), frappe.ValidationError)
	now = now_datetime()
	if schedule.check_in_opens_at and now < get_datetime(schedule.check_in_opens_at):
		frappe.throw(_("Candidate check-in has not opened for this Schedule."), frappe.ValidationError)
	if now > latest_candidate_entry_time(schedule):
		frappe.throw(_("Candidate check-in has closed for this Schedule."), frappe.ValidationError)


def assert_manual_release_window(schedule, previous_status: str) -> None:
	if schedule.candidate_start_mode != "Invigilator Releases Candidates":
		frappe.throw(
			_("Manual candidate release is available only when Candidate Start Mode is Invigilator Releases Candidates."),
			frappe.ValidationError,
		)
	if schedule.status != "Active":
		frappe.throw(_("Candidates can be released only after the Schedule becomes Active."), frappe.ValidationError)
	now = now_datetime()
	if now < get_datetime(schedule.scheduled_start):
		frappe.throw(_("Candidates cannot be released before the Scheduled Start."), frappe.ValidationError)
	if now > get_datetime(schedule.scheduled_end):
		frappe.throw(_("Candidate access has closed for this Schedule."), frappe.ValidationError)
	if cint(schedule.require_candidate_check_in):
		if previous_status != "Checked In":
			frappe.throw(_("The candidate must be Checked In before release."), frappe.ValidationError)
		return
	if previous_status != "Eligible":
		frappe.throw(_("Only an Eligible candidate can be released without check-in."), frappe.ValidationError)
	if now > latest_candidate_entry_time(schedule):
		frappe.throw(_("Candidate entry has closed for this Schedule."), frappe.ValidationError)


def write_lifecycle_log(
	*,
	reference_doctype: str,
	reference_name: str,
	exam_schedule: str,
	exam_scope: str | None,
	school_branch: str | None,
	event_type: str,
	from_status: str | None,
	to_status: str,
	reason: str,
	candidate_assignment: str | None = None,
) -> str:
	clean_reason = str(reason or "").strip()
	if not clean_reason:
		frappe.throw(_("A reason is required for this lifecycle action."), frappe.ValidationError)
	doc = frappe.new_doc(LIFECYCLE_DOCTYPE)
	doc.reference_doctype = reference_doctype
	doc.reference_name = reference_name
	doc.exam_schedule = exam_schedule
	doc.candidate_assignment = candidate_assignment
	doc.exam_scope = exam_scope
	doc.school_branch = school_branch
	doc.event_type = event_type
	doc.from_status = from_status or ""
	doc.to_status = to_status
	doc.reason = clean_reason
	doc.acted_by = frappe.session.user
	doc.acted_on = now_datetime()
	doc.flags.eduedge_internal_lifecycle_log = True
	# Source Schedule/Candidate permission has already been checked by the
	# controller. The audit record itself is not directly creatable by users.
	doc.insert(ignore_permissions=True)
	return doc.name
