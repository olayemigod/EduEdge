from __future__ import annotations

import frappe
from education.education.test_utils import before_tests
from frappe.tests.utils import FrappeTestCase

from eduedge.api.teaching_schedule_rooms import create_teaching_schedule_room
from eduedge.education.custom_fields import BRANCH_FIELD


IGNORE_TEST_RECORD_DEPENDENCIES = ["EduEdge Institution", "User"]


class TestTeachingScheduleRoomQuickCreate(FrappeTestCase):
    def setUp(self) -> None:
        before_tests()
        frappe.set_user("Administrator")
        self.suffix = frappe.generate_hash(length=8).upper()
        self.company = "_Test Company"

    def _insert(self, doctype: str, **values):
        return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)

    def test_room_quick_create_is_branch_bound_and_idempotent(self):
        institution = self._insert(
            "EduEdge Institution",
            institution_name=f"QA Room School {self.suffix}",
            institution_code=f"QARS{self.suffix}",
            company=self.company,
            institution_type="SECONDARY",
            enabled=1,
        )
        branch = self._insert(
            "EduEdge School Branch",
            branch_name=f"QA Room Campus {self.suffix}",
            branch_code=f"QARB{self.suffix}",
            company=self.company,
            institution=institution.name,
            enabled=1,
        )
        room_name = f"QA Teaching Room {self.suffix}"

        created = create_teaching_schedule_room(
            branch=branch.name,
            room_name=room_name,
            room_number="A-12",
            seating_capacity="30",
        )
        self.assertTrue(created["created"])
        self.assertEqual(created["label"], room_name)
        self.assertEqual(created[BRANCH_FIELD], branch.name)
        self.assertEqual(
            frappe.db.get_value("Room", created["name"], BRANCH_FIELD),
            branch.name,
        )

        reused = create_teaching_schedule_room(
            branch=branch.name,
            room_name=room_name,
            room_number="SHOULD-NOT-DUPLICATE",
            seating_capacity="99",
        )
        self.assertFalse(reused["created"])
        self.assertEqual(reused["name"], created["name"])
        self.assertEqual(
            frappe.db.count(
                "Room",
                {BRANCH_FIELD: branch.name, "room_name": room_name},
            ),
            1,
        )
