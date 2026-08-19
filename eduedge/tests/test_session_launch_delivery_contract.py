from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSessionLaunchDeliveryContract(unittest.TestCase):
    def test_delivery_api_reuses_existing_curriculum_assignment_and_readiness_services(self):
        api = (APP / "api/session_launch_delivery.py").read_text(encoding="utf-8")
        for token in (
            "def get_session_delivery_context",
            "def add_guided_class_subject",
            "def assign_guided_subject_instructor",
            "def assign_guided_class_teacher",
            "add_programme_courses(",
            "save_instructor_assignment_batch(",
            "readiness._expected_contexts",
            "readiness._assignment_matches_context",
            "readiness._select_scheme_for_context",
            '"schedule_ready"',
            '"scheme_status"',
            '"class_responsibility_required"',
            '"academic_delivery_ready"',
            "MAX_TEACHING_CONTEXTS",
            "MAX_SCHEDULE_ROWS",
        ):
            self.assertIn(token, api)
        self.assertNotIn("ignore_permissions=True", api)
        self.assertNotIn("frappe.db.set_value", api)

    def test_delivery_api_keeps_primary_secondary_class_teacher_governance_separate_from_subject_teaching(self):
        api = (APP / "api/session_launch_delivery.py").read_text(encoding="utf-8")
        for token in (
            'CLASS_RESPONSIBILITY_TYPES = ("Class Teacher", "Form Teacher")',
            'CLASS_RESPONSIBILITY_INSTITUTION_TYPES = {"PRIMARY", "SECONDARY"}',
            'return "Subject Instructor"',
            'return "Lecturer"',
            'return "Tutor"',
            "CLASS_ARM_SCOPE if context.get(\"student_group\") else CLASS_SCOPE",
            '"courses": []',
        ):
            self.assertIn(token, api)

    def test_delivery_panel_is_embedded_as_step_seven_and_is_operational(self):
        panel = (APP / "public/js/eduedge_ui/components/EduEdgeSessionDeliveryPanel.vue").read_text(encoding="utf-8")
        launch = (APP / "public/js/eduedge_ui/components/EduEdgeSessionLaunchPanel.vue").read_text(encoding="utf-8")
        for token in (
            "Academic Delivery",
            "Subjects & Class Curriculum",
            "Subject Teaching Assignments",
            "Class Teacher Responsibility",
            "Teaching Schedule & Scheme Readiness",
            "Add Subject",
            "Assign Selected",
            "Review Assignments in new tab",
            "Review Teaching Schedule in new tab",
            "Review Schemes in new tab",
            "this slice audits scheduling readiness but does not generate Course Schedule records",
            "guided_instructor_query",
            "guided_course_query",
            "@emit",
        ):
            if token == "@emit":
                self.assertIn("$emit('save-step', 'academic_delivery')", panel)
            else:
                self.assertIn(token, panel)
        self.assertIn("EduEdgeSessionDeliveryPanel", launch)
        self.assertIn('"academic_delivery"', launch)
        self.assertLess(launch.index("<EduEdgeSessionLearnersPanel"), launch.index("<EduEdgeSessionDeliveryPanel"))
        self.assertLess(launch.index("<EduEdgeSessionDeliveryPanel"), launch.index("futureOverviewSteps"))

    def test_delivery_smart_fields_use_bounded_filtered_link_queries(self):
        api = (APP / "api/session_launch_delivery.py").read_text(encoding="utf-8")
        panel = (APP / "public/js/eduedge_ui/components/EduEdgeSessionDeliveryPanel.vue").read_text(encoding="utf-8")
        for token in (
            "def guided_instructor_query",
            "search_instructors(query=txt",
            "def guided_course_query",
            "search_assignment_courses(",
            'and not row.get("in_program")',
        ):
            self.assertIn(token, api)
        self.assertIn("INSTRUCTOR_QUERY", panel)
        self.assertIn("COURSE_QUERY", panel)
        self.assertIn("program_offering: row.program_offering", panel)
        self.assertNotIn("get_all(\"Instructor\"", panel)
        self.assertNotIn("get_all(\"Course\"", panel)

    def test_timetable_readiness_is_audited_without_copying_or_inventing_historical_schedules(self):
        api = (APP / "api/session_launch_delivery.py").read_text(encoding="utf-8")
        panel = (APP / "public/js/eduedge_ui/components/EduEdgeSessionDeliveryPanel.vue").read_text(encoding="utf-8")
        self.assertIn('"schedule_date": ["between", [start_date, end_date]]', api)
        self.assertIn('"student_group": ["in", group_names]', api)
        self.assertNotIn('frappe.new_doc("Course Schedule")', api)
        self.assertNotIn('frappe.get_doc({"doctype": "Course Schedule"', api)
        self.assertIn("Historical schedules, lesson delivery and results are never copied forward", panel)


if __name__ == "__main__":
    unittest.main()
