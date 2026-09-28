from __future__ import annotations

import frappe
from education.education.test_utils import before_tests
from frappe.tests.utils import FrappeTestCase

from eduedge.api.instructor_assignments import (
    get_instructor_assignments_page,
    preview_instructor_assignment_batch,
)
from eduedge.education.academic_fields import INSTITUTION_FIELD


class TestInstructorAssignmentPersonaMatrix(FrappeTestCase):
    """Database-backed visibility and authoring scope for Instructor Assignments."""

    def setUp(self) -> None:
        before_tests()
        frappe.set_user("Administrator")
        self.suffix = frappe.generate_hash(length=8).upper()
        self.company = "_Test Company"
        settings = frappe.get_single("EduEdge Settings")
        self.original_enforcement = settings.get("enable_user_branch_access_enforcement")
        settings.enable_user_branch_access_enforcement = 1
        settings.save(ignore_permissions=True)

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
            institution_name=f"Persona {label} School {self.suffix}",
            institution_code=f"PM{label[:4].upper()}{self.suffix}",
            company=self.company,
            institution_type="PRIMARY",
            enabled=1,
        )

    def _make_branch(self, institution, label: str):
        return self._insert(
            "EduEdge School Branch",
            branch_name=f"Persona {label} Campus {self.suffix}",
            branch_code=f"PM{label.replace(' ', '').upper()[:8]}{self.suffix}",
            company=self.company,
            institution=institution.name,
            enabled=1,
        )

    def _make_instructor(self, institution, label: str):
        return self._insert(
            "Instructor",
            instructor_name=f"Persona {label} Instructor {self.suffix}",
            status="Active",
            **{INSTITUTION_FIELD: institution.name},
        )

    def _make_user(self, role: str, label: str):
        email = f"persona-{label.lower().replace(' ', '-')}-{self.suffix.lower()}@example.com"
        user = self._insert(
            "User",
            email=email,
            first_name=f"Persona {label}",
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

    def _grant_instructor_branch(self, instructor, branch, *, primary: bool = False):
        return self._insert(
            "EduEdge Instructor Branch Assignment",
            instructor=instructor.name,
            school_branch=branch.name,
            enabled=1,
            is_primary=1 if primary else 0,
        )

    @staticmethod
    def _names(rows: list[dict]) -> set[str]:
        return {str(row.get("name")) for row in rows if row.get("name")}

    def test_assignment_page_personas_fail_closed_and_global_admin_remains_global(self):
        institution_a = self._make_institution("Alpha")
        branch_a1 = self._make_branch(institution_a, "Alpha One")
        branch_a2 = self._make_branch(institution_a, "Alpha Two")
        institution_b = self._make_institution("Beta")
        branch_b1 = self._make_branch(institution_b, "Beta One")

        instructor_a = self._make_instructor(institution_a, "Alpha")
        instructor_b = self._make_instructor(institution_b, "Beta")
        self._grant_instructor_branch(instructor_a, branch_a1, primary=True)
        self._grant_instructor_branch(instructor_a, branch_a2)
        self._grant_instructor_branch(instructor_b, branch_b1, primary=True)

        school_admin = self._make_user("School Administrator", "School Admin")
        self._grant_branch(school_admin, branch_a1)
        academic_admin = self._make_user("Academic Administrator", "Academic Admin")
        self._grant_branch(academic_admin, branch_a1)
        education_manager = self._make_user("Education Manager", "Education Manager")
        self._grant_branch(education_manager, branch_a2)
        instructor_user = self._make_user("Instructor", "Instructor User")
        self._grant_branch(instructor_user, branch_a1)
        global_admin = self._make_user("EduEdge Administrator", "Global Admin")

        for manager, branch in (
            (school_admin, branch_a1),
            (academic_admin, branch_a1),
            (education_manager, branch_a2),
        ):
            frappe.set_user(manager.name)
            page = get_instructor_assignments_page(instructor=instructor_a.name)
            self.assertTrue(page["permissions"]["can_manage"])
            self.assertEqual(self._names(page["permitted_branches"]), {branch.name})
            self.assertEqual(self._names(page["allowed_branches"]), {branch.name})
            self.assertEqual(self._names(page["instructors"]), {instructor_a.name})

            with self.assertRaises(frappe.PermissionError):
                get_instructor_assignments_page(
                    instructor=instructor_b.name,
                )

        frappe.set_user(school_admin.name)
        with self.assertRaises(frappe.PermissionError):
            get_instructor_assignments_page(
                instructor=instructor_a.name,
                branches=[branch_a2.name],
            )

        frappe.set_user(instructor_user.name)
        self.assertFalse(
            frappe.has_permission("EduEdge Instructor Assignment", "create")
        )
        self.assertFalse(
            frappe.has_permission("EduEdge Instructor Assignment", "write")
        )
        page = get_instructor_assignments_page()
        self.assertFalse(page["permissions"]["can_manage"])
        self.assertEqual(page["instructors"], [])
        self.assertEqual(page["allowed_branches"], [])
        with self.assertRaises(frappe.PermissionError):
            preview_instructor_assignment_batch({})

        frappe.set_user(global_admin.name)
        page = get_instructor_assignments_page(instructor=instructor_a.name)
        self.assertTrue(page["permissions"]["can_manage"])
        self.assertTrue(
            {branch_a1.name, branch_a2.name, branch_b1.name}.issubset(
                self._names(page["permitted_branches"])
            )
        )
        self.assertEqual(
            self._names(page["allowed_branches"]),
            {branch_a1.name, branch_a2.name},
        )
        self.assertTrue(
            {instructor_a.name, instructor_b.name}.issubset(
                self._names(page["instructors"])
            )
        )
        cross_campus = get_instructor_assignments_page(
            instructor=instructor_a.name,
            branches=[branch_a2.name],
        )
        self.assertEqual(cross_campus["selected_branches"], [branch_a2.name])


if __name__ == "__main__":
    import unittest

    unittest.main()
