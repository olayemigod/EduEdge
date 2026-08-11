from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate

from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access
from eduedge.education.teaching_assignments import CLASS_ARM_SCOPE, CLASS_SCOPE, COURSE_REQUIRED_TYPES

LESSON_PLAN_ACTION_FLAG = "in_eduedge_lesson_plan_action"
LESSON_PLAN_STATUSES = {"Draft", "Submitted", "Approved", "Returned"}

PROTECTED_WORKFLOW_FIELDS = (
    "status",
    "prepared_by",
    "submitted_by",
    "submitted_on",
    "reviewed_by",
    "reviewed_on",
    "review_comment",
    "return_reason",
    "instructor_assignment",
    "scheme_version",
    "scheme_title_snapshot",
    "offering_title_snapshot",
    "student_group_name_snapshot",
    "course_name_snapshot",
    "topic_name_snapshot",
    "learning_objective_snapshot",
)


def _group_belongs_to_offering(student_group: str, offering: str, branch: str) -> bool:
    if not student_group:
        return True
    meta = frappe.get_meta("Student Group")
    fields = ["name", BRANCH_FIELD]
    if meta.has_field(OFFERING_FIELD):
        fields.append(OFFERING_FIELD)
    row = frappe.db.get_value("Student Group", student_group, fields, as_dict=True)
    if not row or row.get(BRANCH_FIELD) != branch:
        return False
    if meta.has_field(OFFERING_FIELD) and row.get(OFFERING_FIELD):
        return row.get(OFFERING_FIELD) == offering
    offering_row = frappe.db.get_value(
        "EduEdge Program Offering",
        offering,
        ["program", "academic_year", "academic_term"],
        as_dict=True,
    )
    group_row = frappe.db.get_value(
        "Student Group",
        student_group,
        ["program", "academic_year", "academic_term"],
        as_dict=True,
    )
    if not offering_row or not group_row:
        return False
    return bool(
        group_row.program == offering_row.program
        and group_row.academic_year == offering_row.academic_year
        and (not offering_row.academic_term or group_row.academic_term == offering_row.academic_term)
    )


def _scheme_item(scheme, reference: str):
    value = str(reference or "").strip()
    for row in scheme.get("items") or []:
        if row.name == value:
            return row
    return None


def resolve_lesson_instructor_assignment(
    *,
    instructor: str,
    school_branch: str,
    program_offering: str,
    student_group: str | None,
    course: str,
    lesson_date,
) -> dict:
    reference_date = getdate(lesson_date)
    rows = frappe.get_all(
        "EduEdge Instructor Assignment",
        filters={
            "instructor": instructor,
            "school_branch": school_branch,
            "program_offering": program_offering,
            "course": course,
            "assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)],
            "enabled": 1,
        },
        fields=[
            "name",
            "assignment_title",
            "assignment_type",
            "assignment_scope",
            "student_group",
            "valid_from",
            "valid_to",
        ],
        order_by="assignment_scope asc, valid_from desc, modified desc",
        limit_page_length=100,
    )
    for row in rows:
        scope = row.assignment_scope or CLASS_ARM_SCOPE
        if scope == CLASS_SCOPE:
            pass
        elif scope == CLASS_ARM_SCOPE and student_group and row.student_group == student_group:
            pass
        else:
            continue
        if row.valid_from and getdate(row.valid_from) > reference_date:
            continue
        if row.valid_to and getdate(row.valid_to) < reference_date:
            continue
        return dict(row)
    frappe.throw(
        _(
            "Instructor {0} has no effective Subject Instructor Assignment for this Branch, Class, Class Arm, Subject and Lesson Date."
        ).format(instructor),
        frappe.ValidationError,
    )


def snapshot_lesson_plan_context(doc) -> None:
    scheme = frappe.get_doc("EduEdge Scheme of Work", doc.scheme_of_work)
    item = _scheme_item(scheme, doc.scheme_item_reference)
    if not item:
        frappe.throw(_("The selected Scheme item no longer belongs to this Scheme of Work."), frappe.ValidationError)
    doc.scheme_title_snapshot = scheme.scheme_title or scheme.name
    doc.offering_title_snapshot = (
        scheme.offering_title_snapshot
        or frappe.db.get_value("EduEdge Program Offering", doc.program_offering, "offering_title")
        or doc.program_offering
    )
    doc.student_group_name_snapshot = ""
    if doc.student_group:
        doc.student_group_name_snapshot = (
            frappe.db.get_value("Student Group", doc.student_group, "eduedge_display_name")
            if frappe.get_meta("Student Group").has_field("eduedge_display_name")
            else ""
        ) or frappe.db.get_value("Student Group", doc.student_group, "student_group_name") or doc.student_group
    doc.course_name_snapshot = frappe.db.get_value("Course", doc.course, "course_name") or doc.course
    doc.topic_name_snapshot = item.topic_name_snapshot or frappe.db.get_value("Topic", item.topic, "topic_name") or item.topic
    doc.learning_objective_snapshot = item.learning_objective or ""


class EduEdgeLessonPlan(Document):
    def validate(self):
        self._validate_status()
        self._resolve_scheme_context()
        self._validate_lesson_date()
        self._resolve_teaching_assignment()
        self._validate_duplicate()
        self._set_title()
        if self.is_new() and not self.prepared_by:
            self.prepared_by = frappe.session.user
        self._protect_workflow_fields()

    def _validate_status(self):
        if self.status not in LESSON_PLAN_STATUSES:
            frappe.throw(_("Invalid Lesson Plan status."), frappe.ValidationError)
        if cint(self.duration_minutes or 0) <= 0:
            frappe.throw(_("Lesson duration must be greater than zero minutes."), frappe.ValidationError)

    def _resolve_scheme_context(self):
        if not self.scheme_of_work:
            frappe.throw(_("Select an approved Scheme of Work."), frappe.ValidationError)
        scheme = frappe.get_doc("EduEdge Scheme of Work", self.scheme_of_work)
        if scheme.status != "Approved":
            frappe.throw(_("Lesson Plans must be prepared from an Approved Scheme of Work."), frappe.ValidationError)
        item = _scheme_item(scheme, self.scheme_item_reference)
        if not item:
            frappe.throw(_("Select a valid item from the approved Scheme of Work."), frappe.ValidationError)
        assert_branch_access(scheme.school_branch)
        self.institution = scheme.institution
        self.school_branch = scheme.school_branch
        self.program_offering = scheme.program_offering
        self.course = scheme.course
        self.academic_year = scheme.academic_year
        self.academic_term = scheme.academic_term
        self.scheme_version = cint(scheme.version_no)
        if scheme.student_group:
            if self.student_group and self.student_group != scheme.student_group:
                frappe.throw(_("The selected Class Arm does not match the approved Scheme of Work."), frappe.ValidationError)
            self.student_group = scheme.student_group
        elif self.student_group and not _group_belongs_to_offering(
            self.student_group, self.program_offering, self.school_branch
        ):
            frappe.throw(_("The selected Class Arm does not belong to the Scheme's Class / Programme Offering."), frappe.ValidationError)
        self._scheme = scheme
        self._scheme_item_row = item

    def _validate_lesson_date(self):
        if not self.lesson_date:
            frappe.throw(_("Select the Lesson Date."), frappe.ValidationError)
        lesson_date = getdate(self.lesson_date)
        start = getdate(self._scheme.period_start_date) if self._scheme.period_start_date else None
        end = getdate(self._scheme.period_end_date) if self._scheme.period_end_date else None
        if start and lesson_date < start:
            frappe.throw(_("Lesson Date cannot precede the Scheme academic period."), frappe.ValidationError)
        if end and lesson_date > end:
            frappe.throw(_("Lesson Date cannot extend beyond the Scheme academic period."), frappe.ValidationError)

    def _resolve_teaching_assignment(self):
        if not self.instructor:
            frappe.throw(_("Select the Instructor responsible for this Lesson Plan."), frappe.ValidationError)
        assignment = resolve_lesson_instructor_assignment(
            instructor=self.instructor,
            school_branch=self.school_branch,
            program_offering=self.program_offering,
            student_group=self.student_group,
            course=self.course,
            lesson_date=self.lesson_date,
        )
        self.instructor_assignment = assignment["name"]

    def _validate_duplicate(self):
        filters = {
            "instructor": self.instructor,
            "school_branch": self.school_branch,
            "program_offering": self.program_offering,
            "course": self.course,
            "lesson_date": self.lesson_date,
            "scheme_item_reference": self.scheme_item_reference,
            "period_label": self.period_label or "",
        }
        if self.student_group:
            filters["student_group"] = self.student_group
        else:
            filters["student_group"] = ["is", "not set"]
        existing = frappe.get_all("EduEdge Lesson Plan", filters=filters, pluck="name", limit_page_length=2)
        existing = [name for name in existing if name != self.name]
        if existing:
            frappe.throw(
                _("A Lesson Plan already exists for this Instructor, Class, Subject, Scheme item, Lesson Date and Period / Slot."),
                frappe.ValidationError,
            )

    def _set_title(self):
        instructor_name = frappe.db.get_value("Instructor", self.instructor, "instructor_name") or self.instructor
        offering = frappe.db.get_value("EduEdge Program Offering", self.program_offering, "offering_title") or self.program_offering
        course = frappe.db.get_value("Course", self.course, "course_name") or self.course
        topic = self._scheme_item_row.topic_name_snapshot or frappe.db.get_value("Topic", self._scheme_item_row.topic, "topic_name") or self._scheme_item_row.topic
        group = ""
        if self.student_group:
            group = frappe.db.get_value("Student Group", self.student_group, "student_group_name") or self.student_group
        parts = [instructor_name, offering]
        if group:
            parts.append(group)
        parts.extend([course, topic, str(self.lesson_date)])
        if self.period_label:
            parts.append(self.period_label)
        self.lesson_plan_title = " · ".join(str(value) for value in parts if value)

    def _protect_workflow_fields(self):
        if self.is_new() or getattr(frappe.flags, LESSON_PLAN_ACTION_FLAG, False):
            return
        before = self.get_doc_before_save()
        if not before:
            return
        if before.status == "Approved":
            frappe.throw(_("Approved Lesson Plans are immutable academic history."), frappe.ValidationError)
        if before.status == "Submitted":
            frappe.throw(_("Submitted Lesson Plans are read-only until Academic Review returns or approves them."), frappe.ValidationError)
        for fieldname in PROTECTED_WORKFLOW_FIELDS:
            if self.get(fieldname) != before.get(fieldname):
                frappe.throw(_("Lesson Plan workflow fields can only change through governed Lesson Plan actions."), frappe.ValidationError)

    def on_trash(self):
        if self.status != "Draft" or self.submitted_on:
            frappe.throw(_("Submitted, Returned or Approved Lesson Plans are retained as academic history and cannot be deleted."), frappe.ValidationError)
