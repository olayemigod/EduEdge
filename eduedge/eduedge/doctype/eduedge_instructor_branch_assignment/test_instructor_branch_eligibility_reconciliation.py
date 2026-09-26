from __future__ import annotations

from unittest.mock import patch

import frappe
from education.education.test_utils import before_tests
from frappe.tests.utils import FrappeTestCase

from eduedge.api.class_arms import save_class_arm
from eduedge.api.instructor_branch_eligibility import (
    disable_unused_instructor_branch_eligibility,
    get_instructor_branch_eligibility_review,
)
from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.people_fields import (
    INSTRUCTOR_PRIMARY_BRANCH_FIELD,
    reconcile_instructor_primary_branches,
)
from eduedge.services.academic_calendar import ensure_institution_calendar


class TestInstructorBranchEligibilityReconciliation(FrappeTestCase):
    """Database-backed persona and history-safety coverage for Branch Eligibility review."""

    def setUp(self) -> None:
        before_tests()
        frappe.set_user("Administrator")
        self.suffix = frappe.generate_hash(length=8).upper()
        self.company = "_Test Company"
        self.settings = frappe.get_single("EduEdge Settings")
        self.original_enforcement = self.settings.get("enable_user_branch_access_enforcement")
        self.settings.enable_user_branch_access_enforcement = 1
        self.settings.save(ignore_permissions=True)

    def tearDown(self) -> None:
        frappe.set_user("Administrator")
        settings = frappe.get_single("EduEdge Settings")
        settings.enable_user_branch_access_enforcement = self.original_enforcement or 0
        settings.save(ignore_permissions=True)

    def _insert(self, doctype: str, **values):
        return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)

    def _make_institution(self, label: str):
        return self._insert(
            "EduEdge Institution",
            institution_name=f"QA {label} School {self.suffix}",
            institution_code=f"QA{label[:4].upper()}{self.suffix}",
            company=self.company,
            institution_type="PRIMARY",
            enabled=1,
        )

    def _make_branch(self, institution, label: str):
        return self._insert(
            "EduEdge School Branch",
            branch_name=f"QA {label} Campus {self.suffix}",
            branch_code=f"QA{label.replace(' ', '').upper()[:8]}{self.suffix}",
            company=self.company,
            institution=institution.name,
            enabled=1,
        )

    def _make_instructor(self, institution, label: str):
        return self._insert(
            "Instructor",
            instructor_name=f"QA {label} Instructor {self.suffix}",
            status="Active",
            **{INSTITUTION_FIELD: institution.name},
        )

    def _make_user(self, role: str, label: str):
        email = f"qa-{label.lower().replace(' ', '-')}-{self.suffix.lower()}@example.com"
        user = self._insert(
            "User",
            email=email,
            first_name=f"QA {label}",
            enabled=1,
            user_type="System User",
            send_welcome_email=0,
            roles=[{"role": role}],
        )
        frappe.clear_cache(user=user.name)
        return user

    def _grant_branch(self, user, branch):
        return self._insert(
            "EduEdge User Branch Access",
            user=user.name,
            branch_role="Other",
            access_scope="Branch",
            school_branch=branch.name,
            enabled=1,
            can_switch_branch=1,
        )

    def _make_supported_assignment(self, instructor, institution, branch):
        year = self._insert(
            "Academic Year",
            academic_year_name=f"QA Eligibility {self.suffix}",
            year_start_date="2094-09-01",
            year_end_date="2095-08-31",
        )
        self._insert(
            "Academic Term",
            academic_year=year.name,
            term_name=f"QA Eligibility Term {self.suffix}",
            term_start_date="2094-09-01",
            term_end_date="2095-08-31",
        )
        ensure_institution_calendar(institution.name, year.name)
        department = self._insert(
            "Department",
            department_name=f"QA Eligibility Section {self.suffix}",
            company=self.company,
            is_group=0,
            **{INSTITUTION_FIELD: institution.name},
        )
        program = self._insert(
            "Program",
            program_name=f"QA Eligibility Class {self.suffix}",
            department=department.name,
            **{INSTITUTION_FIELD: institution.name},
        )
        offering = self._insert(
            "EduEdge Program Offering",
            school_branch=branch.name,
            program=program.name,
            academic_year=year.name,
            offering_title=f"QA Eligibility Intake {self.suffix}",
            offering_code=f"QA-ELIG-{self.suffix}",
            study_mode="Full-Time",
            delivery_mode="Onsite",
            is_active=1,
        )
        class_arm = save_class_arm(
            display_name=f"QA Eligibility Class Arm {self.suffix}",
            branch=branch.name,
            offering=offering.name,
            group_based_on="Batch",
            students=[],
        )
        return self._insert(
            "EduEdge Instructor Assignment",
            instructor=instructor.name,
            assignment_type="Class Teacher",
            assignment_scope="Class Arm",
            institution=institution.name,
            school_branch=branch.name,
            program_offering=offering.name,
            student_group=class_arm["name"],
            enabled=1,
        )

    def test_dated_primary_branch_mirror_rolls_forward_and_expires(self):
        institution = self._make_institution("Rollover")
        branch_one = self._make_branch(institution, "January Primary")
        branch_two = self._make_branch(institution, "February Primary")
        instructor = self._make_instructor(institution, "Rollover")

        self._insert(
            "EduEdge Instructor Branch Assignment",
            instructor=instructor.name,
            school_branch=branch_one.name,
            enabled=1,
            is_primary=1,
            valid_from="2099-01-01",
            valid_to="2099-01-31",
        )
        self._insert(
            "EduEdge Instructor Branch Assignment",
            instructor=instructor.name,
            school_branch=branch_two.name,
            enabled=1,
            is_primary=1,
            valid_from="2099-02-01",
            valid_to="2099-02-28",
        )

        with patch("eduedge.education.people_fields.nowdate", return_value="2099-01-15"):
            january = reconcile_instructor_primary_branches()
            self.assertGreaterEqual(january["updated"], 1)
            self.assertEqual(
                frappe.db.get_value("Instructor", instructor.name, INSTRUCTOR_PRIMARY_BRANCH_FIELD),
                branch_one.name,
            )
            rerun = reconcile_instructor_primary_branches()
            self.assertEqual(rerun["updated"], 0)

        with patch("eduedge.education.people_fields.nowdate", return_value="2099-02-15"):
            reconcile_instructor_primary_branches()
            self.assertEqual(
                frappe.db.get_value("Instructor", instructor.name, INSTRUCTOR_PRIMARY_BRANCH_FIELD),
                branch_two.name,
            )

        with patch("eduedge.education.people_fields.nowdate", return_value="2099-03-15"):
            reconcile_instructor_primary_branches()
            self.assertIsNone(
                frappe.db.get_value("Instructor", instructor.name, INSTRUCTOR_PRIMARY_BRANCH_FIELD)
            )

        self.assertEqual(
            frappe.db.get_value("Instructor", instructor.name, INSTITUTION_FIELD),
            institution.name,
        )

    def test_persona_scoped_review_and_history_safe_cleanup(self):
        institution_a = self._make_institution("Alpha")
        branch_a1 = self._make_branch(institution_a, "Alpha One")
        branch_a2 = self._make_branch(institution_a, "Alpha Two")
        institution_b = self._make_institution("Beta")
        branch_b1 = self._make_branch(institution_b, "Beta One")

        instructor_a = self._make_instructor(institution_a, "Alpha")
        instructor_b = self._make_instructor(institution_b, "Beta")

        primary_supported = self._insert(
            "EduEdge Instructor Branch Assignment",
            instructor=instructor_a.name,
            school_branch=branch_a1.name,
            enabled=1,
            is_primary=1,
        )
        unsupported = self._insert(
            "EduEdge Instructor Branch Assignment",
            instructor=instructor_a.name,
            school_branch=branch_a2.name,
            enabled=1,
            is_primary=0,
        )
        beta_eligibility = self._insert(
            "EduEdge Instructor Branch Assignment",
            instructor=instructor_b.name,
            school_branch=branch_b1.name,
            enabled=1,
            is_primary=1,
        )
        assignment = self._make_supported_assignment(
            instructor_a,
            institution_a,
            branch_a1,
        )

        school_admin = self._make_user("School Administrator", "School Admin")
        self._grant_branch(school_admin, branch_a1)
        self._grant_branch(school_admin, branch_a2)

        academic_admin = self._make_user("Academic Administrator", "Academic Admin")
        self._grant_branch(academic_admin, branch_a1)

        education_manager = self._make_user("Education Manager", "Education Manager")
        self._grant_branch(education_manager, branch_a2)

        instructor_user = self._make_user("Instructor", "Instructor User")
        self._grant_branch(instructor_user, branch_a1)

        frappe.set_user(school_admin.name)
        school_review = get_instructor_branch_eligibility_review(instructor_a.name)
        rows = {row["name"]: row for row in school_review["rows"]}
        self.assertEqual(set(rows), {primary_supported.name, unsupported.name})
        self.assertEqual(rows[primary_supported.name]["supporting_assignment_count"], 1)
        self.assertEqual(
            rows[primary_supported.name]["supporting_assignments"][0]["name"],
            assignment.name,
        )
        self.assertFalse(rows[primary_supported.name]["review_required"])
        self.assertTrue(rows[unsupported.name]["review_required"])
        self.assertEqual(
            rows[unsupported.name]["review_classification"],
            "unsupported-enabled-eligibility",
        )
        self.assertTrue(rows[unsupported.name]["provenance"]["created_by"])
        self.assertEqual(school_review["review_required_count"], 1)

        with self.assertRaises(frappe.ValidationError):
            disable_unused_instructor_branch_eligibility(
                primary_supported.name,
                "QA must not one-click disable a primary eligibility.",
            )

        frappe.set_user(academic_admin.name)
        academic_review = get_instructor_branch_eligibility_review(instructor_a.name)
        self.assertEqual(
            {row["school_branch"] for row in academic_review["rows"]},
            {branch_a1.name},
        )
        hidden_instructor = get_instructor_branch_eligibility_review(instructor_b.name)
        missing_instructor = get_instructor_branch_eligibility_review(
            f"DOES-NOT-EXIST-{self.suffix}"
        )
        self.assertEqual(hidden_instructor["rows"], [])
        self.assertEqual(missing_instructor["rows"], [])
        with self.assertRaises(frappe.PermissionError):
            disable_unused_instructor_branch_eligibility(
                unsupported.name,
                "Out-of-scope cleanup must fail.",
            )

        frappe.set_user(instructor_user.name)
        self.assertTrue(
            frappe.has_permission("EduEdge Instructor Branch Assignment", "read")
        )
        self.assertFalse(
            frappe.has_permission("EduEdge Instructor Branch Assignment", "write")
        )
        with self.assertRaises(frappe.PermissionError):
            get_instructor_branch_eligibility_review(instructor_a.name)

        frappe.set_user(education_manager.name)
        manager_review = get_instructor_branch_eligibility_review(instructor_a.name)
        self.assertEqual(
            {row["school_branch"] for row in manager_review["rows"]},
            {branch_a2.name},
        )
        reason = "QA legacy unsupported eligibility reconciliation"
        result = disable_unused_instructor_branch_eligibility(unsupported.name, reason)
        self.assertEqual(result["status"], "disabled")
        self.assertTrue(
            frappe.db.exists("EduEdge Instructor Branch Assignment", unsupported.name)
        )
        self.assertEqual(
            frappe.db.get_value(
                "EduEdge Instructor Branch Assignment",
                unsupported.name,
                "enabled",
            ),
            0,
        )
        self.assertTrue(
            frappe.db.exists(
                "Comment",
                {
                    "reference_doctype": "EduEdge Instructor Branch Assignment",
                    "reference_name": unsupported.name,
                    "content": ["like", f"%{reason}%"],
                },
            )
        )

        cleaned_review = get_instructor_branch_eligibility_review(instructor_a.name)
        cleaned = next(row for row in cleaned_review["rows"] if row["name"] == unsupported.name)
        self.assertFalse(cleaned["review_required"])
        self.assertEqual(cleaned["support_state"], "disabled-history")

        # The unrelated Institution remains untouched and invisible to this manager.
        self.assertEqual(
            frappe.db.get_value(
                "EduEdge Instructor Branch Assignment",
                beta_eligibility.name,
                "enabled",
            ),
            1,
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
