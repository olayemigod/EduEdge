from __future__ import annotations

import frappe
from education.education.test_utils import before_tests
from frappe.tests.utils import FrappeTestCase

from eduedge.api.class_arms import save_class_arm
from eduedge.api.programme_offerings import save_programme_offering
from eduedge.api.session_launch import start_or_resume_session_launch
from eduedge.api.session_launch_delivery import (
    add_guided_class_subject,
    assign_guided_class_teacher,
    assign_guided_subject_instructor,
    get_session_delivery_context,
)
from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.services.academic_calendar import ensure_institution_calendar


IGNORE_TEST_RECORD_DEPENDENCIES = ["EduEdge Institution", "Academic Year", "User"]


class TestSessionLaunchDelivery(FrappeTestCase):
    def setUp(self) -> None:
        before_tests()
        frappe.set_user("Administrator")
        self.suffix = frappe.generate_hash(length=8).upper()
        self.company = "_Test Company"

    def _insert(self, doctype: str, **values):
        return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)

    def test_guided_delivery_adds_curriculum_and_reuses_governed_assignment_services(self):
        year = self._insert(
            "Academic Year",
            academic_year_name=f"QA Delivery {self.suffix}",
            year_start_date="2093-09-01",
            year_end_date="2094-08-31",
        )
        self._insert(
            "Academic Term",
            academic_year=year.name,
            term_name=f"QA Delivery Term {self.suffix}",
            term_start_date="2093-09-01",
            term_end_date="2093-12-20",
        )
        institution = self._insert(
            "EduEdge Institution",
            institution_name=f"QA Delivery School {self.suffix}",
            institution_code=f"QADS{self.suffix}",
            company=self.company,
            institution_type="SECONDARY",
            enabled=1,
        )
        branch = self._insert(
            "EduEdge School Branch",
            branch_name=f"QA Delivery Campus {self.suffix}",
            branch_code=f"QADB{self.suffix}",
            company=self.company,
            institution=institution.name,
            enabled=1,
        )
        ensure_institution_calendar(institution.name, year.name)
        department = self._insert(
            "Department",
            department_name=f"QA Delivery Section {self.suffix}",
            company=self.company,
            is_group=0,
            **{INSTITUTION_FIELD: institution.name},
        )
        program = self._insert(
            "Program",
            program_name=f"QA Delivery Class {self.suffix}",
            department=department.name,
            **{INSTITUTION_FIELD: institution.name},
        )
        course_values = {"course_name": f"QA Mathematics {self.suffix}"}
        if frappe.get_meta("Course").has_field(INSTITUTION_FIELD):
            course_values[INSTITUTION_FIELD] = institution.name
        course = self._insert("Course", **course_values)
        instructor_values = {"instructor_name": f"QA Teacher {self.suffix}"}
        if frappe.get_meta("Instructor").has_field("status"):
            instructor_values["status"] = "Active"
        if frappe.get_meta("Instructor").has_field(INSTITUTION_FIELD):
            instructor_values[INSTITUTION_FIELD] = institution.name
        instructor = self._insert("Instructor", **instructor_values)

        offering = save_programme_offering(
            school_branch=branch.name,
            program=program.name,
            academic_year=year.name,
        )
        arm = save_class_arm(
            display_name=f"QA Delivery Class A {self.suffix}",
            branch=branch.name,
            offering=offering["name"],
            group_based_on="Batch",
            students=[],
        )
        started = start_or_resume_session_launch(
            academic_year=year.name,
            institution=institution.name,
        )
        launch_name = started["launch"]["name"]

        initial = get_session_delivery_context(launch_name)
        self.assertEqual(initial["summary"]["class_intakes"], 1)
        self.assertEqual(initial["summary"]["classes_without_subjects"], 1)
        self.assertEqual(initial["summary"]["expected_teaching_contexts"], 0)
        self.assertTrue(initial["summary"]["class_responsibility_required"])
        responsibility = initial["branches"][0]["class_responsibilities"][0]
        self.assertEqual(responsibility["student_group"], arm["name"])
        self.assertFalse(responsibility["assigned"])

        added = add_guided_class_subject(
            launch=launch_name,
            program_offering=offering["name"],
            course=course.name,
        )
        after_subject = added["context"]
        self.assertEqual(after_subject["summary"]["classes_without_subjects"], 0)
        self.assertEqual(after_subject["summary"]["classes_with_subjects"], 1)
        self.assertEqual(after_subject["summary"]["expected_teaching_contexts"], 1)
        self.assertTrue(any(row.course == course.name for row in frappe.get_doc("Program", program.name).courses))

        teaching = after_subject["branches"][0]["teaching_contexts"][0]
        self.assertFalse(teaching["assigned"])
        assigned = assign_guided_subject_instructor(
            launch=launch_name,
            instructor=instructor.name,
            contexts=[{"context_key": teaching["context_key"]}],
        )
        self.assertEqual(assigned["context"]["summary"]["assigned_teaching_contexts"], 1)
        self.assertEqual(assigned["context"]["summary"]["unassigned_teaching_contexts"], 0)
        self.assertTrue(
            frappe.db.exists(
                "EduEdge Instructor Assignment",
                {
                    "instructor": instructor.name,
                    "program_offering": offering["name"],
                    "student_group": arm["name"],
                    "course": course.name,
                    "enabled": 1,
                },
            )
        )

        class_teacher = assign_guided_class_teacher(
            launch=launch_name,
            instructor=instructor.name,
            student_groups=[arm["name"]],
            assignment_type="Class Teacher",
        )
        self.assertEqual(class_teacher["context"]["summary"]["class_responsibility_assigned"], 1)
        self.assertEqual(class_teacher["context"]["summary"]["class_responsibility_missing"], 0)
        self.assertTrue(class_teacher["context"]["summary"]["class_responsibility_ready"])

        # Session Launch does not invent a timetable or Scheme of Work while
        # preparing teaching responsibility. Those remain separately auditable.
        final = class_teacher["context"]
        self.assertEqual(final["summary"]["scheduled_teaching_contexts"], 0)
        self.assertEqual(final["summary"]["unscheduled_teaching_contexts"], 1)
        self.assertEqual(final["summary"]["approved_scheme_contexts"], 0)
        self.assertEqual(final["summary"]["scheme_attention_contexts"], 1)
        self.assertFalse(final["summary"]["academic_delivery_ready"])
        self.assertFalse(
            frappe.db.exists(
                "Course Schedule",
                {"student_group": arm["name"], "course": course.name},
            )
        )
