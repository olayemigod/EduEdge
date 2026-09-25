from __future__ import annotations

import frappe
from education.education.test_utils import before_tests
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cint, now_datetime

from eduedge.api.academic_operations_safe import (
    get_attendance_register,
    get_operations_context,
    save_attendance_register,
)
from eduedge.api.assessment_assignment_options import (
    assessment_plan_course_query,
    assessment_plan_student_group_query,
)
from eduedge.api.attendance_tool_safe import get_student_attendance_records
from eduedge.api.branch_governance import get_governance_context
from eduedge.api.class_arms import save_class_arm
from eduedge.api.academic_operations_review import (
    course_query as schedule_course_query,
    student_group_query as schedule_student_group_query,
)
from eduedge.api.teaching_assignment_options import course_schedule_instructor_query
from eduedge.api.teaching_schedule import (
    get_teaching_schedule_context,
    search_teaching_schedule_class_arms,
    search_teaching_schedule_courses,
    search_teaching_schedule_offerings,
)
from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.academic_operations import before_validate_student_attendance
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.instructor_assignment_capabilities import (
    get_instructor_assignment_capability_state,
)
from eduedge.permissions_baseline import ensure_legacy_attendance_report_role_guard
from eduedge.services.academic_calendar import ensure_institution_calendar


class TestInstitutionCorePersonaFlow(FrappeTestCase):
    """DB-backed freeze coverage for Branch -> Instructor -> Schedule -> Attendance."""

    def setUp(self) -> None:
        before_tests()
        frappe.set_user("Administrator")
        self.suffix = frappe.generate_hash(length=8).upper()
        self.company = "_Test Company"
        settings = frappe.get_single("EduEdge Settings")
        self.original_branch_enforcement = cint(
            settings.enable_user_branch_access_enforcement
        )
        self.original_capability_enforcement = cint(
            settings.enforce_instructor_assignment_capabilities
        )
        self._set_enforcement(branch=1, capabilities=1)
        if frappe.db.exists("Holiday List", "Test Holiday List"):
            frappe.db.set_value(
                "Company",
                self.company,
                "default_holiday_list",
                "Test Holiday List",
            )

    def tearDown(self) -> None:
        frappe.set_user("Administrator")
        self._set_enforcement(
            branch=self.original_branch_enforcement,
            capabilities=self.original_capability_enforcement,
        )

    def _set_enforcement(self, *, branch: int, capabilities: int) -> None:
        settings = frappe.get_single("EduEdge Settings")
        settings.enable_user_branch_access_enforcement = cint(branch)
        settings.enforce_instructor_assignment_capabilities = cint(capabilities)
        frappe.flags.in_eduedge_capability_enforcement_change = True
        try:
            settings.save(ignore_permissions=True)
        finally:
            frappe.flags.in_eduedge_capability_enforcement_change = False

    def _insert(self, doctype: str, **values):
        return frappe.get_doc({"doctype": doctype, **values}).insert(
            ignore_permissions=True
        )

    def _make_user(self, role: str, label: str):
        email = (
            f"qa-core-{label.lower().replace(' ', '-')}-"
            f"{self.suffix.lower()}@example.com"
        )
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

    def _make_institution(self, label: str):
        return self._insert(
            "EduEdge Institution",
            institution_name=f"QA Core {label} School {self.suffix}",
            institution_code=f"QAC{label[:4].upper()}{self.suffix}",
            company=self.company,
            institution_type="PRIMARY",
            enabled=1,
        )

    def _make_branch(self, institution, label: str):
        return self._insert(
            "EduEdge School Branch",
            branch_name=f"QA Core {label} Campus {self.suffix}",
            branch_code=f"QAC{label.replace(' ', '').upper()[:8]}{self.suffix}",
            company=self.company,
            institution=institution.name,
            enabled=1,
        )

    def _make_employee(self, user, department, label: str):
        return self._insert(
            "Employee",
            naming_series="HR-EMP-",
            first_name=f"QA {label}",
            company=self.company,
            user_id=user.name,
            create_user_permission=0,
            date_of_birth="1990-05-08",
            date_of_joining="2020-01-01",
            department=department.name,
            gender="Female",
            status="Active",
        )

    def _make_instructor(self, institution, label: str, employee=None):
        values = {
            "instructor_name": f"QA {label} Instructor {self.suffix}",
            "status": "Active",
            INSTITUTION_FIELD: institution.name,
        }
        if employee:
            values["employee"] = employee.name
        return self._insert("Instructor", **values)

    def _make_offering(self, institution, branch, program, year, label: str):
        return self._insert(
            "EduEdge Program Offering",
            school_branch=branch.name,
            program=program.name,
            academic_year=year.name,
            offering_title=f"QA Core {label} Intake {self.suffix}",
            offering_code=f"QA-CORE-{label.replace(' ', '').upper()[:8]}-{self.suffix}",
            study_mode="Full-Time",
            delivery_mode="Onsite",
            enrollment_enabled=1,
            is_active=1,
        )

    def _make_eligibility(self, instructor, branch, *, primary: int = 0):
        return self._insert(
            "EduEdge Instructor Branch Assignment",
            instructor=instructor.name,
            school_branch=branch.name,
            enabled=1,
            is_primary=primary,
        )

    def _make_subject_assignment(
        self,
        instructor,
        institution,
        branch,
        offering,
        student_group: str,
        course,
    ):
        return self._insert(
            "EduEdge Instructor Assignment",
            instructor=instructor.name,
            assignment_type="Subject Instructor",
            assignment_scope="Class Arm",
            institution=institution.name,
            school_branch=branch.name,
            program_offering=offering.name,
            student_group=student_group,
            course=course.name,
            enabled=1,
        )

    def _grant_assignment_capabilities(self, assignment) -> None:
        doc = frappe.get_doc("EduEdge Instructor Assignment", assignment.name)
        doc.can_view_subject_content = 1
        doc.can_create_assessment_plans = 1
        doc.can_enter_marks = 1
        doc.capabilities_updated_on = now_datetime()
        doc.capabilities_updated_by = "Administrator"
        doc.capabilities_update_reason = "Institution Core persona freeze fixture"
        frappe.flags.in_eduedge_assignment_capability_update = True
        try:
            doc.save(ignore_permissions=True)
        finally:
            frappe.flags.in_eduedge_assignment_capability_update = False

    def _make_schedule(
        self,
        *,
        student_group: str,
        instructor,
        course,
        room,
        branch,
        from_time: str,
    ):
        return self._insert(
            "Course Schedule",
            naming_series="EDU-CSH-.YYYY.-",
            student_group=student_group,
            instructor=instructor.name,
            course=course.name,
            schedule_date="2094-10-05",
            room=room.name,
            from_time=from_time,
            to_time="10:00:00" if from_time == "09:00:00" else "12:00:00",
            **{BRANCH_FIELD: branch.name},
        )

    def test_institution_core_persona_matrix(self):
        institution = self._make_institution("Alpha")
        branch_a = self._make_branch(institution, "Alpha One")
        branch_b = self._make_branch(institution, "Alpha Two")
        unrelated_institution = self._make_institution("Beta")
        unrelated_branch = self._make_branch(unrelated_institution, "Beta One")

        year = self._insert(
            "Academic Year",
            academic_year_name=f"QA Core {self.suffix}",
            year_start_date="2094-09-01",
            year_end_date="2095-08-31",
        )
        self._insert(
            "Academic Term",
            academic_year=year.name,
            term_name=f"QA Core Term {self.suffix}",
            term_start_date="2094-09-01",
            term_end_date="2094-12-31",
        )
        ensure_institution_calendar(institution.name, year.name)

        department = self._insert(
            "Department",
            department_name=f"QA Core Section {self.suffix}",
            company=self.company,
            is_group=0,
            **{INSTITUTION_FIELD: institution.name},
        )
        course = self._insert(
            "Course",
            course_name=f"QA Core Mathematics {self.suffix}",
            **{INSTITUTION_FIELD: institution.name},
        )
        extra_course = self._insert(
            "Course",
            course_name=f"QA Core Science {self.suffix}",
            **{INSTITUTION_FIELD: institution.name},
        )
        program = self._insert(
            "Program",
            program_name=f"QA Core Class {self.suffix}",
            department=department.name,
            courses=[
                {"course": course.name, "required": 1},
                {"course": extra_course.name, "required": 1},
            ],
            **{INSTITUTION_FIELD: institution.name},
        )

        offering_a = self._make_offering(
            institution, branch_a, program, year, "Alpha One"
        )
        offering_b = self._make_offering(
            institution, branch_b, program, year, "Alpha Two"
        )

        instructor_user = self._make_user("Instructor", "Instructor")
        instructor_employee = self._make_employee(
            instructor_user, department, "Instructor"
        )
        instructor_a = self._make_instructor(
            institution, "Alpha", employee=instructor_employee
        )
        instructor_b = self._make_instructor(institution, "Beta")
        self._make_eligibility(instructor_a, branch_a, primary=1)
        self._make_eligibility(instructor_b, branch_b, primary=1)
        self._grant_branch(instructor_user, branch_a)

        school_admin = self._make_user("School Administrator", "School Admin")
        self._grant_branch(school_admin, branch_a)
        self._grant_branch(school_admin, branch_b)

        academics_user = self._make_user("Academics User", "Academics User")
        self._grant_branch(academics_user, branch_a)
        ensure_legacy_attendance_report_role_guard()
        frappe.set_user(academics_user.name)
        self.assertTrue(frappe.has_permission("Student Attendance", "report"))
        for report_name in (
            "Student Batch-Wise Attendance",
            "Student Monthly Attendance Sheet",
            "Absent Student Report",
        ):
            self.assertFalse(frappe.get_doc("Report", report_name).is_permitted())
        frappe.set_user("Administrator")

        student = self._insert(
            "Student",
            first_name="QA",
            last_name=f"Core Learner {self.suffix}",
            student_email_id=f"qa-core-student-{self.suffix.lower()}@example.com",
            enabled=1,
            **{BRANCH_FIELD: branch_a.name},
        )
        enrollment = self._insert(
            "Program Enrollment",
            student=student.name,
            program=program.name,
            academic_year=year.name,
            enrollment_date="2094-09-02",
            **{
                BRANCH_FIELD: branch_a.name,
                OFFERING_FIELD: offering_a.name,
            },
        )
        enrollment.submit()

        class_a = save_class_arm(
            display_name=f"QA Core A {self.suffix}",
            branch=branch_a.name,
            offering=offering_a.name,
            students=[{"student": student.name}],
        )
        class_b = save_class_arm(
            display_name=f"QA Core B {self.suffix}",
            branch=branch_b.name,
            offering=offering_b.name,
            students=[],
        )
        class_peer = save_class_arm(
            display_name=f"QA Core Peer {self.suffix}",
            branch=branch_a.name,
            offering=offering_a.name,
            students=[],
        )

        assignment_a = self._make_subject_assignment(
            instructor_a,
            institution,
            branch_a,
            offering_a,
            class_a["name"],
            course,
        )
        self._grant_assignment_capabilities(assignment_a)

        peer_instructor = self._make_instructor(institution, "Peer")
        self._make_eligibility(peer_instructor, branch_a)
        self._make_subject_assignment(
            peer_instructor,
            institution,
            branch_a,
            offering_a,
            class_a["name"],
            course,
        )
        self._make_subject_assignment(
            peer_instructor,
            institution,
            branch_a,
            offering_a,
            class_peer["name"],
            course,
        )

        self._make_subject_assignment(
            instructor_b,
            institution,
            branch_b,
            offering_b,
            class_b["name"],
            course,
        )

        frappe.set_user(instructor_user.name)
        first_assessment_groups = assessment_plan_student_group_query(
            "Student Group",
            "",
            "name",
            0,
            20,
            {
                BRANCH_FIELD: branch_a.name,
                "academic_year": year.name,
                "schedule_date": "2094-10-05",
            },
        )
        self.assertEqual(
            [row[0] for row in first_assessment_groups],
            [class_a["name"]],
        )

        # Assessment Plan creation is governed by can_create_assessment_plans,
        # independently from generic Subject-content visibility.
        frappe.set_user("Administrator")
        frappe.db.set_value(
            "EduEdge Instructor Assignment",
            assignment_a.name,
            "can_view_subject_content",
            0,
            update_modified=False,
        )
        frappe.set_user(instructor_user.name)
        first_assessment_courses = assessment_plan_course_query(
            "Course",
            "",
            "name",
            0,
            20,
            {
                BRANCH_FIELD: branch_a.name,
                "student_group": class_a["name"],
                "schedule_date": "2094-10-05",
            },
        )
        self.assertEqual(
            [row[0] for row in first_assessment_courses],
            [course.name],
        )
        frappe.set_user("Administrator")
        frappe.db.set_value(
            "EduEdge Instructor Assignment",
            assignment_a.name,
            "can_view_subject_content",
            1,
            update_modified=False,
        )
        frappe.set_user(instructor_user.name)

        first_schedule_groups = schedule_student_group_query(
            "Student Group",
            "",
            "name",
            0,
            20,
            {
                BRANCH_FIELD: branch_a.name,
                "reference_date": "2094-10-05",
            },
        )
        self.assertEqual(
            [row[0] for row in first_schedule_groups],
            [class_a["name"]],
        )

        limited_schedule_courses = schedule_course_query(
            "Course",
            "",
            "name",
            0,
            20,
            {
                BRANCH_FIELD: branch_a.name,
                "student_group": class_a["name"],
                "program": program.name,
                "reference_date": "2094-10-05",
            },
        )
        self.assertEqual(
            [row[0] for row in limited_schedule_courses],
            [course.name],
        )

        guided_offerings = search_teaching_schedule_offerings(
            branch=branch_a.name,
            reference_date="2094-10-05",
        )
        self.assertEqual(
            [row["value"] for row in guided_offerings],
            [offering_a.name],
        )
        guided_class_arms = search_teaching_schedule_class_arms(
            branch=branch_a.name,
            program_offering=offering_a.name,
            reference_date="2094-10-05",
        )
        self.assertEqual(
            [row["value"] for row in guided_class_arms],
            [class_a["name"]],
        )
        guided_courses = search_teaching_schedule_courses(
            branch=branch_a.name,
            program_offering=offering_a.name,
            student_group=class_a["name"],
            reference_date="2094-10-05",
        )
        self.assertEqual(
            [row["value"] for row in guided_courses],
            [course.name],
        )

        frappe.set_user(school_admin.name)
        manager_schedule_groups = schedule_student_group_query(
            "Student Group",
            "",
            "name",
            0,
            20,
            {
                BRANCH_FIELD: branch_a.name,
                "reference_date": "2094-10-05",
            },
        )
        self.assertEqual(
            {row[0] for row in manager_schedule_groups},
            {class_a["name"], class_peer["name"]},
        )
        manager_schedule_courses = schedule_course_query(
            "Course",
            "",
            "name",
            0,
            20,
            {
                BRANCH_FIELD: branch_a.name,
                "student_group": class_a["name"],
                "program": program.name,
                "reference_date": "2094-10-05",
            },
        )
        self.assertEqual(
            {row[0] for row in manager_schedule_courses},
            {course.name, extra_course.name},
        )

        frappe.set_user("Administrator")
        room_a = self._insert(
            "Room",
            room_name=f"QA Core A Room {self.suffix}",
            **{BRANCH_FIELD: branch_a.name},
        )
        room_b = self._insert(
            "Room",
            room_name=f"QA Core B Room {self.suffix}",
            **{BRANCH_FIELD: branch_b.name},
        )
        schedule_a = self._make_schedule(
            student_group=class_a["name"],
            instructor=instructor_a,
            course=course,
            room=room_a,
            branch=branch_a,
            from_time="09:00:00",
        )
        schedule_b = self._make_schedule(
            student_group=class_b["name"],
            instructor=instructor_b,
            course=course,
            room=room_b,
            branch=branch_b,
            from_time="11:00:00",
        )

        frappe.set_user(instructor_user.name)
        limited_selector_rows = course_schedule_instructor_query(
            "Instructor",
            "",
            "name",
            0,
            20,
            {
                BRANCH_FIELD: branch_a.name,
                "student_group": class_a["name"],
                "course": course.name,
                "reference_date": "2094-10-05",
            },
        )
        self.assertEqual(
            [row[0] for row in limited_selector_rows],
            [instructor_a.name],
        )

        frappe.set_user(school_admin.name)
        manager_selector_rows = course_schedule_instructor_query(
            "Instructor",
            "",
            "name",
            0,
            20,
            {
                BRANCH_FIELD: branch_a.name,
                "student_group": class_a["name"],
                "course": course.name,
                "reference_date": "2094-10-05",
            },
        )
        self.assertEqual(
            {row[0] for row in manager_selector_rows},
            {instructor_a.name, peer_instructor.name},
        )

        frappe.set_user(instructor_user.name)
        visible_schedules = frappe.get_list(
            "Course Schedule",
            filters={"name": ["in", [schedule_a.name, schedule_b.name]]},
            pluck="name",
            page_length=10,
        )
        self.assertEqual(visible_schedules, [schedule_a.name])
        teaching_context = get_teaching_schedule_context(
            branch=branch_a.name,
            reference_date="2094-10-05",
            view="day",
        )
        self.assertEqual(
            [row["name"] for row in teaching_context["schedules"]],
            [schedule_a.name],
        )

        self.assertEqual(
            frappe.get_list(
                "Student Group",
                filters={"name": class_a["name"]},
                pluck="name",
                page_length=10,
            ),
            [class_a["name"]],
        )
        self.assertEqual(
            frappe.get_list(
                "Student",
                filters={"name": student.name},
                pluck="name",
                page_length=10,
            ),
            [student.name],
        )
        self.assertEqual(
            frappe.get_list(
                "Program Enrollment",
                filters={"name": enrollment.name},
                pluck="name",
                page_length=10,
            ),
            [enrollment.name],
        )

        exact_capabilities = get_instructor_assignment_capability_state(
            user=instructor_user.name,
            school_branch=branch_a.name,
            program_offering=offering_a.name,
            student_group=class_a["name"],
            course=course.name,
            on_date="2094-10-05",
        )
        self.assertEqual(exact_capabilities["identity_status"], "resolved")
        self.assertEqual(exact_capabilities["instructor"], instructor_a.name)
        self.assertTrue(exact_capabilities["can_view_subject_content"])
        self.assertTrue(exact_capabilities["can_enter_marks"])

        wrong_subject_capabilities = get_instructor_assignment_capability_state(
            user=instructor_user.name,
            school_branch=branch_a.name,
            program_offering=offering_a.name,
            student_group=class_a["name"],
            course=extra_course.name,
            on_date="2094-10-05",
        )
        self.assertFalse(wrong_subject_capabilities["can_view_subject_content"])
        self.assertFalse(wrong_subject_capabilities["can_enter_marks"])

        register = get_attendance_register(
            class_a["name"],
            "2094-10-05",
            schedule_a.name,
        )
        self.assertEqual(register["course_schedule"]["name"], schedule_a.name)
        self.assertEqual(
            [row["student"] for row in register["students"]],
            [student.name],
        )

        legacy_tool_rows = get_student_attendance_records(
            "Course Schedule",
            course_schedule=schedule_a.name,
        )
        self.assertEqual(
            [row["student"] for row in legacy_tool_rows],
            [student.name],
        )
        legacy_group_rows = get_student_attendance_records(
            "Student Group",
            date="2094-10-05",
            student_group=class_a["name"],
        )
        self.assertEqual(
            [row["student"] for row in legacy_group_rows],
            [student.name],
        )
        with self.assertRaises(frappe.PermissionError):
            get_student_attendance_records(
                "Course Schedule",
                course_schedule=schedule_b.name,
            )

        save_result = save_attendance_register(
            class_a["name"],
            "2094-10-05",
            [{"student": student.name, "status": "Present"}],
            schedule_a.name,
            submit=0,
        )
        self.assertEqual(save_result["created"], 1)
        self.assertEqual(save_result["course_schedule"], schedule_a.name)

        with self.assertRaises(frappe.PermissionError):
            get_attendance_register(
                class_b["name"],
                "2094-10-05",
                schedule_b.name,
            )

        # Native Student Attendance must apply the same exact Course Schedule
        # ownership boundary as the EdgeSuite attendance register.
        native_attendance = frappe.new_doc("Student Attendance")
        native_attendance.student = student.name
        native_attendance.student_group = class_a["name"]
        native_attendance.date = "2094-10-05"
        native_attendance.status = "Present"
        # The register flow already created this Student/session row above. Native
        # validation must first resolve and authorize the exact schedule, then the
        # existing duplicate guard remains authoritative.
        with self.assertRaises(frappe.DuplicateEntryError):
            before_validate_student_attendance(native_attendance)
        self.assertEqual(native_attendance.course_schedule, schedule_a.name)

        unscheduled_attendance = frappe.new_doc("Student Attendance")
        unscheduled_attendance.student = student.name
        unscheduled_attendance.student_group = class_a["name"]
        unscheduled_attendance.date = "2094-10-06"
        unscheduled_attendance.status = "Present"
        with self.assertRaises(frappe.PermissionError):
            before_validate_student_attendance(unscheduled_attendance)

        foreign_schedule_attendance = frappe.new_doc("Student Attendance")
        foreign_schedule_attendance.student = student.name
        foreign_schedule_attendance.student_group = class_b["name"]
        foreign_schedule_attendance.course_schedule = schedule_b.name
        foreign_schedule_attendance.date = "2094-10-05"
        foreign_schedule_attendance.status = "Present"
        with self.assertRaises(frappe.PermissionError):
            before_validate_student_attendance(foreign_schedule_attendance)

        # Ambiguous teaching identity must fail closed everywhere, not just at
        # document-level Course Schedule permission checks.
        frappe.set_user("Administrator")
        ambiguous_employee = self._insert(
            "Employee",
            naming_series="HR-EMP-",
            first_name="QA Ambiguous Instructor",
            company=self.company,
            create_user_permission=0,
            date_of_birth="1991-06-09",
            date_of_joining="2021-01-01",
            department=department.name,
            gender="Female",
            status="Active",
        )
        self._make_instructor(
            institution,
            "Ambiguous Alpha",
            employee=ambiguous_employee,
        )
        # Simulate a legacy/data-integrity anomaly without weakening normal Instructor
        # or Employee validation: one User resolves through two active Employees.
        frappe.db.set_value(
            "Employee",
            ambiguous_employee.name,
            "user_id",
            instructor_user.name,
            update_modified=False,
        )
        frappe.clear_cache(user=instructor_user.name)

        frappe.set_user(instructor_user.name)
        self.assertEqual(
            frappe.get_list(
                "Course Schedule",
                filters={"name": schedule_a.name},
                pluck="name",
                page_length=10,
            ),
            [],
        )
        self.assertEqual(
            frappe.get_list(
                "Student",
                filters={"name": student.name},
                pluck="name",
                page_length=10,
            ),
            [],
        )
        with self.assertRaises(frappe.PermissionError):
            get_operations_context(
                branch=branch_a.name,
                date="2094-10-05",
                student_group=class_a["name"],
            )
        with self.assertRaises(frappe.PermissionError):
            get_attendance_register(
                class_a["name"],
                "2094-10-05",
                schedule_a.name,
            )

        frappe.set_user("Administrator")
        frappe.db.set_value(
            "Employee",
            ambiguous_employee.name,
            "user_id",
            None,
            update_modified=False,
        )
        frappe.clear_cache(user=instructor_user.name)

        frappe.set_user(instructor_user.name)
        self.assertEqual(
            frappe.get_list(
                "Course Schedule",
                filters={"name": schedule_a.name},
                pluck="name",
                page_length=10,
            ),
            [schedule_a.name],
        )

        # A stale Course Schedule must not keep downstream learner visibility alive
        # after the exact Subject responsibility is no longer effective.
        frappe.set_user("Administrator")
        frappe.db.set_value(
            "EduEdge Instructor Assignment",
            assignment_a.name,
            "enabled",
            0,
            update_modified=False,
        )
        frappe.clear_cache(user=instructor_user.name)

        frappe.set_user(instructor_user.name)
        self.assertEqual(
            frappe.get_list(
                "Course Schedule",
                filters={"name": schedule_a.name},
                pluck="name",
                page_length=10,
            ),
            [],
        )
        self.assertEqual(
            frappe.get_list(
                "Student Group",
                filters={"name": class_a["name"]},
                pluck="name",
                page_length=10,
            ),
            [],
        )
        self.assertEqual(
            frappe.get_list(
                "Student",
                filters={"name": student.name},
                pluck="name",
                page_length=10,
            ),
            [],
        )
        self.assertEqual(
            frappe.get_list(
                "Program Enrollment",
                filters={"name": enrollment.name},
                pluck="name",
                page_length=10,
            ),
            [],
        )
        self.assertEqual(
            frappe.get_list(
                "Student Attendance",
                filters={"course_schedule": schedule_a.name},
                pluck="name",
                page_length=10,
            ),
            [],
        )
        with self.assertRaises(frappe.PermissionError):
            get_attendance_register(
                class_a["name"],
                "2094-10-05",
                schedule_a.name,
            )

        frappe.set_user("Administrator")
        self.assertTrue(frappe.db.exists("Course Schedule", schedule_a.name))
        self.assertTrue(frappe.db.exists("EduEdge Instructor Assignment", assignment_a.name))

        frappe.set_user(school_admin.name)
        governance = get_governance_context()
        governed_branches = {row["name"] for row in governance["branches"]}
        self.assertEqual(governed_branches, {branch_a.name, branch_b.name})
        self.assertNotIn(unrelated_branch.name, governed_branches)

        manager_schedules = frappe.get_list(
            "Course Schedule",
            filters={"name": ["in", [schedule_a.name, schedule_b.name]]},
            pluck="name",
            page_length=10,
        )
        self.assertEqual(set(manager_schedules), {schedule_a.name, schedule_b.name})


if __name__ == "__main__":
    import unittest

    unittest.main()
