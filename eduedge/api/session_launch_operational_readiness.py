from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, get_time

from eduedge.api.session_launch import _get_launch_by_name, _require_manager
from eduedge.api.session_launch_assessment import get_assessment_cbt_readiness
from eduedge.api.session_launch_delivery import _context as get_delivery_context
from eduedge.api.session_launch_learners import _context as get_learner_context
from eduedge.api.session_launch_structure import _context_for_doc as get_structure_context
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.academic_calendar import get_enabled_institution_calendar


STATUS_READY = "Ready"
STATUS_ATTENTION = "Attention"
STATUS_BLOCKED = "Blocked"
MAX_ISSUES = 30
MAX_ASSESSMENT_CONFLICT_ROWS = 5000
RESOURCE_LABELS = {
	"student_group": "Class Arm",
	"instructor": "Instructor / Assessment Supervisor",
	"room": "Room",
}


def _category(key, label, status, message, *, route, metrics=None, issues=None) -> dict:
	return {
		"key": key,
		"label": label,
		"status": status,
		"ready": status == STATUS_READY,
		"message": message,
		"route": route,
		"metrics": metrics or {},
		"issues": (issues or [])[:MAX_ISSUES],
	}


def _add_interval(buckets, *, row, resource_type, value, source_type, source_name) -> None:
	if not value or not row.get("schedule_date") or row.get("from_time") is None or row.get("to_time") is None:
		return
	start = get_time(row.get("from_time"))
	end = get_time(row.get("to_time"))
	if start >= end:
		return
	buckets[(str(row.get("schedule_date")), resource_type, str(value))].append(
		{"source_type": source_type, "source_name": source_name, "start": start, "end": end}
	)


def _assessment_conflict_rows(delivery: dict) -> tuple[list[dict], bool]:
	branches = sorted({row.get("branch") for row in delivery.get("branches") or [] if row.get("branch")})
	if not branches or not frappe.has_permission("Assessment Plan", "read"):
		return [], False
	rows = frappe.get_list(
		"Assessment Plan",
		filters={BRANCH_FIELD: ["in", branches], "academic_year": delivery.get("academic_year"), "docstatus": ["!=", 2]},
		fields=["name", "student_group", "room", "supervisor", "schedule_date", "from_time", "to_time"],
		order_by="schedule_date asc, from_time asc, name asc",
		page_length=MAX_ASSESSMENT_CONFLICT_ROWS,
	)
	return [dict(row) for row in rows], len(rows) >= MAX_ASSESSMENT_CONFLICT_ROWS


def _timetable_conflicts(delivery: dict) -> list[str]:
	"""Batch-scan permission-filtered Teaching Schedules and Assessment Plans."""
	buckets: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
	issues: list[str] = []
	for branch in delivery.get("branches") or []:
		for raw in branch.get("schedule_rows") or []:
			row = dict(raw)
			for resource_type, value in (
				("student_group", row.get("student_group")),
				("instructor", row.get("instructor")),
				("room", row.get("room")),
			):
				_add_interval(
					buckets,
					row=row,
					resource_type=resource_type,
					value=value,
					source_type="Teaching Schedule",
					source_name=row.get("name") or "",
				)

	assessment_rows, truncated = _assessment_conflict_rows(delivery)
	if truncated:
		issues.append(_("Assessment conflict scan reached its safety limit; narrow the Session scope before activation."))
	for row in assessment_rows:
		for resource_type, value in (
			("student_group", row.get("student_group")),
			("instructor", row.get("supervisor")),
			("room", row.get("room")),
		):
			_add_interval(
				buckets,
				row=row,
				resource_type=resource_type,
				value=value,
				source_type="Assessment Plan",
				source_name=row.get("name") or "",
			)

	seen = set()
	for (schedule_date, resource_type, value), intervals in buckets.items():
		active = []
		for current in sorted(intervals, key=lambda row: (row["start"], row["end"], row["source_type"], row["source_name"])):
			active = [row for row in active if row["end"] > current["start"]]
			for other in active:
				if current["source_type"] == other["source_type"] == "Assessment Plan":
					continue
				pair = tuple(sorted((f"{current['source_type']}:{current['source_name']}", f"{other['source_type']}:{other['source_name']}")))
				signature = pair + (schedule_date, resource_type, value)
				if signature in seen:
					continue
				seen.add(signature)
				issues.append(
					_("{0} {1} conflicts with {2} {3} on {4} for {5} \"{6}\".").format(
						_(current["source_type"]), current["source_name"], _(other["source_type"]), other["source_name"],
						schedule_date, _(RESOURCE_LABELS[resource_type]), value,
					)
				)
				if len(issues) >= MAX_ISSUES:
					return issues
			active.append(current)
	return issues


def _foundation_category(doc, delivery):
	terms = delivery.get("academic_terms") or []
	calendar = get_enabled_institution_calendar(doc.institution, academic_year=doc.academic_year)
	issues = []
	if not terms:
		issues.append(_("No dated Terms / Semesters are available in the Institution Academic Calendar."))
	if not calendar:
		issues.append(_("The Institution Academic Calendar has not been prepared."))
	status = STATUS_READY if not issues else STATUS_BLOCKED
	return _category(
		"foundation", _("Session Foundation"), status,
		_("Session, Terms and Institution Calendar are ready.") if status == STATUS_READY else _("Complete the Session calendar foundation before activation."),
		route="/app/eduedge-academic-sessions", metrics={"terms": len(terms), "calendar": calendar.name if calendar else ""}, issues=issues,
	)


def _branch_scope_category(delivery):
	scope = delivery.get("branch_scope") or {}
	accessible, total, complete = cint(scope.get("accessible")), cint(scope.get("institution_total")), bool(scope.get("complete"))
	issues = [] if complete else [_('Your current Branch scope covers {0} of {1} enabled Institution Branches. Final readiness must be reviewed with complete Institution scope.').format(accessible, total)]
	return _category(
		"branch_scope", _("Branch / Campus Scope"), STATUS_READY if complete else STATUS_BLOCKED,
		_("All enabled Branches are represented in this readiness review.") if complete else _("The readiness review is incomplete because some enabled Branches are outside the current user's scope."),
		route="/app/eduedge-branch-governance", metrics={"accessible_branches": accessible, "institution_branches": total}, issues=issues,
	)


def _structure_category(structure, delivery):
	summary = structure.get("summary") or {}
	delivery_summary = delivery.get("summary") or {}
	issues, blocked = [], False
	if not cint(summary.get("intended_classes")):
		issues.append(_("No Classes / Programmes are configured for this Institution.")); blocked = True
	if not cint(delivery_summary.get("class_intakes")):
		issues.append(_("No active Class Intakes are available for the target Session.")); blocked = True
	if cint(summary.get("missing_intakes")):
		issues.append(_("{0} intended Class Intakes are still missing.").format(cint(summary.get("missing_intakes")))); blocked = True
	if not cint(delivery_summary.get("class_arms")):
		issues.append(_("No active Class Arms are available for the target Session.")); blocked = True
	if cint(summary.get("arms_blocked")):
		issues.append(_("{0} Class Arm rollover rows are blocked.").format(cint(summary.get("arms_blocked")))); blocked = True
	if cint(summary.get("arms_ready_to_create")):
		issues.append(_("{0} Class Arms are still ready to create from the source Session.").format(cint(summary.get("arms_ready_to_create"))))
	status = STATUS_BLOCKED if blocked else STATUS_ATTENTION if issues else STATUS_READY
	return _category(
		"structure", _("Classes, Intakes & Class Arms"), status,
		_("Session class structure is operationally ready.") if status == STATUS_READY else _("Resolve outstanding class structure preparation before final review."),
		route="/app/eduedge-class-arms",
		metrics={"classes": cint(summary.get("intended_classes")), "class_intakes": cint(delivery_summary.get("class_intakes")), "class_arms": cint(delivery_summary.get("class_arms")), "missing_intakes": cint(summary.get("missing_intakes")), "arms_to_create": cint(summary.get("arms_ready_to_create")), "arms_blocked": cint(summary.get("arms_blocked"))},
		issues=issues,
	)


def _learner_category(learners):
	summary = learners.get("summary") or {}
	issues, blocked = [], False
	unresolved = cint(summary.get("decision_required")) + cint(summary.get("draft_prepared")) + cint(summary.get("target_submitted"))
	if unresolved:
		issues.append(_("{0} returning Student progression decisions are not finalized.").format(unresolved)); blocked = True
	if cint(summary.get("submitted_unassigned")):
		issues.append(_("{0} submitted Enrollments are not assigned to a Class Arm.").format(cint(summary.get("submitted_unassigned")))); blocked = True
	if cint(summary.get("draft_enrollments")):
		issues.append(_("{0} target-session Enrollments remain in Draft.").format(cint(summary.get("draft_enrollments"))))
	if not summary.get("admissions_ready", True):
		missing = max(cint(summary.get("admission_branches_required")) - cint(summary.get("admission_branches_ready")), 0)
		issues.append(_("{0} Branches with admission-enabled Class Intakes do not yet have an Admission cycle.").format(missing))
	status = STATUS_BLOCKED if blocked else STATUS_ATTENTION if issues else STATUS_READY
	return _category(
		"learners", _("Progression, Admissions & Enrollment"), status,
		_("Returning and new Student placement is ready.") if status == STATUS_READY else _("Review unresolved Student placement and admission preparation."),
		route="/app/eduedge-student-enrollments",
		metrics={"source_enrollments": cint(summary.get("source_enrollments")), "progression_finalized": cint(summary.get("finalized")), "progression_unresolved": unresolved, "submitted_enrollments": cint(summary.get("submitted_enrollments")), "draft_enrollments": cint(summary.get("draft_enrollments")), "submitted_unassigned": cint(summary.get("submitted_unassigned"))},
		issues=issues,
	)


def _delivery_category(delivery, conflicts):
	summary = delivery.get("summary") or {}
	issues, blocked = list(conflicts), bool(conflicts)
	if cint(summary.get("classes_without_subjects")):
		issues.append(_("{0} Class Intakes have no curriculum Subjects.").format(cint(summary.get("classes_without_subjects")))); blocked = True
	if cint(summary.get("unassigned_teaching_contexts")):
		issues.append(_("{0} teaching responsibilities have no effective Instructor assignment.").format(cint(summary.get("unassigned_teaching_contexts")))); blocked = True
	if summary.get("class_responsibility_required") and cint(summary.get("class_responsibility_missing")):
		issues.append(_("{0} Class Arms have no Class/Form Teacher responsibility assignment.").format(cint(summary.get("class_responsibility_missing"))))
	if cint(summary.get("unscheduled_teaching_contexts")):
		issues.append(_("{0} Class Arm × Subject contexts have no Teaching Schedule coverage.").format(cint(summary.get("unscheduled_teaching_contexts"))))
	if cint(summary.get("scheme_attention_contexts")):
		issues.append(_("{0} teaching contexts do not have approved Scheme coverage for every configured Term.").format(cint(summary.get("scheme_attention_contexts"))))
	if summary.get("schedule_truncated") or summary.get("scheme_truncated"):
		issues.append(_("Readiness data reached a safety limit; narrow the Session scope before final review.")); blocked = True
	status = STATUS_BLOCKED if blocked else STATUS_ATTENTION if issues else STATUS_READY
	return _category(
		"academic_delivery", _("Academic Delivery"), status,
		_("Curriculum, teaching responsibility, timetable and Scheme coverage are ready.") if status == STATUS_READY else _("Resolve Academic Delivery exceptions before Session activation."),
		route="/app/eduedge-academic-readiness",
		metrics={"teaching_contexts": cint(summary.get("expected_teaching_contexts")), "unassigned": cint(summary.get("unassigned_teaching_contexts")), "unscheduled": cint(summary.get("unscheduled_teaching_contexts")), "scheme_attention": cint(summary.get("scheme_attention_contexts")), "class_teacher_missing": cint(summary.get("class_responsibility_missing")), "timetable_conflicts": len(conflicts)},
		issues=issues,
	)


def _assessment_category(payload):
	state = payload.get("assessment") or {}
	issues = [_('{0}: {1}').format(row.get("term_name") or row.get("academic_term"), row.get("message") or _("Assessment readiness needs attention.")) for row in state.get("term_rows") or [] if row.get("status") != STATUS_READY]
	status = STATUS_READY if state.get("ready") else STATUS_ATTENTION
	return _category(
		"assessment", _("Assessment Readiness"), status,
		_("Assessment planning is ready across configured Terms.") if status == STATUS_READY else _("Assessment planning has outstanding Term or Class Arm coverage."),
		route="/app/eduedge-assessment-operations",
		metrics={"submitted_plans": cint(state.get("submitted_plans")), "draft_plans": cint(state.get("draft_plans")), "class_arms": cint(state.get("class_arms"))}, issues=issues,
	)


def _cbt_category(payload):
	state = payload.get("cbt") or {}
	if not state.get("planned"):
		return _category("cbt", _("CBT Readiness"), STATUS_READY, _("No CBT sitting is planned for this Session. CBT is optional and does not block launch."), route="/app/eduedge-cbt-operations", metrics={"planned_schedules": 0, "status": "Not Planned"})
	issues = [_('{0}: {1}').format(row.get("term_name") or row.get("academic_term"), issue) for row in state.get("term_rows") or [] for issue in row.get("issues") or []]
	status = STATUS_READY if state.get("ready") else STATUS_ATTENTION
	return _category(
		"cbt", _("CBT Readiness"), status,
		_("Configured CBT sittings are operationally ready.") if status == STATUS_READY else _("Configured CBT sittings have readiness exceptions."),
		route="/app/eduedge-cbt-schedules",
		metrics={"planned_schedules": cint(state.get("schedules")), "approved_templates": cint(state.get("approved_templates")), "approved_questions": cint(state.get("approved_question_bank_questions"))}, issues=issues,
	)


def _calendar_category(doc):
	calendar = get_enabled_institution_calendar(doc.institution, academic_year=doc.academic_year)
	branches = frappe.get_list("EduEdge School Branch", filters={"institution": doc.institution, "enabled": 1}, pluck="name", page_length=500)
	events = 0
	if calendar and branches and frappe.db.exists("DocType", "EduEdge School Event") and frappe.has_permission("EduEdge School Event", "read"):
		events = len(frappe.get_list("EduEdge School Event", filters={"school_branch": ["in", branches], "academic_year": doc.academic_year, "status": ["!=", "Archived"]}, fields=["name"], page_length=5000))
	status = STATUS_READY if calendar else STATUS_BLOCKED
	return _category(
		"school_calendar", _("School Calendar & Events"), status,
		_("The unified School Calendar is available. Managed School Events are optional.") if calendar else _("Prepare the Institution Academic Calendar before activation."),
		route="/app/eduedge-school-calendar", metrics={"calendar": calendar.name if calendar else "", "school_events": events}, issues=[] if calendar else [_('Institution Academic Calendar is missing.')],
	)


def _attendance_category(delivery):
	summary = delivery.get("summary") or {}
	class_arms, unscheduled = cint(summary.get("class_arms")), cint(summary.get("unscheduled_teaching_contexts"))
	if not class_arms:
		status, issues = STATUS_BLOCKED, [_('Attendance cannot operate because no active Class Arms are available.')]
	elif unscheduled:
		status, issues = STATUS_ATTENTION, [_('{0} teaching contexts are unscheduled; daily attendance coverage may be incomplete.').format(unscheduled)]
	else:
		status, issues = STATUS_READY, []
	return _category(
		"attendance", _("Attendance Readiness"), status,
		_("Attendance can operate from the prepared Class Arms and Teaching Schedule. No historical attendance rows are required for launch.") if status == STATUS_READY else _("Resolve Class Arm or timetable readiness before relying on attendance operations."),
		route="/app/eduedge-attendance", metrics={"class_arms": class_arms, "unscheduled_teaching_contexts": unscheduled}, issues=issues,
	)


def _overall(categories):
	blocked = [row for row in categories if row["status"] == STATUS_BLOCKED]
	attention = [row for row in categories if row["status"] == STATUS_ATTENTION]
	if blocked:
		status, message = STATUS_BLOCKED, _("Resolve hard operational blockers before Final Review & Activation.")
	elif attention:
		status, message = STATUS_ATTENTION, _("No hard blocker remains, but operational warnings should be reviewed before activation.")
	else:
		status, message = STATUS_READY, _("All currently implemented Session Launch readiness categories are ready for Final Review.")
	return {"status": status, "ready": status == STATUS_READY, "message": message, "blocked_categories": len(blocked), "attention_categories": len(attention), "ready_categories": sum(1 for row in categories if row["status"] == STATUS_READY), "total_categories": len(categories)}


@frappe.whitelist()
def get_session_launch_operational_readiness(launch: str) -> dict:
	"""Return a governed, read-only readiness aggregate without exposing the orchestration DocType."""
	_require_manager("get_session_launch_operational_readiness")
	doc = _get_launch_by_name(str(launch or "").strip())
	structure = get_structure_context(doc)
	learners = get_learner_context(doc)
	delivery = get_delivery_context(doc)
	assessment = get_assessment_cbt_readiness(doc.name)
	conflicts = _timetable_conflicts(delivery)
	categories = [
		_foundation_category(doc, delivery), _branch_scope_category(delivery), _structure_category(structure, delivery),
		_learner_category(learners), _delivery_category(delivery, conflicts), _assessment_category(assessment), _cbt_category(assessment),
		_calendar_category(doc), _attendance_category(delivery),
	]
	return {
		"launch": doc.name,
		"institution": doc.institution,
		"academic_year": doc.academic_year,
		"source_academic_year": doc.source_academic_year or "",
		"overall": _overall(categories),
		"categories": categories,
		"blockers": [row for row in categories if row["status"] == STATUS_BLOCKED],
		"warnings": [row for row in categories if row["status"] == STATUS_ATTENTION],
		"branch_scope": delivery.get("branch_scope") or {},
		"read_only": True,
	}
