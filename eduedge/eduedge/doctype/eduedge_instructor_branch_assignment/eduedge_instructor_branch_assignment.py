from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate, nowdate

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.people_fields import INSTRUCTOR_PRIMARY_BRANCH_FIELD
from eduedge.services.instructor_branch_governance import primary_branch


class EduEdgeInstructorBranchAssignment(Document):
    def validate(self) -> None:
        self._validate_identity()
        self._validate_instructor()
        self._validate_branch()
        self._lock_instructor_scope()
        self._validate_dates()
        self._validate_duplicate()
        self._validate_primary()

    def on_update(self) -> None:
        _sync_instructor_primary_branch(self.instructor)

    def on_trash(self) -> None:
        if not self.valid_from or getdate(self.valid_from) <= getdate(nowdate()):
            frappe.throw(
                _(
                    "Instructor Branch Eligibility that has started or has no future start date cannot be deleted. Disable or end the eligibility so Branch Governance history remains auditable."
                ),
                frappe.PermissionError,
            )
        if _has_linked_academic_responsibility(self):
            frappe.throw(
                _(
                    "Instructor Branch Eligibility with linked academic responsibilities cannot be deleted. Disable or end the eligibility and preserve the historical governance trail."
                ),
                frappe.PermissionError,
            )

    def after_delete(self) -> None:
        _sync_instructor_primary_branch(self.instructor)

    def _validate_identity(self) -> None:
        before = self.get_doc_before_save()
        if not before:
            return
        if before.instructor != self.instructor or before.school_branch != self.school_branch:
            frappe.throw(
                _(
                    "Existing Instructor Branch Eligibility identity cannot be changed. Delete only an unused future eligibility or create a new eligibility period for the correct Instructor and Branch."
                ),
                frappe.ValidationError,
            )

    def _validate_instructor(self) -> None:
        if not self.instructor:
            frappe.throw(_("Select an Instructor."), frappe.ValidationError)
        meta = frappe.get_meta("Instructor")
        fields = ["name", "instructor_name", "status"]
        if meta.has_field(INSTITUTION_FIELD):
            fields.append(INSTITUTION_FIELD)
        instructor = frappe.db.get_value("Instructor", self.instructor, fields, as_dict=True)
        if not instructor:
            frappe.throw(_("Select a valid Instructor."), frappe.ValidationError)
        if (
            cint(self.enabled)
            and instructor.status != "Active"
            and not self._is_narrowing_update()
        ):
            frappe.throw(
                _(
                    "Instructor Branch Eligibility can be enabled only for an active Instructor. "
                    "Existing historical eligibility may be shortened or disabled, but cannot be widened."
                ),
                frappe.ValidationError,
            )
        self._instructor_row = instructor

    def _validate_branch(self) -> None:
        if not self.school_branch:
            frappe.throw(_("Select a School Branch / Campus."), frappe.ValidationError)
        branch = frappe.db.get_value(
            "EduEdge School Branch",
            self.school_branch,
            ["name", "branch_name", "institution", "enabled"],
            as_dict=True,
        )
        if not branch:
            frappe.throw(_("Select a valid School Branch / Campus."), frappe.ValidationError)
        if (
            cint(self.enabled)
            and not cint(branch.enabled)
            and not self._is_narrowing_update()
        ):
            frappe.throw(
                _(
                    "Instructor Branch Eligibility can be enabled only for an enabled School Branch / Campus. "
                    "Existing historical eligibility may be shortened or disabled, but cannot be widened."
                ),
                frappe.ValidationError,
            )

        home_institution = (
            self._instructor_row.get(INSTITUTION_FIELD)
            if getattr(self, "_instructor_row", None)
            else None
        )
        if (
            cint(self.enabled)
            and not home_institution
            and not self._is_narrowing_update()
        ):
            frappe.throw(
                _(
                    "Set the Instructor's Home Institution before enabling or widening Branch Eligibility. "
                    "Legacy Instructor profiles must be classified before receiving new academic responsibilities."
                ),
                frappe.ValidationError,
            )
        if (
            cint(self.enabled)
            and not branch.institution
            and not self._is_narrowing_update()
        ):
            frappe.throw(
                _(
                    "The School Branch / Campus must belong to an Institution before Instructor Branch Eligibility can be enabled or widened."
                ),
                frappe.ValidationError,
            )
        if (
            cint(self.enabled)
            and home_institution
            and branch.institution
            and home_institution != branch.institution
            and not self._is_narrowing_update()
        ):
            frappe.throw(
                _(
                    "School Branch / Campus must belong to the Instructor's Home Institution. Cross-campus eligibility is allowed within the same Institution; cross-Institution eligibility is not."
                ),
                frappe.ValidationError,
            )
        self._branch_row = branch

    def _is_narrowing_update(self) -> bool:
        before = self.get_doc_before_save()
        if not before:
            return False
        if before.instructor != self.instructor or before.school_branch != self.school_branch:
            return False
        if not cint(self.enabled):
            return True
        if not cint(before.enabled):
            return False
        old_start = getdate(before.valid_from) if before.valid_from else getdate("1900-01-01")
        new_start = getdate(self.valid_from) if self.valid_from else getdate("1900-01-01")
        old_end = getdate(before.valid_to) if before.valid_to else getdate("2999-12-31")
        new_end = getdate(self.valid_to) if self.valid_to else getdate("2999-12-31")
        if new_start < old_start or new_end > old_end:
            return False
        if cint(self.is_primary) > cint(before.is_primary):
            return False
        return True

    def _lock_instructor_scope(self) -> None:
        # Serialize all eligibility writes for an Instructor so concurrent inserts
        # cannot bypass overlap or single-primary-period validation.
        frappe.db.sql(
            "select name from `tabInstructor` where name = %s for update",
            (self.instructor,),
        )

    def _validate_dates(self) -> None:
        if self.valid_from and self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
            frappe.throw(_("Valid To cannot be earlier than Valid From."), frappe.ValidationError)

    def _validate_duplicate(self) -> None:
        if not self.enabled:
            return
        rows = frappe.get_all(
            self.doctype,
            filters={
                "instructor": self.instructor,
                "school_branch": self.school_branch,
                "enabled": 1,
                "name": ["!=", self.name or ""],
            },
            fields=["name", "valid_from", "valid_to"],
            limit_page_length=0,
        )
        for row in rows:
            if _date_ranges_overlap(self.valid_from, self.valid_to, row.valid_from, row.valid_to):
                frappe.throw(
                    _(
                        "Instructor {0} already has overlapping Branch eligibility for School Branch / Campus {1}."
                    ).format(self.instructor, self.school_branch),
                    frappe.DuplicateEntryError,
                )

    def _validate_primary(self) -> None:
        if not self.is_primary or not self.enabled:
            return
        rows = frappe.get_all(
            self.doctype,
            filters={
                "instructor": self.instructor,
                "is_primary": 1,
                "enabled": 1,
                "name": ["!=", self.name or ""],
            },
            fields=["name", "school_branch", "valid_from", "valid_to"],
            limit_page_length=0,
        )
        for row in rows:
            if _date_ranges_overlap(self.valid_from, self.valid_to, row.valid_from, row.valid_to):
                frappe.throw(
                    _(
                        "Instructor {0} already has a primary School Branch assignment for this period."
                    ).format(self.instructor),
                    frappe.ValidationError,
                )


def _has_linked_academic_responsibility(doc) -> bool:
    if not frappe.db.exists("DocType", "EduEdge Instructor Assignment"):
        return False
    rows = frappe.get_all(
        "EduEdge Instructor Assignment",
        filters={
            "instructor": doc.instructor,
            "school_branch": doc.school_branch,
        },
        fields=["name", "valid_from", "valid_to"],
        limit_page_length=0,
    )
    return any(
        _date_ranges_overlap(doc.valid_from, doc.valid_to, row.valid_from, row.valid_to)
        for row in rows
    )


def _sync_instructor_primary_branch(instructor: str | None) -> None:
    name = str(instructor or "").strip()
    if not name or not frappe.db.exists("Instructor", name):
        return
    meta = frappe.get_meta("Instructor")
    if not meta.has_field(INSTRUCTOR_PRIMARY_BRANCH_FIELD):
        return
    governed_primary = primary_branch(name)
    current = frappe.db.get_value("Instructor", name, INSTRUCTOR_PRIMARY_BRANCH_FIELD)
    if (current or None) == (governed_primary or None):
        return
    frappe.db.set_value(
        "Instructor",
        name,
        INSTRUCTOR_PRIMARY_BRANCH_FIELD,
        governed_primary,
        update_modified=False,
    )


def _date_ranges_overlap(start_a=None, end_a=None, start_b=None, end_b=None) -> bool:
    minimum = getdate("1900-01-01")
    maximum = getdate("2999-12-31")
    a_start = getdate(start_a) if start_a else minimum
    a_end = getdate(end_a) if end_a else maximum
    b_start = getdate(start_b) if start_b else minimum
    b_end = getdate(end_b) if end_b else maximum
    return a_start <= b_end and b_start <= a_end
