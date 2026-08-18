from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime, nowdate

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.eduedge.doctype.eduedge_academic_session_launch.eduedge_academic_session_launch import STEP_LABELS
from eduedge.platform.access import require_eduedge_access
from eduedge.services.academic_calendar import ensure_institution_calendar, get_enabled_institution_calendar
from eduedge.services.institution_context import get_effective_institution_context


LAUNCH_DOCTYPE = "EduEdge Academic Session Launch"
MAX_SESSIONS = 500
LAUNCH_MANAGER_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Registrar",
}

STEP_DEFINITIONS = [
	{
		"key": "session_terms",
		"label": "Session & Terms",
		"description": "Academic Session, dated Terms and Institution Calendar readiness.",
		"route": "/app/eduedge-academic-sessions",
		"implemented": True,
	},
	{
		"key": "class_structure",
		"label": "Class Structure",
		"description": "Review the persistent Classes / Programmes that will operate in the new Session.",
		"route": "/app/eduedge-programs",
		"implemented": True,
	},
	{
		"key": "class_intakes",
		"label": "Class Intakes",
		"description": "Prepare the Branch + Class + Academic Session offerings required for the new Session.",
		"route": "/app/eduedge-program-offerings",
		"implemented": True,
	},
	{
		"key": "class_arms",
		"label": "Class Arms",
		"description": "Prepare new-session Class Arm structure without copying Students.",
		"route": "/app/eduedge-class-arms",
		"implemented": True,
	},
	{
		"key": "student_progression",
		"label": "Student Progression",
		"description": "Promote, repeat, transfer, complete or graduate returning Students through governed destination Enrollments.",
		"route": "/app/eduedge-student-progression",
		"implemented": False,
	},
	{
		"key": "admissions_enrollment",
		"label": "Admissions & Enrollment",
		"description": "Prepare new admissions, enrollment capacity and unresolved learner placement.",
		"route": "/app/eduedge-admissions",
		"implemented": False,
	},
	{
		"key": "academic_delivery",
		"label": "Academic Delivery",
		"description": "Subjects, Instructor assignments, teaching schedule and Scheme readiness.",
		"route": "/app/eduedge-academic-readiness",
		"implemented": False,
	},
	{
		"key": "assessment_cbt",
		"label": "Assessment & CBT",
		"description": "Prepare assessment structures and CBT readiness without copying historical results or attempts.",
		"route": "/app/eduedge-assessment-operations",
		"implemented": False,
	},
	{
		"key": "operational_readiness",
		"label": "Operational Readiness",
		"description": "Review enabled finance, boarding, transport, pickup, portal and notification capabilities.",
		"route": "/app/eduedge-setup-center",
		"implemented": False,
	},
	{
		"key": "final_review",
		"label": "Final Review & Activation",
		"description": "Resolve blockers, review readiness and activate the Session for operations.",
		"route": "/app/eduedge-academic-readiness",
		"implemented": False,
	},
]


def _require_manager(action: str) -> None:
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	require_eduedge_access(feature_key="academics", action=action)
	if frappe.session.user == "Administrator":
		return
	if LAUNCH_MANAGER_ROLES.intersection(set(frappe.get_roles())):
		return
	if frappe.has_permission("Academic Year", "write") and frappe.has_permission("Academic Term", "write"):
		return
	frappe.throw(_("You are not permitted to prepare an Academic Session Launch."), frappe.PermissionError)


def _normalise(value: Any) -> str:
	return " ".join(str(value or "").split())


def _resolve_institution(institution: str | None = None) -> tuple[str, dict]:
	context = get_effective_institution_context() or {}
	resolved = _normalise(institution) or _normalise(context.get("institution"))
	if not resolved or not frappe.db.exists("EduEdge Institution", resolved):
		frappe.throw(_("Select an Institution before preparing a Session Launch."), frappe.ValidationError)
	doc = frappe.get_doc("EduEdge Institution", resolved)
	doc.check_permission("read")
	if not cint(doc.enabled):
		frappe.throw(_("The selected Institution is disabled."), frappe.ValidationError)
	return resolved, context


def _session_options() -> list[dict]:
	if not frappe.has_permission("Academic Year", "read"):
		frappe.throw(_("You are not permitted to view Academic Sessions."), frappe.PermissionError)
	rows = frappe.get_all(
		"Academic Year",
		fields=["name", "academic_year_name", "year_start_date", "year_end_date"],
		order_by="year_start_date asc, name asc",
		page_length=MAX_SESSIONS,
	)
	today = getdate(nowdate())
	for row in rows:
		start = getdate(row.year_start_date)
		end = getdate(row.year_end_date)
		row["status"] = "Current" if start <= today <= end else "Upcoming" if today < start else "Past"
	return [dict(row) for row in rows]


def _suggest_target_session(sessions: list[dict]) -> str:
	upcoming = [row for row in sessions if row.get("status") == "Upcoming"]
	if upcoming:
		return upcoming[0]["name"]
	current = next((row for row in sessions if row.get("status") == "Current"), None)
	return current["name"] if current else (sessions[-1]["name"] if sessions else "")


def _suggest_source_session(sessions: list[dict], target: str) -> str:
	target_row = next((row for row in sessions if row.get("name") == target), None)
	if not target_row:
		return ""
	target_start = getdate(target_row.get("year_start_date"))
	candidates = [row for row in sessions if getdate(row.get("year_start_date")) < target_start]
	return candidates[-1]["name"] if candidates else ""


def _load_launch(institution: str, academic_year: str) -> frappe.model.document.Document | None:
	name = frappe.db.get_value(
		LAUNCH_DOCTYPE,
		{"institution": institution, "academic_year": academic_year},
		"name",
	)
	return frappe.get_doc(LAUNCH_DOCTYPE, name) if name else None


def _get_launch_by_name(name: str) -> frappe.model.document.Document:
	if not name or not frappe.db.exists(LAUNCH_DOCTYPE, name):
		frappe.throw(_("Session Launch could not be found."), frappe.DoesNotExistError)
	doc = frappe.get_doc(LAUNCH_DOCTYPE, name)
	_resolve_institution(doc.institution)
	return doc


def _serialize_launch(doc) -> dict | None:
	if not doc:
		return None
	return {
		"name": doc.name,
		"institution": doc.institution,
		"academic_year": doc.academic_year,
		"source_academic_year": doc.source_academic_year,
		"status": doc.status,
		"current_step_key": doc.current_step_key,
		"current_step_label": doc.current_step_label,
		"notes": doc.notes,
		"started_by": doc.started_by,
		"started_on": doc.started_on,
		"last_resumed_by": doc.last_resumed_by,
		"last_resumed_on": doc.last_resumed_on,
		"ready_on": doc.ready_on,
		"activated_on": doc.activated_on,
		"closed_on": doc.closed_on,
	}


def _term_readiness(academic_year: str) -> dict:
	terms = frappe.get_all(
		"Academic Term",
		filters={"academic_year": academic_year},
		fields=["name", "term_start_date", "term_end_date"],
		order_by="term_start_date asc, name asc",
		page_length=1000,
	)
	missing_dates = [row.name for row in terms if not row.term_start_date or not row.term_end_date]
	return {
		"count": len(terms),
		"missing_dates": missing_dates,
		"ready": bool(terms and not missing_dates),
	}


def _allowed_branches(institution: str) -> tuple[list[dict], int]:
	rows = frappe.get_list(
		"EduEdge School Branch",
		filters={"institution": institution, "enabled": 1},
		fields=["name", "branch_name"],
		order_by="branch_name asc, name asc",
		page_length=500,
	)
	total = frappe.db.count("EduEdge School Branch", {"institution": institution, "enabled": 1})
	return [dict(row) for row in rows], cint(total)


def _program_count(institution: str) -> int:
	if not frappe.get_meta("Program").has_field(INSTITUTION_FIELD):
		return 0
	return len(
		frappe.get_list(
			"Program",
			filters={INSTITUTION_FIELD: institution},
			fields=["name"],
			page_length=1000,
		)
	)


def _offering_count(branches: list[str], academic_year: str) -> int:
	if not branches:
		return 0
	return len(
		frappe.get_list(
			"EduEdge Program Offering",
			filters={"school_branch": ["in", branches], "academic_year": academic_year},
			fields=["name"],
			page_length=2000,
		)
	)


def _class_arm_count(branches: list[str], academic_year: str) -> int:
	if not branches or not frappe.get_meta("Student Group").has_field(BRANCH_FIELD):
		return 0
	return len(
		frappe.get_list(
			"Student Group",
			filters={BRANCH_FIELD: ["in", branches], "academic_year": academic_year, "disabled": 0},
			fields=["name"],
			page_length=2000,
		)
	)


def _enrollment_metrics(branches: list[str], academic_year: str) -> dict:
	if not branches or not frappe.get_meta("Program Enrollment").has_field(BRANCH_FIELD):
		return {"submitted": 0, "draft": 0}
	base = {BRANCH_FIELD: ["in", branches], "academic_year": academic_year}
	return {
		"submitted": len(
			frappe.get_list("Program Enrollment", filters={**base, "docstatus": 1}, fields=["name"], page_length=5000)
		),
		"draft": len(
			frappe.get_list("Program Enrollment", filters={**base, "docstatus": 0}, fields=["name"], page_length=5000)
		),
	}


def _step_payload(definition: dict, *, ready: bool = False, status: str = "Not started", metrics: dict | None = None, message: str = "") -> dict:
	return {
		**definition,
		"ready": bool(ready),
		"status": status,
		"metrics": metrics or {},
		"message": message,
	}


def _readiness(institution: str, academic_year: str, source_academic_year: str | None = None) -> dict:
	terms = _term_readiness(academic_year)
	calendar = get_enabled_institution_calendar(institution, academic_year=academic_year)
	branches, total_branch_count = _allowed_branches(institution)
	branch_names = [row["name"] for row in branches]
	program_count = _program_count(institution)
	offering_count = _offering_count(branch_names, academic_year)
	class_arm_count = _class_arm_count(branch_names, academic_year)
	enrollments = _enrollment_metrics(branch_names, academic_year)

	steps: list[dict] = []
	for definition in STEP_DEFINITIONS:
		key = definition["key"]
		if key == "session_terms":
			ready = terms["ready"] and bool(calendar)
			status = "Ready" if ready else "Needs attention"
			message = "Session, Terms and Institution Calendar are ready." if ready else (
				"Complete dated Terms. The Institution Calendar can then be prepared without a separate manual master."
			)
			steps.append(
				_step_payload(
					definition,
					ready=ready,
					status=status,
					metrics={
						"terms": terms["count"],
						"terms_missing_dates": len(terms["missing_dates"]),
						"calendar": calendar.name if calendar else "",
					},
					message=message,
				)
			)
		elif key == "class_structure":
			ready = program_count > 0
			steps.append(
				_step_payload(
					definition,
					ready=ready,
					status="Ready to review" if ready else "Needs attention",
					metrics={"classes": program_count},
					message="Persistent Class masters are available for Session preparation." if ready else "Create the Classes / Programmes required by the Institution.",
				)
			)
		elif key == "class_intakes":
			steps.append(
				_step_payload(
					definition,
					ready=False,
					status="Review required" if offering_count else "Not started",
					metrics={"class_intakes": offering_count},
					message="Slice 2 will add selective bulk preparation here; current records are shown for guided review.",
				)
			)
		elif key == "class_arms":
			steps.append(
				_step_payload(
					definition,
					ready=False,
					status="Review required" if class_arm_count else "Not started",
					metrics={"class_arms": class_arm_count},
					message="Structural rollover remains student-free; Slice 2 will embed the validated rollover planner here.",
				)
			)
		else:
			metrics = {}
			if key == "student_progression":
				metrics = {"source_session": source_academic_year or ""}
			elif key == "admissions_enrollment":
				metrics = enrollments
			steps.append(
				_step_payload(
					definition,
					ready=False,
					status="Planned",
					metrics=metrics,
					message="This stage is part of the saved launch plan and will be activated in a later implementation slice.",
				)
			)

	implemented = [row for row in steps if row.get("implemented")]
	ready_implemented = [row for row in implemented if row.get("ready")]
	return {
		"steps": steps,
		"summary": {
			"implemented_steps": len(implemented),
			"implemented_ready": len(ready_implemented),
			"foundation_progress_percent": round((len(ready_implemented) / len(implemented)) * 100) if implemented else 0,
			"accessible_branch_count": len(branches),
			"institution_branch_count": total_branch_count,
			"branch_scope_complete": len(branches) == total_branch_count,
			"target_submitted_enrollments": enrollments["submitted"],
			"target_draft_enrollments": enrollments["draft"],
		},
	}


def _response(institution: str, context: dict, sessions: list[dict], academic_year: str, launch=None) -> dict:
	return {
		"active_context": context,
		"institution": institution,
		"sessions": sessions,
		"academic_year": academic_year,
		"suggested_source_academic_year": _suggest_source_session(sessions, academic_year) if academic_year else "",
		"launch": _serialize_launch(launch),
		"readiness": _readiness(institution, academic_year, launch.source_academic_year if launch else None) if academic_year else {"steps": [], "summary": {}},
	}


@frappe.whitelist()
def get_session_launch_context(academic_year: str | None = None, institution: str | None = None) -> dict:
	_require_manager("get_session_launch_context")
	resolved_institution, context = _resolve_institution(institution)
	sessions = _session_options()
	selected = _normalise(academic_year)
	if selected and not any(row["name"] == selected for row in sessions):
		frappe.throw(_("Select a valid Academic Session."), frappe.ValidationError)
	if not selected:
		selected = _suggest_target_session(sessions)
	launch = _load_launch(resolved_institution, selected) if selected else None
	return _response(resolved_institution, context, sessions, selected, launch)


@frappe.whitelist(methods=["POST"])
def start_or_resume_session_launch(
	academic_year: str,
	institution: str | None = None,
	source_academic_year: str | None = None,
) -> dict:
	_require_manager("start_or_resume_session_launch")
	resolved_institution, context = _resolve_institution(institution)
	academic_year = _normalise(academic_year)
	if not academic_year or not frappe.db.exists("Academic Year", academic_year):
		frappe.throw(_("Select a valid Academic Session."), frappe.ValidationError)
	launch = _load_launch(resolved_institution, academic_year)
	if not launch:
		launch = frappe.new_doc(LAUNCH_DOCTYPE)
		launch.institution = resolved_institution
		launch.academic_year = academic_year
		launch.source_academic_year = _normalise(source_academic_year) or None
		launch.status = "Preparing"
		launch.current_step_key = "session_terms"
		launch.last_resumed_by = frappe.session.user
		launch.last_resumed_on = now_datetime()
		launch.insert(ignore_permissions=True)
	else:
		if launch.status == "Closed":
			frappe.throw(_("This Session Launch is closed and cannot be resumed."), frappe.ValidationError)
		requested_source = _normalise(source_academic_year)
		if requested_source:
			launch.source_academic_year = requested_source
		if launch.status == "Draft":
			launch.status = "Preparing"
		launch.last_resumed_by = frappe.session.user
		launch.last_resumed_on = now_datetime()
		launch.save(ignore_permissions=True)

	sessions = _session_options()
	return _response(resolved_institution, context, sessions, academic_year, launch)


@frappe.whitelist(methods=["POST"])
def save_session_launch_progress(
	launch: str,
	current_step: str,
	source_academic_year: str | None = None,
	notes: str | None = None,
) -> dict:
	_require_manager("save_session_launch_progress")
	doc = _get_launch_by_name(_normalise(launch))
	step = _normalise(current_step)
	if step not in STEP_LABELS:
		frappe.throw(_("Select a valid Session Launch step."), frappe.ValidationError)
	if doc.status == "Closed":
		frappe.throw(_("This Session Launch is closed and cannot be changed."), frappe.ValidationError)
	requested_source = _normalise(source_academic_year)
	if requested_source:
		doc.source_academic_year = requested_source
	doc.current_step_key = step
	if notes is not None:
		doc.notes = str(notes or "").strip()
	if doc.status == "Draft":
		doc.status = "Preparing"
	doc.last_resumed_by = frappe.session.user
	doc.last_resumed_on = now_datetime()
	doc.save(ignore_permissions=True)
	return {
		"launch": _serialize_launch(doc),
		"readiness": _readiness(doc.institution, doc.academic_year, doc.source_academic_year),
	}


@frappe.whitelist(methods=["POST"])
def prepare_session_foundation(launch: str) -> dict:
	_require_manager("prepare_session_foundation")
	doc = _get_launch_by_name(_normalise(launch))
	if doc.status == "Closed":
		frappe.throw(_("This Session Launch is closed and cannot be changed."), frappe.ValidationError)
	calendar = ensure_institution_calendar(doc.institution, doc.academic_year)
	if doc.current_step_key == "session_terms":
		doc.current_step_key = "class_structure"
	doc.status = "Preparing"
	doc.last_resumed_by = frappe.session.user
	doc.last_resumed_on = now_datetime()
	doc.save(ignore_permissions=True)
	return {
		"calendar": calendar,
		"launch": _serialize_launch(doc),
		"readiness": _readiness(doc.institution, doc.academic_year, doc.source_academic_year),
	}
