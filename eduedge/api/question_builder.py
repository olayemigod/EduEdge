from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.utils import cint, flt

from eduedge.cbt.public_access import get_public_exam_capability_summary
from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.curriculum_permissions import is_teacher_user
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.teaching_assignments import assigned_courses
from eduedge.eduedge.doctype.eduedge_cbt_question.eduedge_cbt_question import (
	PLATFORM_BANK,
	SCHOOL_BANK,
	_require_question_author,
	can_review_questions,
	course_topic_query,
)
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

QUESTION_DOCTYPE = "EduEdge CBT Question"
EDITABLE_FIELDS = (
	"ownership_scope",
	"school_branch",
	"program_offering",
	"student_group",
	"version_number",
	"supersedes_question",
	"course",
	"topic",
	"curriculum",
	"exam_body",
	"difficulty",
	"question_type",
	"question_text",
	"answer_key",
	"marking_guide",
	"default_mark",
	"negative_mark",
	"notes",
)
QUESTION_TYPES = (
	"Single Choice",
	"Multiple Choice",
	"True/False",
	"Yes/No",
	"Short Answer",
	"Essay",
	"Numeric",
)
DIFFICULTIES = ("Easy", "Moderate", "Hard")
EXAM_BODIES = ("School Internal", "WAEC", "NECO", "JAMB", "Post-UTME", "Other")
EDITABLE_STATUSES = {"Draft", "Changes Requested"}


def _parse_payload(payload) -> dict:
	if isinstance(payload, str):
		return frappe.parse_json(payload) or {}
	return payload or {}


def _require_question_reader() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	if not frappe.has_permission(QUESTION_DOCTYPE, "read"):
		frappe.throw(_("You are not permitted to view CBT questions."), frappe.PermissionError)


def _require_readable_question(name: str):
	doc = frappe.get_doc(QUESTION_DOCTYPE, name)
	if not doc.has_permission("read"):
		frappe.throw(_("You are not permitted to view this CBT question."), frappe.PermissionError)
	return doc


def _question_scope_options(public_access: dict, current_scope: str | None = None) -> list[dict]:
	options = [{"value": SCHOOL_BANK, "label": _("School Question Bank")}]
	can_author_public = bool(public_access.get("capabilities", {}).get("author", {}).get("allowed"))
	if can_author_public or current_scope == PLATFORM_BANK:
		options.append({"value": PLATFORM_BANK, "label": _("EduEdge Examination Bank")})
	return options


def _course_label(course: str | None) -> str:
	return frappe.db.get_value("Course", course, "course_name") or course if course else ""


def _topic_label(topic: str | None) -> str:
	return frappe.db.get_value("Topic", topic, "topic_name") or topic if topic else ""


def _serialize_question(doc) -> dict:
	return {
		"name": doc.name if not doc.is_new() else None,
		"question_code": doc.question_code or "",
		"ownership_scope": doc.ownership_scope or SCHOOL_BANK,
		"school_branch": doc.school_branch or "",
		"institution": doc.institution or "",
		"program_offering": doc.program_offering or "",
		"student_group": doc.student_group or "",
		"version_number": cint(doc.version_number) or 1,
		"supersedes_question": doc.supersedes_question or "",
		"course": doc.course or "",
		"course_label": _course_label(doc.course),
		"topic": doc.topic or "",
		"topic_label": _topic_label(doc.topic),
		"curriculum": doc.curriculum or "",
		"exam_body": doc.exam_body or "School Internal",
		"difficulty": doc.difficulty or "",
		"question_type": doc.question_type or "Single Choice",
		"question_text": doc.question_text or "",
		"options": [
			{
				"option_key": row.option_key or "",
				"option_text": row.option_text or "",
				"is_correct": cint(row.is_correct),
				"display_order": cint(row.display_order) or cint(row.idx),
			}
			for row in (doc.get("options") or [])
		],
		"answer_key": doc.answer_key or "",
		"marking_guide": doc.marking_guide or "",
		"default_mark": flt(doc.default_mark) or 1,
		"negative_mark": flt(doc.negative_mark),
		"status": doc.status or "Draft",
		"recommended_by": doc.recommended_by or "",
		"recommended_on": doc.recommended_on,
		"review_feedback": doc.review_feedback or "",
		"reviewed_by": doc.reviewed_by or "",
		"reviewed_on": doc.reviewed_on,
		"notes": doc.notes or "",
	}


def _new_question() -> dict:
	current_branch = get_current_school_branch() or {}
	return {
		"name": None,
		"question_code": "",
		"ownership_scope": SCHOOL_BANK,
		"school_branch": current_branch.get("name") or "",
		"institution": current_branch.get("institution") or "",
		"program_offering": "",
		"student_group": "",
		"version_number": 1,
		"supersedes_question": "",
		"course": "",
		"course_label": "",
		"topic": "",
		"topic_label": "",
		"curriculum": "",
		"exam_body": "School Internal",
		"difficulty": "",
		"question_type": "Single Choice",
		"question_text": "",
		"options": [],
		"answer_key": "",
		"marking_guide": "",
		"default_mark": 1,
		"negative_mark": 0,
		"status": "Draft",
		"recommended_by": "",
		"recommended_on": None,
		"review_feedback": "",
		"reviewed_by": "",
		"reviewed_on": None,
		"notes": "",
	}


def _can_review(scope: str, public_access: dict) -> bool:
	if not can_review_questions(frappe.session.user):
		return False
	if scope == PLATFORM_BANK:
		return bool(public_access.get("capabilities", {}).get("author", {}).get("allowed"))
	return True


def _allowed_branch_names() -> set[str]:
	return {row.get("name") for row in get_allowed_school_branches() if row.get("name")}


def _academic_options(branch: str | None, program_offering: str | None = None) -> dict:
	if not branch:
		return {"offerings": [], "groups": [], "institution": None}
	if branch not in _allowed_branch_names():
		frappe.throw(_("The selected Branch is not available to your user."), frappe.PermissionError)
	institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
	offerings = frappe.get_list(
		"EduEdge Program Offering",
		filters={"school_branch": branch, "is_active": 1},
		fields=["name", "offering_title", "program", "academic_year", "academic_term", "school_branch", "institution"],
		order_by="academic_year desc, offering_title asc",
		limit_page_length=500,
	)
	if is_teacher_user():
		assigned = {
			row.program_offering
			for row in frappe.get_all(
				"EduEdge Instructor Assignment",
				filters={
					"instructor": ["in", _current_instructors()],
					"school_branch": branch,
					"enabled": 1,
				},
				fields=["program_offering", "valid_from", "valid_to"],
				limit_page_length=0,
			)
			if row.program_offering
		}
		offerings = [row for row in offerings if row.name in assigned]
	selected = next((row for row in offerings if row.name == program_offering), None) if program_offering else None
	if program_offering and not selected:
		frappe.throw(_("The selected Class is not available to your assignment context."), frappe.PermissionError)
	filters = {BRANCH_FIELD: branch, "disabled": 0}
	meta = frappe.get_meta("Student Group")
	if program_offering and meta.has_field(OFFERING_FIELD):
		filters[OFFERING_FIELD] = program_offering
	fields = ["name", "student_group_name", BRANCH_FIELD]
	for fieldname in ("eduedge_display_name", OFFERING_FIELD):
		if meta.has_field(fieldname):
			fields.append(fieldname)
	groups = frappe.get_list(
		"Student Group",
		filters=filters,
		fields=fields,
		order_by="student_group_name asc",
		limit_page_length=500,
	)
	return {"offerings": offerings, "groups": groups, "institution": institution, "selected_offering": selected}


def _current_instructors() -> list[str]:
	from eduedge.education.teaching_assignments import current_user_instructors
	return current_user_instructors()


def _builder_response(question: dict, public_access: dict, source_doc=None) -> dict:
	status = question.get("status") or "Draft"
	is_new = not question.get("name")
	if is_new:
		can_write = frappe.has_permission(QUESTION_DOCTYPE, "create")
	else:
		can_write = bool(source_doc and source_doc.has_permission("write"))
	if status not in EDITABLE_STATUSES:
		can_write = False
	current_branch = get_current_school_branch() or {}
	branch = question.get("school_branch") or current_branch.get("name")
	academic = _academic_options(branch, question.get("program_offering")) if question.get("ownership_scope") != PLATFORM_BANK else {"offerings": [], "groups": [], "institution": None}
	return {
		"question": question,
		"user": {
			"name": frappe.session.user,
			"full_name": frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user,
		},
		"tenant_name": current_branch.get("company") or "",
		"current_branch": current_branch,
		"allowed_branches": get_allowed_school_branches(),
		"offerings": academic.get("offerings", []),
		"groups": academic.get("groups", []),
		"scope_options": _question_scope_options(public_access, question.get("ownership_scope")),
		"question_types": list(QUESTION_TYPES),
		"difficulties": list(DIFFICULTIES),
		"exam_bodies": list(EXAM_BODIES),
		"permissions": {
			"can_write": bool(can_write),
			"can_review": _can_review(question.get("ownership_scope") or SCHOOL_BANK, public_access),
			"can_create_version": bool(
				question.get("name")
				and status in {"Approved", "Retired"}
				and frappe.has_permission(QUESTION_DOCTYPE, "create")
			),
			"can_open_technical_record": bool(frappe.has_permission(QUESTION_DOCTYPE, "read")),
			"is_assigned_teacher": is_teacher_user(),
		},
		"public_exam_access": public_access,
	}


@frappe.whitelist()
def get_question_builder_context(question: str | None = None) -> dict:
	public_access = get_public_exam_capability_summary(frappe.session.user)
	if question:
		_require_question_reader()
		doc = _require_readable_question(question)
		return _builder_response(_serialize_question(doc), public_access, doc)
	_require_question_author()
	return _builder_response(_new_question(), public_access)


@frappe.whitelist()
def get_question_academic_options(branch: str, program_offering: str | None = None) -> dict:
	_require_question_author()
	return _academic_options(branch, program_offering)


@frappe.whitelist()
def search_courses(
	txt: str | None = None,
	page_len: int = 20,
	branch: str | None = None,
	program_offering: str | None = None,
	student_group: str | None = None,
) -> list[dict]:
	_require_question_author()
	pattern = f"%{(txt or '').strip()}%"
	filters: dict = {}
	if program_offering:
		offering = frappe.db.get_value(
			"EduEdge Program Offering",
			program_offering,
			["program", "school_branch", "institution", "is_active"],
			as_dict=True,
		)
		if not offering or not offering.is_active or (branch and offering.school_branch != branch):
			frappe.throw(_("Select a valid Class / Programme Offering."), frappe.ValidationError)
		course_names = set(_program_courses(offering.program))
		if is_teacher_user():
			course_names &= assigned_courses(branch=offering.school_branch, program_offering=program_offering, student_group=student_group)
		filters["name"] = ["in", sorted(course_names)] if course_names else ["in", ["__none__"]]
	elif branch:
		institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
		filters[INSTITUTION_FIELD] = institution
		if is_teacher_user():
			course_names = assigned_courses(branch=branch)
			filters["name"] = ["in", sorted(course_names)] if course_names else ["in", ["__none__"]]
	rows = frappe.get_list(
		"Course",
		filters=filters,
		or_filters=[["name", "like", pattern], ["course_name", "like", pattern]],
		fields=["name", "course_name"],
		order_by="course_name asc",
		page_length=min(cint(page_len) or 20, 50),
	)
	return [{"value": row.name, "label": row.course_name or row.name} for row in rows]


def _program_courses(program: str | None) -> list[str]:
	if not program:
		return []
	return frappe.get_all(
		"Program Course",
		filters={"parent": program, "parenttype": "Program"},
		pluck="course",
		order_by="idx asc",
		limit_page_length=0,
	)


@frappe.whitelist()
def search_topics(
	course: str,
	txt: str | None = None,
	page_len: int = 50,
	program_offering: str | None = None,
	student_group: str | None = None,
) -> list[dict]:
	_require_question_reader()
	rows = course_topic_query(
		"Topic",
		txt or "",
		"name",
		0,
		min(cint(page_len) or 50, 100),
		{"course": course, "program_offering": program_offering, "student_group": student_group},
	)
	return [
		{"value": row[0], "label": row[1] or row[0], "description": row[2] or ""}
		for row in rows
	]


@frappe.whitelist()
def save_question(payload) -> dict:
	_require_question_author()
	values = _parse_payload(payload)
	name = (values.get("name") or "").strip()
	if name:
		doc = _require_readable_question(name)
		if not doc.has_permission("write"):
			frappe.throw(_("You are not permitted to edit this CBT question."), frappe.PermissionError)
		if doc.status not in EDITABLE_STATUSES:
			frappe.throw(_("Question content can be changed only while the question is Draft or Changes Requested."), frappe.ValidationError)
		if values.get("question_code") and values.get("question_code").strip().upper() != doc.question_code:
			frappe.throw(_("Question Code cannot be changed after the first save."), frappe.ValidationError)
	else:
		if not frappe.has_permission(QUESTION_DOCTYPE, "create"):
			frappe.throw(_("You are not permitted to create CBT questions."), frappe.PermissionError)
		doc = frappe.new_doc(QUESTION_DOCTYPE)
		doc.question_code = (values.get("question_code") or "").strip().upper()
	for fieldname in EDITABLE_FIELDS:
		if fieldname in values:
			doc.set(fieldname, values.get(fieldname))
	doc.set("options", [])
	for row in values.get("options") or []:
		doc.append("options", {"option_text": (row.get("option_text") or "").strip(), "is_correct": cint(row.get("is_correct"))})
	doc.status = values.get("status") or doc.status or "Draft"
	if doc.is_new():
		doc.insert()
	else:
		doc.save()
	public_access = get_public_exam_capability_summary(frappe.session.user)
	return _builder_response(_serialize_question(doc), public_access, doc)


def _next_version_code(source_code: str, version_number: int) -> str:
	base = re.sub(r"-V\d+(?:-\d+)?$", "", (source_code or "QUESTION").strip().upper())
	candidate = f"{base}-V{version_number}"
	sequence = 2
	while frappe.db.exists(QUESTION_DOCTYPE, candidate):
		candidate = f"{base}-V{version_number}-{sequence}"
		sequence += 1
	return candidate


@frappe.whitelist()
def create_question_version(question: str) -> dict:
	_require_question_author()
	source = _require_readable_question(question)
	if source.status not in {"Approved", "Retired"}:
		frappe.throw(_("Only an Approved or Retired question can start a new version."), frappe.ValidationError)
	if not frappe.has_permission(QUESTION_DOCTYPE, "create"):
		frappe.throw(_("You are not permitted to create a new question version."), frappe.PermissionError)
	version_number = cint(source.version_number) + 1
	doc = frappe.copy_doc(source)
	doc.name = None
	doc.question_code = _next_version_code(source.question_code, version_number)
	doc.version_number = version_number
	doc.supersedes_question = source.name
	doc.status = "Draft"
	doc.recommended_by = None
	doc.recommended_on = None
	doc.review_feedback = None
	doc.reviewed_by = None
	doc.reviewed_on = None
	doc.insert()
	public_access = get_public_exam_capability_summary(frappe.session.user)
	return _builder_response(_serialize_question(doc), public_access, doc)
