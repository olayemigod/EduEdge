from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase


class TestEduEdgeResultPublicationLog(FrappeTestCase):
    def test_publication_log_cannot_be_deleted_even_by_administrator(self):
        frappe.set_user("Administrator")
        log = frappe.get_doc(
            {
                "doctype": "EduEdge Result Publication Log",
                "result_publication": "_Test Missing Result Publication",
                "action": "Test Audit Event",
                "from_status": "Draft",
                "to_status": "Pending Approval",
                "remarks": "Publication audit immutability regression fixture.",
            }
        )
        log.insert(
            ignore_permissions=True,
            ignore_links=True,
        )

        with self.assertRaises(frappe.ValidationError):
            frappe.delete_doc(
                "EduEdge Result Publication Log",
                log.name,
                force=True,
            )
