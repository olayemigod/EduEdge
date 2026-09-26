from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cint


class TestCapabilityEnforcementGuard(FrappeTestCase):
    def setUp(self) -> None:
        frappe.set_user("Administrator")
        self.settings = frappe.get_single("EduEdge Settings")
        self.original = cint(self.settings.enforce_instructor_assignment_capabilities)

    def tearDown(self) -> None:
        frappe.set_user("Administrator")
        settings = frappe.get_single("EduEdge Settings")
        if cint(settings.enforce_instructor_assignment_capabilities) != self.original:
            settings.enforce_instructor_assignment_capabilities = self.original
            frappe.flags.in_eduedge_capability_enforcement_change = True
            try:
                settings.save()
            finally:
                frappe.flags.in_eduedge_capability_enforcement_change = False

    def test_direct_capability_enforcement_change_is_blocked(self):
        target = 0 if self.original else 1
        self.settings.enforce_instructor_assignment_capabilities = target

        with self.assertRaises(frappe.PermissionError):
            self.settings.save()

        self.assertEqual(
            cint(
                frappe.db.get_single_value(
                    "EduEdge Settings",
                    "enforce_instructor_assignment_capabilities",
                )
            ),
            self.original,
        )

    def test_guarded_capability_enforcement_change_is_persisted(self):
        target = 0 if self.original else 1
        self.settings.enforce_instructor_assignment_capabilities = target
        frappe.flags.in_eduedge_capability_enforcement_change = True
        try:
            self.settings.save()
        finally:
            frappe.flags.in_eduedge_capability_enforcement_change = False

        self.assertEqual(
            cint(
                frappe.db.get_single_value(
                    "EduEdge Settings",
                    "enforce_instructor_assignment_capabilities",
                )
            ),
            target,
        )
