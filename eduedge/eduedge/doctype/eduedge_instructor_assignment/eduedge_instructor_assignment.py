from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access
from eduedge.education.teaching_assignments import (
    ACADEMIC_ASSIGNMENT_SCOPES,
    CLASS_ARM_SCOPE,
    CLASS_RESPONSIBILITY_TYPES,
    CLASS_SCOPE,
    COURSE_REQUIRED_TYPES,
    LEGACY_SUBJECT_TEACHER,
    SUBJECT_INSTRUCTOR,
    UNIQUE_PRIMARY_ASSIGNMENT_TYPES,
)


class EduEdgeInstructorAssignment(Document):
    def validate(self) -> None:
        self.assignment_scope = self.assignment_scope or (
            CLASS_ARM_SCOPE if self.student_group else CLASS_SCOPE
        )
        self.assignment_type = (
            SUBJECT_INSTRUCTOR
            if self.assignment_type == LEGACY_SUBJECT_TEACHER
            else self.assignment_type
        )
        if self.assignment_scope not in ACADEMIC_ASSIGNMENT_SCOPES:
            frappe.throw(_("Select a valid Assignment Scope."), frappe.ValidationError)
        self._validate_dates()
        self._apply_offering_context()
        self._validate_group_context()
        self._validate_instructor_context()
        self._validate_assignment_type_scope()
        self._validate_course_context()
        self._validate_duplicate()
        self._validate_primary_responsibility()
        self.assignment_title = self._build_title()

    def _validate_dates(self) -> None:
        if self.valid_from and self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
            frappe.throw(_("Valid To cannot be earlier than Valid From."), frappe.ValidationError)

    def _apply_offering_context(self) -> None:
        if not self.program_offering:
            frappe.throw(_("Select a Class / Programme Offering."), frappe.ValidationError)
        offering = frappe.db.get_value(
            "EduEdge Program Offering",
            self.program_offering,
            [
                "name",
                "institution",
                "school_branch",
                "program",
                "academic_year",
                "academic_term",
                "is_active",
            ],
            as_dict=True,
        )
        if not offering or not offering.is_active:
            frappe.throw(_("Select an active Class / Programme Offering."), frappe.ValidationError)
        assert_branch_access(offering.school_branch)
        if self.school_branch and self.school_branch != offering.school_branch:
            frappe.throw(
                _("Class / Programme Offering must belong to the selected Branch."),
                frappe.ValidationError,
            )
        if self.institution and self.institution != offering.institution:
            frappe.throw(
                _("Class / Programme Offering must belong to the selected Institution."),
                frappe.ValidationError,
            )
        self.school_branch = offering.school_branch
        self.institution = offering.institution
        self.academic_year = offering.academic_year
        self.academic_term = offering.academic_term or None
        self._offering_program = offering.program

    def _validate_group_context(self) -> None:
        if self.assignment_scope == CLASS_SCOPE:
            self.student_group = None
            return
        if not self.student_group:
            frappe.throw(
                _("Select a Class Arm / Student Group for a Class Arm assignment."),
                frappe.ValidationError,
            )
        meta = frappe.get_meta("Student Group")
        fields = [
            "name",
            "program",
            "academic_year",
            "academic_term",
            "disabled",
            BRANCH_FIELD,
        ]
        if meta.has_field(OFFERING_FIELD):
            fields.append(OFFERING_FIELD)
        group = frappe.db.get_value("Student Group", self.student_group, fields, as_dict=True)
        if not group or group.disabled:
            frappe.throw(_("Select an active Class Arm / Student Group."), frappe.ValidationError)
        if group.get(BRANCH_FIELD) != self.school_branch:
            frappe.throw(
                _("Class Arm / Student Group must belong to the selected Branch."),
                frappe.ValidationError,
            )
        if group.program and group.program != self._offering_program:
            frappe.throw(
                _("Class Arm / Student Group Programme must match the Class / Programme Offering."),
                frappe.ValidationError,
            )
        if group.academic_year and group.academic_year != self.academic_year:
            frappe.throw(
                _("Class Arm / Student Group Academic Session must match the Class / Programme Offering."),
                frappe.ValidationError,
            )
        if group.academic_term and group.academic_term != self.academic_term:
            frappe.throw(
                _("Class Arm / Student Group Term must match the Class / Programme Offering."),
                frappe.ValidationError,
            )
        if (
            meta.has_field(OFFERING_FIELD)
            and group.get(OFFERING_FIELD)
            and group.get(OFFERING_FIELD) != self.program_offering
        ):
            frappe.throw(
                _("Class Arm / Student Group must belong to the selected Class / Programme Offering."),
                frappe.ValidationError,
            )

    def _validate_instructor_context(self) -> None:
        if not self.instructor:
            frappe.throw(_("Select an Instructor."), frappe.ValidationError)
        instructor = frappe.db.get_value(
            "Instructor",
            self.instructor,
            ["name", "instructor_name", "status"],
            as_dict=True,
        )
        if not instructor or instructor.status != "Active":
            frappe.throw(_("Select an active Instructor."), frappe.ValidationError)
        frappe.get_doc("Instructor", self.instructor).check_permission("read")
        has_explicit_access = _has_branch_eligibility(
            self.instructor,
            self.school_branch,
            self.valid_from or nowdate(),
            self.valid_to,
        )
        # Historical guidance: Save through Instructor Assignments or add Branch eligibility first.
        if not has_explicit_access and not getattr(
            frappe.flags,
            "in_eduedge_assignment_matrix_save",
            False,
        ):
            frappe.throw(
                _(
                    "Instructor has no explicit Branch Access record. Save through Instructor Assignments, which validates the exact Class responsibility without widening Branch access dates."
                ),
                frappe.ValidationError,
            )
        self.instructor_name = instructor.instructor_name

    def _validate_assignment_type_scope(self) -> None:
        if self.assignment_type in {"Class Teacher", "Form Teacher"} and self.assignment_scope != CLASS_ARM_SCOPE:
            frappe.throw(
                _("{0} must be assigned to a specific Class Arm.").format(self.assignment_type),
                frappe.ValidationError,
            )
        if self.assignment_type == "Head of Class / Level" and self.assignment_scope != CLASS_SCOPE:
            frappe.throw(
                _("Head of Class / Level must use Class / Programme Offering scope."),
                frappe.ValidationError,
            )
        if self.assignment_type in CLASS_RESPONSIBILITY_TYPES and self.course:
            frappe.throw(
                _(
                    "{0} is a class responsibility and cannot carry a Subject. Create a separate Subject Instructor assignment."
                ).format(self.assignment_type),
                frappe.ValidationError,
            )

    def _validate_course_context(self) -> None:
        if self.assignment_type in COURSE_REQUIRED_TYPES and not self.course:
            frappe.throw(
                _("Subject / Course is required for this assignment type."),
                frappe.ValidationError,
            )
        if not self.course:
            return
        course = frappe.db.get_value(
            "Course",
            self.course,
            ["name", INSTITUTION_FIELD],
            as_dict=True,
        )
        if not course:
            frappe.throw(_("Select a valid Subject / Course."), frappe.ValidationError)
        if course.get(INSTITUTION_FIELD) and course.get(INSTITUTION_FIELD) != self.institution:
            frappe.throw(
                _("Subject / Course must belong to the selected Institution."),
                frappe.ValidationError,
            )
        if self._offering_program and not frappe.db.exists(
            "Program Course",
            {
                "parent": self._offering_program,
                "parenttype": "Program",
                "course": self.course,
            },
        ):
            frappe.throw(
                _("Subject / Course is not configured for the selected Class / Programme Offering."),
                frappe.ValidationError,
            )

    def _validate_duplicate(self) -> None:
        if not self.enabled:
            return
        variants = [self.assignment_type]
        if self.assignment_type == SUBJECT_INSTRUCTOR:
            variants.append(LEGACY_SUBJECT_TEACHER)
        filters = {
            "instructor": self.instructor,
            "school_branch": self.school_branch,
            "program_offering": self.program_offering,
            "assignment_scope": self.assignment_scope,
            "assignment_type": ["in", variants],
            "enabled": 1,
            "name": ["!=", self.name or ""],
        }
        rows = frappe.get_all(
            self.doctype,
            filters=filters,
            fields=["name", "student_group", "course", "valid_from", "valid_to"],
            limit_page_length=0,
        )
        for row in rows:
            if (row.student_group or "") != (self.student_group or ""):
                continue
            if (row.course or "") != (self.course or ""):
                continue
            if _date_ranges_overlap(self.valid_from, self.valid_to, row.valid_from, row.valid_to):
                frappe.throw(
                    _("An overlapping active Instructor Assignment already exists."),
                    frappe.DuplicateEntryError,
                )

    def _validate_primary_responsibility(self) -> None:
        if not self.enabled or self.assignment_type not in UNIQUE_PRIMARY_ASSIGNMENT_TYPES:
            return
        filters = {
            "instructor": ["!=", self.instructor],
            "school_branch": self.school_branch,
            "program_offering": self.program_offering,
            "assignment_scope": self.assignment_scope,
            "assignment_type": self.assignment_type,
            "enabled": 1,
            "name": ["!=", self.name or ""],
        }
        if self.assignment_scope == CLASS_ARM_SCOPE:
            filters["student_group"] = self.student_group
        rows = frappe.get_all(
            self.doctype,
            filters=filters,
            fields=["name", "instructor", "valid_from", "valid_to"],
            limit_page_length=0,
        )
        for row in rows:
            if _date_ranges_overlap(self.valid_from, self.valid_to, row.valid_from, row.valid_to):
                frappe.throw(
                    _("{0} already has another active primary Instructor ({1}).").format(
                        self.assignment_type,
                        row.instructor,
                    ),
                    frappe.ValidationError,
                )

    def _build_title(self) -> str:
        target = _assignment_target_label(self.assignment_scope, self.program_offering, self.student_group)
        parts = [self.instructor_name or self.instructor, self.assignment_type, target]
        if self.course:
            parts.append(_course_label(self.course))
        return " · ".join(value for value in parts if value)


def _assignment_target_label(
    assignment_scope: str | None,
    program_offering: str | None,
    student_group: str | None,
) -> str:
    if assignment_scope == CLASS_SCOPE:
        return (
            frappe.db.get_value("EduEdge Program Offering", program_offering, "offering_title")
            if program_offering
            else ""
        ) or (program_offering or "")
    if not student_group:
        return ""
    meta = frappe.get_meta("Student Group")
    fields = ["student_group_name"]
    if meta.has_field("eduedge_display_name"):
        fields.insert(0, "eduedge_display_name")
    row = frappe.db.get_value("Student Group", student_group, fields, as_dict=True) or {}
    return row.get("eduedge_display_name") or row.get("student_group_name") or student_group


def _course_label(course: str | None) -> str:
    if not course:
        return ""
    return frappe.db.get_value("Course", course, "course_name") or course


def _has_branch_eligibility(instructor: str, branch: str, start_date, end_date=None) -> bool:
    rows = frappe.get_all(
        "EduEdge Instructor Branch Assignment",
        filters={"instructor": instructor, "school_branch": branch, "enabled": 1},
        fields=["valid_from", "valid_to"],
        limit_page_length=0,
    )
    return any(
        _date_ranges_overlap(start_date, end_date, row.valid_from, row.valid_to)
        for row in rows
    )


def _date_ranges_overlap(start_a=None, end_a=None, start_b=None, end_b=None) -> bool:
    minimum = getdate("1900-01-01")
    maximum = getdate("2999-12-31")
    a_start = getdate(start_a) if start_a else minimum
    a_end = getdate(end_a) if end_a else maximum
    b_start = getdate(start_b) if start_b else minimum
    b_end = getdate(end_b) if end_b else maximum
    return a_start <= b_end and b_start <= a_end
