from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class EduEdgeInstructorBranchAssignment(Document):
    def validate(self) -> None:
        self._validate_branch()
        self._validate_dates()
        self._validate_duplicate()
        self._validate_primary()

    def _validate_branch(self) -> None:
        if not frappe.db.get_value("EduEdge School Branch", self.school_branch, "enabled"):
            frappe.throw(_("Select an enabled School Branch / Campus."), frappe.ValidationError)

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


def _date_ranges_overlap(start_a=None, end_a=None, start_b=None, end_b=None) -> bool:
    minimum = getdate("1900-01-01")
    maximum = getdate("2999-12-31")
    a_start = getdate(start_a) if start_a else minimum
    a_end = getdate(end_a) if end_a else maximum
    b_start = getdate(start_b) if start_b else minimum
    b_end = getdate(end_b) if end_b else maximum
    return a_start <= b_end and b_start <= a_end
