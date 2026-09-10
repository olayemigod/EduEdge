from __future__ import annotations

import frappe
from education.education.test_utils import before_tests
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from eduedge.api.class_arms import save_class_arm
from eduedge.api.programme_offerings import save_programme_offering
from eduedge.api.session_launch import start_or_resume_session_launch
from eduedge.api.session_launch_learners import (
    create_guided_admission_cycle,
    create_guided_enrollment_draft,
    finalize_guided_progression,
    get_guided_progression_options,
    get_session_learner_context,
    prepare_guided_progression,
)
from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.academic_progression import (
    PROGRAM_ALLOW_REPETITION_FIELD,
    PROGRAM_NEXT_FIELD,
    PROGRAM_PROGRESSION_MODE_FIELD,
    PROGRAM_PROMOTION,
    PROGRAM_TERMINAL_FIELD,
)
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.academic_calendar import ensure_institution_calendar


IGNORE_TEST_RECORD_DEPENDENCIES = ["EduEdge Institution", "Academic Year", "User"]


class TestSessionLaunchLearners(FrappeTestCase):
    def setUp(self) -> None:
        before_tests()
        frappe.set_user("Administrator")
        self.suffix = frappe.generate_hash(length=8).upper()
        self.company = "_Test Company"

    def _insert(self, doctype: str, **values):
        return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)

    def _year(self, label: str, start: str, end: str):
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

    def _student(self, branch: str, label: str):
        return self._insert(
            "Student",
            first_name="QA",
            last_name=f"{label} {self.suffix}",
            student_email_id=f"qa-{label.lower()}-{self.suffix.lower()}@example.com",
            **{BRANCH_FIELD: branch},
        )

    def test_guided_progression_admissions_and_new_enrollment_remain_draft_first(self):
        source_year = self._year("LEARNER SOURCE", "2092-09-01", "2093-08-31")
        target_year = self._year("LEARNER TARGET", "2093-09-01", "2094-08-31")
        institution = self._insert(
            "EduEdge Institution",
            institution_name=f"QA Learner Launch School {self.suffix}",
            institution_code=f"QALL{self.suffix}",
            company=self.company,
            institution_type="SECONDARY",
            enabled=1,
        )
        branch = self._insert(
            "EduEdge School Branch",
            branch_name=f"QA Learner Campus {self.suffix}",
            branch_code=f"QALC{self.suffix}",
            company=self.company,
            institution=institution.name,
            enabled=1,
        )
        ensure_institution_calendar(institution.name, source_year.name)
        ensure_institution_calendar(institution.name, target_year.name)

        department = self._insert(
            "Department",
            department_name=f"QA Learner Section {self.suffix}",
            company=self.company,
            is_group=0,
            **{INSTITUTION_FIELD: institution.name},
        )
        class_two = self._insert(
            "Program",
            program_name=f"QA Learner Class 2 {self.suffix}",
            department=department.name,
            **{
                INSTITUTION_FIELD: institution.name,
                PROGRAM_PROGRESSION_MODE_FIELD: PROGRAM_PROMOTION,
                PROGRAM_TERMINAL_FIELD: 1,
                PROGRAM_ALLOW_REPETITION_FIELD: 1,
            },
        )
        class_one = self._insert(
            "Program",
            program_name=f"QA Learner Class 1 {self.suffix}",
            department=department.name,
            **{
                INSTITUTION_FIELD: institution.name,
                PROGRAM_PROGRESSION_MODE_FIELD: PROGRAM_PROMOTION,
                PROGRAM_NEXT_FIELD: class_two.name,
                PROGRAM_TERMINAL_FIELD: 0,
                PROGRAM_ALLOW_REPETITION_FIELD: 1,
            },
        )

        source_offering = save_programme_offering(
            school_branch=branch.name,
            program=class_one.name,
            academic_year=source_year.name,
            admission_enabled=1,
            enrollment_enabled=1,
        )
        destination_offering = save_programme_offering(
            school_branch=branch.name,
            program=class_two.name,
            academic_year=target_year.name,
            admission_enabled=1,
            enrollment_enabled=1,
        )

        returning = self._student(branch.name, "Returning")
        source_enrollment = self._insert(
            "Program Enrollment",
            student=returning.name,
            enrollment_date=nowdate(),
            program=class_one.name,
            academic_year=source_year.name,
            **{OFFERING_FIELD: source_offering["name"]},
        )
        source_enrollment.submit()

        destination_arm = save_class_arm(
            display_name=f"QA Learner Class 2A {self.suffix}",
            branch=branch.name,
            offering=destination_offering["name"],
            group_based_on="Batch",
            students=[],
        )

        started = start_or_resume_session_launch(
            academic_year=target_year.name,
            institution=institution.name,
            source_academic_year=source_year.name,
        )
        launch = started["launch"]["name"]

        context = get_session_learner_context(launch)
        progression_row = next(row for row in context["progression"] if row["name"] == source_enrollment.name)
        self.assertEqual(progression_row["launch_state"], "decision_required")
        self.assertEqual(context["summary"]["decision_required"], 1)

        options = get_guided_progression_options(
            launch=launch,
            source_enrollment=source_enrollment.name,
            outcome="Promote",
        )
        self.assertEqual(options["offering"]["name"], destination_offering["name"])
        self.assertIn(destination_arm["name"], {row["name"] for row in options["student_groups"]})

        prepared = prepare_guided_progression(
            launch=launch,
            source_enrollment=source_enrollment.name,
            outcome="Promote",
            reason="QA guided promotion",
            target_student_group=destination_arm["name"],
        )
        self.assertEqual(prepared["result"]["created_count"], 1)
        target_name = prepared["result"]["created"][0]["name"]
        target = frappe.get_doc("Program Enrollment", target_name)
        self.assertEqual(target.docstatus, 0)
        self.assertEqual(target.academic_year, target_year.name)
        self.assertEqual(target.get(OFFERING_FIELD), destination_offering["name"])
        refreshed_row = next(row for row in prepared["context"]["progression"] if row["name"] == source_enrollment.name)
        self.assertEqual(refreshed_row["launch_state"], "draft_prepared")

        retry = prepare_guided_progression(
            launch=launch,
            source_enrollment=source_enrollment.name,
            outcome="Promote",
            reason="QA guided promotion",
            target_student_group=destination_arm["name"],
        )
        self.assertEqual(retry["result"]["created_count"], 0)
        self.assertEqual(retry["result"]["existing_count"], 1)

        with self.assertRaisesRegex(frappe.ValidationError, "returning Student"):
            create_guided_enrollment_draft(
                launch=launch,
                branch=branch.name,
                student=returning.name,
                offering=destination_offering["name"],
            )

        target.submit()
        submitted_context = get_session_learner_context(launch)
        submitted_row = next(row for row in submitted_context["progression"] if row["name"] == source_enrollment.name)
        self.assertEqual(submitted_row["launch_state"], "target_submitted")

        finalized = finalize_guided_progression(
            launch=launch,
            source_enrollment=source_enrollment.name,
            outcome="Promote",
            reason="QA final promotion approval",
        )
        self.assertEqual(finalized["result"]["finalized_count"], 1)
        final_row = next(row for row in finalized["context"]["progression"] if row["name"] == source_enrollment.name)
        self.assertEqual(final_row["launch_state"], "finalized")
        arm_doc = frappe.get_doc("Student Group", destination_arm["name"])
        self.assertIn(returning.name, {row.student for row in arm_doc.students if row.active})

        admission = create_guided_admission_cycle(
            launch=launch,
            branch=branch.name,
            title=f"{target_year.name} Admissions - {branch.name} - {self.suffix}",
            programs=[class_two.name],
            enable_admission_application=0,
            published=0,
        )
        admission_doc = frappe.get_doc("Student Admission", admission["result"]["name"])
        self.assertEqual(admission_doc.docstatus, 0)
        self.assertEqual(admission_doc.academic_year, target_year.name)
        self.assertEqual(admission_doc.get(BRANCH_FIELD), branch.name)
        self.assertEqual({row.program for row in admission_doc.program_details}, {class_two.name})
        self.assertEqual(admission["context"]["summary"]["admission_branches_ready"], 1)

        new_student = self._student(branch.name, "NewStudent")
        direct = create_guided_enrollment_draft(
            launch=launch,
            branch=branch.name,
            student=new_student.name,
            offering=destination_offering["name"],
        )
        direct_doc = frappe.get_doc("Program Enrollment", direct["result"]["name"])
        self.assertEqual(direct_doc.docstatus, 0)
        self.assertEqual(direct_doc.student, new_student.name)
        self.assertEqual(direct_doc.academic_year, target_year.name)
        self.assertEqual(direct_doc.get(OFFERING_FIELD), destination_offering["name"])
        self.assertEqual(direct["context"]["summary"]["direct_enrollments"], 1)
        self.assertGreaterEqual(direct["context"]["summary"]["progression_enrollments"], 1)
