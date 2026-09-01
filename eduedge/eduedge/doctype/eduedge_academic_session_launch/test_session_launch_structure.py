from __future__ import annotations

import frappe
from education.education.test_utils import before_tests
from frappe.tests.utils import FrappeTestCase

from eduedge.api.class_arms import save_class_arm
from eduedge.api.programme_offerings import save_programme_offering
from eduedge.api.session_launch import start_or_resume_session_launch
from eduedge.api.session_launch_structure import (
    carry_forward_selected_class_arms,
    create_selected_class_intakes,
    get_session_structure_context,
)
from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.class_arm_identity import CLASS_ARM_FIELD, PREVIOUS_GROUP_FIELD
from eduedge.services.academic_calendar import ensure_institution_calendar


IGNORE_TEST_RECORD_DEPENDENCIES = ["EduEdge Institution", "Academic Year", "User"]


class TestSessionLaunchStructure(FrappeTestCase):
    def setUp(self) -> None:
        before_tests()
        frappe.set_user("Administrator")
        self.suffix = frappe.generate_hash(length=8).upper()
        self.company = "_Test Company"

    def _insert(self, doctype: str, **values):
        return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)

    def _make_year(self, label: str, start: str, end: str):
        year = self._insert(
            "Academic Year",
            academic_year_name=f"QA {label} {self.suffix}",
            year_start_date=start,
            year_end_date=end,
        )
        self._insert(
            "Academic Term",
            academic_year=year.name,
            term_name=f"QA {label} Term {self.suffix}",
            term_start_date=start,
            term_end_date=end,
        )
        return year

    def test_guided_structure_lists_classes_creates_selected_intakes_and_rolls_empty_arms(self):
        source_year = self._make_year("SOURCE", "2090-09-01", "2091-08-31")
        target_year = self._make_year("TARGET", "2091-09-01", "2092-08-31")
        institution = self._insert(
            "EduEdge Institution",
            institution_name=f"QA Launch Structure School {self.suffix}",
            institution_code=f"QALS{self.suffix}",
            company=self.company,
            institution_type="SECONDARY",
            enabled=1,
        )
        branch = self._insert(
            "EduEdge School Branch",
            branch_name=f"QA Launch Campus {self.suffix}",
            branch_code=f"QALB{self.suffix}",
            company=self.company,
            institution=institution.name,
            enabled=1,
        )
        optional_branch = self._insert(
            "EduEdge School Branch",
            branch_name=f"QA Optional Campus {self.suffix}",
            branch_code=f"QALO{self.suffix}",
            company=self.company,
            institution=institution.name,
            enabled=1,
        )
        ensure_institution_calendar(institution.name, source_year.name)
        ensure_institution_calendar(institution.name, target_year.name)

        department = self._insert(
            "Department",
            department_name=f"QA Launch Section {self.suffix}",
            company=self.company,
            is_group=0,
            **{INSTITUTION_FIELD: institution.name},
        )
        class_one = self._insert(
            "Program",
            program_name=f"QA Launch Class 1 {self.suffix}",
            department=department.name,
            **{INSTITUTION_FIELD: institution.name},
        )
        class_two = self._insert(
            "Program",
            program_name=f"QA Launch Class 2 {self.suffix}",
            department=department.name,
            **{INSTITUTION_FIELD: institution.name},
        )

        source_one = save_programme_offering(
            school_branch=branch.name,
            program=class_one.name,
            academic_year=source_year.name,
        )
        save_programme_offering(
            school_branch=branch.name,
            program=class_two.name,
            academic_year=source_year.name,
        )
        target_one = save_programme_offering(
            school_branch=branch.name,
            program=class_one.name,
            academic_year=target_year.name,
        )

        source_arm = save_class_arm(
            display_name=f"QA Class 1A {self.suffix}",
            branch=branch.name,
            offering=source_one["name"],
            group_based_on="Batch",
            students=[],
        )
        source_arm_doc = frappe.get_doc("Student Group", source_arm["name"])

        started = start_or_resume_session_launch(
            academic_year=target_year.name,
            institution=institution.name,
            source_academic_year=source_year.name,
        )
        launch_name = started["launch"]["name"]

        context = get_session_structure_context(launch_name)
        self.assertEqual(context["summary"]["classes"], 2)
        self.assertEqual(context["summary"]["intended_classes"], 2)
        self.assertEqual(context["summary"]["expected_intakes"], 2)
        self.assertEqual(context["summary"]["existing_intakes"], 1)
        self.assertEqual(context["summary"]["missing_intakes"], 1)
        self.assertEqual(context["summary"]["available_intake_candidates"], 2)
        self.assertEqual({row["program"] for row in context["classes"]}, {class_one.name, class_two.name})
        optional_rows = [row for row in context["class_intakes"] if row["branch"] == optional_branch.name]
        self.assertEqual(len(optional_rows), 2)
        self.assertTrue(all(row["status"] == "available" and not row["intended"] for row in optional_rows))

        missing = next(row for row in context["class_intakes"] if row["status"] == "missing")
        created = create_selected_class_intakes(
            launch=launch_name,
            selections=[{"branch": missing["branch"], "program": missing["program"]}],
        )
        self.assertEqual(created["created_count"], 1)
        self.assertEqual(created["context"]["summary"]["missing_intakes"], 0)
        self.assertEqual(created["context"]["summary"]["expected_intakes"], 2)

        retry = create_selected_class_intakes(
            launch=launch_name,
            selections=[{"branch": missing["branch"], "program": missing["program"]}],
        )
        self.assertEqual(retry["created_count"], 0)
        self.assertEqual(retry["existing_count"], 1)

        optional = next(row for row in retry["context"]["class_intakes"] if row["status"] == "available")
        optional_created = create_selected_class_intakes(
            launch=launch_name,
            selections=[{"branch": optional["branch"], "program": optional["program"]}],
        )
        self.assertEqual(optional_created["created_count"], 1)
        self.assertEqual(optional_created["context"]["summary"]["expected_intakes"], 3)
        self.assertEqual(optional_created["context"]["summary"]["existing_intakes"], 3)

        refreshed = optional_created["context"]
        ready_arm = next(
            row
            for row in refreshed["class_arms"]
            if row.get("class_arm_identity") == source_arm_doc.get(CLASS_ARM_FIELD)
        )
        self.assertEqual(ready_arm["status"], "ready")
        self.assertEqual(refreshed["summary"]["students_to_carry"], 0)

        rollover = carry_forward_selected_class_arms(
            launch=launch_name,
            selections=[
                {
                    "branch": branch.name,
                    "class_arm_identity": source_arm_doc.get(CLASS_ARM_FIELD),
                }
            ],
        )
        self.assertEqual(rollover["created_count"], 1)
        self.assertEqual(rollover["blocked_count"], 0)
        destination_name = frappe.db.get_value(
            "Student Group",
            {
                CLASS_ARM_FIELD: source_arm_doc.get(CLASS_ARM_FIELD),
                OFFERING_FIELD: target_one["name"],
                "academic_term": ["is", "not set"],
            },
            "name",
        )
        self.assertTrue(destination_name)
        destination = frappe.get_doc("Student Group", destination_name)
        self.assertEqual(destination.get(PREVIOUS_GROUP_FIELD), source_arm_doc.name)
        self.assertFalse([row for row in destination.students if row.active])
        self.assertEqual(rollover["context"]["summary"]["arms_ready_to_create"], 0)
        self.assertEqual(rollover["context"]["summary"]["arms_existing"], 1)
