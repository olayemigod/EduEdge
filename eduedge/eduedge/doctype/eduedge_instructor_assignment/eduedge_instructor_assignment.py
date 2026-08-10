from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate, nowdate

from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.instructor_assignment_capabilities import CAPABILITY_FIELDS
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


IMMUTABLE_RESPONSIBILITY_FIELDS = (
    "instructor",
    "assignment_type",
    "assignment_scope",
    "school_branch",
    "program_offering",
    "student_group",
    "course",
    "valid_from",
)
LIFECYCLE_AUDIT_FIELDS = (
    "ended_on",
    "ended_by",
    "end_reason",
    "replaces_assignment",
    "replaced_by_assignment",
    "replacement_reason",
    "transferred_from_assignment",
    "transferred_to_assignment",
    "transfer_reason",
    "prepared_from_assignment",
    "preparation_reason",
)
CAPABILITY_AUDIT_FIELDS = (
    "capabilities_updated_on",
    "capabilities_updated_by",
    "capabilities_update_reason",
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
        self._validate_capability_state()
        self._validate_existing_responsibility()
        self._validate_lifecycle_audit()
        self._validate_duplicate()
        self._validate_primary_responsibility()
        self.assignment_title = self._build_title()

    def on_trash(self) -> None:
        if not bool(getattr(frappe.flags, "in_eduedge_assignment_delete", False)):
            frappe.throw(
                _(
                    "Instructor Assignments cannot be deleted directly. Use Delete Unused Assignment so EduEdge can prove that the future record has never started, has no lifecycle history, and is unreferenced."
                ),
                frappe.PermissionError,
            )

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
        before = self.get_doc_before_save()
        lifecycle_action = bool(getattr(frappe.flags, "in_eduedge_assignment_lifecycle", False))
        governed_disable = bool(
            before
            and lifecycle_action
            and int(before.enabled or 0) == 1
            and int(self.enabled or 0) == 0
        )
        if not instructor:
            frappe.throw(_("Select a valid Instructor."), frappe.ValidationError)
        if instructor.status != "Active" and not governed_disable:
            frappe.throw(_("Select an active Instructor."), frappe.ValidationError)
        frappe.get_doc("Instructor", self.instructor).check_permission("read")
        if governed_disable:
            # Disabling a future responsibility must remain possible when an Instructor
            # has since become inactive or Branch Eligibility has been withdrawn. It
            # narrows access rather than granting it and leaves Branch Eligibility alone.
            self.instructor_name = instructor.instructor_name
            return
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

    def _validate_capability_state(self) -> None:
        capability_values = {fieldname: cint(self.get(fieldname)) for fieldname in CAPABILITY_FIELDS}
        capability_action = bool(getattr(frappe.flags, "in_eduedge_assignment_capability_update", False))
        before = self.get_doc_before_save()

        if self.assignment_type not in COURSE_REQUIRED_TYPES and any(capability_values.values()):
            frappe.throw(
                _("Operational Subject capabilities can be granted only to Subject-bearing Instructor Assignments."),
                frappe.ValidationError,
            )
        if any(
            capability_values[fieldname]
            for fieldname in CAPABILITY_FIELDS
            if fieldname != "can_view_subject_content"
        ) and not capability_values["can_view_subject_content"]:
            frappe.throw(
                _("View Subject Content must be enabled before operational Subject capabilities can be granted."),
                frappe.ValidationError,
            )

        protected_fields = (*CAPABILITY_FIELDS, *CAPABILITY_AUDIT_FIELDS)
        if before and not capability_action:
            for fieldname in protected_fields:
                if not _same_value(before.get(fieldname), self.get(fieldname)):
                    frappe.throw(
                        _("Operational capability fields are maintained by EduEdge assignment capability actions."),
                        frappe.PermissionError,
                    )
        if not before and not capability_action and any(self.get(fieldname) for fieldname in protected_fields):
            frappe.throw(
                _("Operational capability fields are maintained by EduEdge assignment capability actions."),
                frappe.PermissionError,
            )

    def _validate_existing_responsibility(self) -> None:
        before = self.get_doc_before_save()
        if not before:
            return
        lifecycle_action = bool(getattr(frappe.flags, "in_eduedge_assignment_lifecycle", False))
        for fieldname in IMMUTABLE_RESPONSIBILITY_FIELDS:
            if _same_value(before.get(fieldname), self.get(fieldname)):
                continue
            frappe.throw(
                _(
                    "Existing Instructor Assignment responsibility cannot be edited in place. Use End, Replace, Transfer or Prepare Next Term / Session actions so history remains intact."
                ),
                frappe.ValidationError,
            )
        if not _same_value(before.get("valid_to"), self.get("valid_to")) and not lifecycle_action:
            frappe.throw(
                _("Use End Assignment to shorten an existing responsibility period."),
                frappe.ValidationError,
            )
        if not _same_value(before.get("enabled"), self.get("enabled")) and not lifecycle_action:
            frappe.throw(
                _("Use Disable Assignment or Re-enable Assignment so status changes are validated and audited."),
                frappe.PermissionError,
            )

    def _validate_lifecycle_audit(self) -> None:
        before = self.get_doc_before_save()
        lifecycle_action = bool(getattr(frappe.flags, "in_eduedge_assignment_lifecycle", False))
        if before and not lifecycle_action:
            for fieldname in LIFECYCLE_AUDIT_FIELDS:
                if not _same_value(before.get(fieldname), self.get(fieldname)):
                    frappe.throw(
                        _("Lifecycle audit fields are maintained by EduEdge assignment actions."),
                        frappe.PermissionError,
                    )
        if not before and not lifecycle_action and any(self.get(fieldname) for fieldname in LIFECYCLE_AUDIT_FIELDS):
            frappe.throw(
                _("Lifecycle audit fields are maintained by EduEdge assignment actions."),
                frappe.PermissionError,
            )
        if self.ended_on:
            if not self.ended_by or not str(self.end_reason or "").strip():
                frappe.throw(
                    _("Ended assignments require Ended By and End Reason audit values."),
                    frappe.ValidationError,
                )
            if not self.valid_to or getdate(self.valid_to) != getdate(self.ended_on):
                frappe.throw(
                    _("Ended On must match the final Valid To date."),
                    frappe.ValidationError,
                )

        if self.replaces_assignment and self.replaces_assignment == self.name:
            frappe.throw(_("An Instructor Assignment cannot replace itself."), frappe.ValidationError)
        if self.replaced_by_assignment and self.replaced_by_assignment == self.name:
            frappe.throw(_("An Instructor Assignment cannot be replaced by itself."), frappe.ValidationError)
        if self.replaces_assignment and not str(self.replacement_reason or "").strip():
            frappe.throw(
                _("Replacement assignments require a Replacement Reason."),
                frappe.ValidationError,
            )
        if self.replacement_reason and not self.replaces_assignment:
            frappe.throw(
                _("Replacement Reason requires a Replaces Assignment link."),
                frappe.ValidationError,
            )
        if self.replaced_by_assignment and not self.ended_on:
            frappe.throw(
                _("An assignment linked to a replacement successor must already be ended."),
                frappe.ValidationError,
            )

        if self.transferred_from_assignment and self.transferred_from_assignment == self.name:
            frappe.throw(_("An Instructor Assignment cannot transfer from itself."), frappe.ValidationError)
        if self.transferred_to_assignment and self.transferred_to_assignment == self.name:
            frappe.throw(_("An Instructor Assignment cannot transfer to itself."), frappe.ValidationError)
        if self.transferred_from_assignment and self.replaces_assignment:
            frappe.throw(
                _("An Instructor Assignment can have only one incoming lifecycle origin: Replace / Handover or Transfer."),
                frappe.ValidationError,
            )
        if self.transferred_to_assignment and self.replaced_by_assignment:
            frappe.throw(
                _("An Instructor Assignment can have only one outgoing lifecycle successor: Replace / Handover or Transfer."),
                frappe.ValidationError,
            )
        if self.transferred_from_assignment and not str(self.transfer_reason or "").strip():
            frappe.throw(
                _("Transferred assignments require a Transfer Reason."),
                frappe.ValidationError,
            )
        if self.transfer_reason and not self.transferred_from_assignment:
            frappe.throw(
                _("Transfer Reason requires a Transferred From Assignment link."),
                frappe.ValidationError,
            )
        if self.transferred_to_assignment and not self.ended_on:
            frappe.throw(
                _("An assignment linked to a transfer successor must already be ended."),
                frappe.ValidationError,
            )

        if self.prepared_from_assignment and self.prepared_from_assignment == self.name:
            frappe.throw(_("An Instructor Assignment cannot be prepared from itself."), frappe.ValidationError)
        if self.prepared_from_assignment and (self.replaces_assignment or self.transferred_from_assignment):
            frappe.throw(
                _("An Instructor Assignment can have only one incoming lifecycle origin: Replace / Handover, Transfer, or Next Period Preparation."),
                frappe.ValidationError,
            )
        if self.prepared_from_assignment and not str(self.preparation_reason or "").strip():
            frappe.throw(
                _("Prepared assignments require a Preparation Reason."),
                frappe.ValidationError,
            )
        if self.preparation_reason and not self.prepared_from_assignment:
            frappe.throw(
                _("Preparation Reason requires a Prepared From Assignment link."),
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


def _same_value(left, right) -> bool:
    return str(left or "") == str(right or "")


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
