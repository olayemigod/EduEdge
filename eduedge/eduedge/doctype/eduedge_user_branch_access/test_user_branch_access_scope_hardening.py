from __future__ import annotations

import frappe
from education.education.test_utils import before_tests
from frappe.tests.utils import FrappeTestCase

from eduedge.education.user_branch_access_permissions import assignable_access_levels


class TestUserBranchAccessScopeHardening(FrappeTestCase):
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
            institution_name=f"UBA {label} School {self.suffix}",
            institution_code=f"UBA{label[:4].upper()}{self.suffix}",
            company=self.company,
            institution_type="PRIMARY",
            enabled=1,
        )

    def _make_branch(self, institution, label: str):
        return self._insert(
            "EduEdge School Branch",
            branch_name=f"UBA {label} Campus {self.suffix}",
            branch_code=f"UBA{label.replace(' ', '').upper()[:7]}{self.suffix}",
            company=self.company,
            institution=institution.name,
            enabled=1,
        )

    def _make_user(self, label: str):
        email = f"uba-{label.lower().replace(' ', '-')}-{self.suffix.lower()}@example.com"
        return self._insert(
            "User",
            email=email,
            first_name=f"UBA {label}",
            enabled=1,
            user_type="System User",
            send_welcome_email=0,
            roles=[{"role": "School Administrator"}],
        )

    def _grant(self, user, scope: str, *, branch=None, institution=None):
        values = {
            "user": user.name,
            "branch_role": "School Administrator",
            "access_scope": scope,
            "company": self.company,
            "enabled": 1,
            "can_switch_branch": 1,
            "is_default_branch": is_default_branch,
        }
        if institution:
            values["institution"] = institution.name
        if branch:
            values["school_branch"] = branch.name
        return self._insert("EduEdge User Branch Access", **values)

    def _regular_create(self, user, scope: str, *, branch=None, institution=None, is_default_branch: int = 0):
        values = {
            "doctype": "EduEdge User Branch Access",
            "user": user.name,
            "branch_role": "Other",
            "access_scope": scope,
            "company": self.company,
            "enabled": 1,
            "can_switch_branch": 1,
        }
        if institution:
            values["institution"] = institution.name
        if branch:
            values["school_branch"] = branch.name
        return frappe.get_doc(values).insert()

    def test_branch_institution_and_company_delegation_never_widen_actor_scope(self):
        institution_a = self._make_institution("Alpha")
        branch_a1 = self._make_branch(institution_a, "Alpha One")
        branch_a2 = self._make_branch(institution_a, "Alpha Two")
        institution_b = self._make_institution("Beta")
        branch_b1 = self._make_branch(institution_b, "Beta One")

        branch_admin = self._make_user("Branch Admin")
        branch_admin_access = self._grant(branch_admin, "Branch", branch=branch_a1)

        target_a1 = self._make_user("Target A1")
        target_a2 = self._make_user("Target A2")
        target_institution = self._make_user("Target Institution")
        target_company = self._make_user("Target Company")
        target_beta = self._make_user("Target Beta")

        # Seed out-of-scope rows as Administrator so list/document visibility can be tested.
        out_a2 = self._grant(target_a2, "Branch", branch=branch_a2)
        out_institution = self._grant(target_institution, "Institution", institution=institution_a)
        out_company = self._grant(target_company, "Company")
        out_beta = self._grant(target_beta, "Branch", branch=branch_b1)

        frappe.set_user(branch_admin.name)
        self.assertEqual(assignable_access_levels(), ["Branch"])
        self.assertTrue(frappe.has_permission("EduEdge User Branch Access", "create"))
        in_scope = self._regular_create(target_a1, "Branch", branch=branch_a1)

        with self.assertRaises(frappe.PermissionError):
            self._regular_create(self._make_user("Denied A2"), "Branch", branch=branch_a2)
        with self.assertRaises(frappe.PermissionError):
            self._regular_create(
                self._make_user("Denied Institution"),
                "Institution",
                institution=institution_a,
            )
        with self.assertRaises(frappe.PermissionError):
            self._regular_create(self._make_user("Denied Company"), "Company")

        visible = set(
            frappe.get_list(
                "EduEdge User Branch Access",
                pluck="name",
                limit_page_length=0,
            )
        )
        self.assertIn(branch_admin_access.name, visible)
        self.assertIn(in_scope.name, visible)
        self.assertNotIn(out_a2.name, visible)
        self.assertNotIn(out_institution.name, visible)
        self.assertNotIn(out_company.name, visible)
        self.assertNotIn(out_beta.name, visible)
        self.assertFalse(frappe.get_doc("EduEdge User Branch Access", out_a2.name).has_permission("read"))
        self.assertFalse(
            frappe.get_doc("EduEdge User Branch Access", out_institution.name).has_permission("read")
        )

        frappe.set_user("Administrator")
        institution_admin = self._make_user("Institution Admin")
        self._grant(institution_admin, "Institution", institution=institution_a)
        frappe.set_user(institution_admin.name)
        self.assertEqual(assignable_access_levels(), ["Institution", "Branch"])
        self._regular_create(self._make_user("Institution Branch"), "Branch", branch=branch_a2)
        self._regular_create(
            self._make_user("Institution Peer"),
            "Institution",
            institution=institution_a,
        )
        with self.assertRaises(frappe.PermissionError):
            self._regular_create(self._make_user("Institution Company Denied"), "Company")
        with self.assertRaises(frappe.PermissionError):
            self._regular_create(
                self._make_user("Institution Beta Denied"),
                "Institution",
                institution=institution_b,
            )

        frappe.set_user("Administrator")
        company_admin = self._make_user("Company Admin")
        self._grant(company_admin, "Company")
        frappe.set_user(company_admin.name)
        self.assertEqual(assignable_access_levels(), ["Company", "Institution", "Branch"])
        self._regular_create(self._make_user("Company Peer"), "Company")
        self._regular_create(
            self._make_user("Company Institution"),
            "Institution",
            institution=institution_b,
        )
        self._regular_create(self._make_user("Company Branch"), "Branch", branch=branch_b1)

    def test_limited_admin_cannot_clear_an_out_of_scope_default_branch(self):
        institution = self._make_institution("Defaults")
        branch_one = self._make_branch(institution, "Default One")
        branch_two = self._make_branch(institution, "Default Two")

        actor = self._make_user("Default Actor")
        self._grant(actor, "Branch", branch=branch_one)
        target = self._make_user("Default Target")

        frappe.set_user("Administrator")
        external_default = self._insert(
            "EduEdge User Branch Access",
            user=target.name,
            branch_role="Other",
            access_scope="Branch",
            company=self.company,
            institution=institution.name,
            school_branch=branch_two.name,
            enabled=1,
            is_default_branch=1,
            can_switch_branch=1,
        )

        frappe.set_user(actor.name)
        with self.assertRaises(frappe.PermissionError):
            self._regular_create(
                target,
                "Branch",
                branch=branch_one,
                is_default_branch=1,
            )

        self.assertEqual(
            frappe.db.get_value(
                "EduEdge User Branch Access",
                external_default.name,
                "is_default_branch",
            ),
            1,
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
