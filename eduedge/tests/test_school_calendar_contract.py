from pathlib import Path
import ast
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSchoolCalendarContract(unittest.TestCase):
    def test_calendar_api_uses_permission_aware_branch_context(self):
        source = (APP / "api" / "school_calendar.py").read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn('require_eduedge_access(feature_key="academics", action="school_calendar")', source)
        self.assertIn("get_allowed_school_branches", source)
        self.assertIn('frappe.has_permission(EVENT_DOCTYPE, "read")', source)
        self.assertIn('frappe.has_permission(EVENT_DOCTYPE, "create")', source)
        self.assertIn('frappe.has_permission(EVENT_DOCTYPE, "write")', source)

    def test_calendar_projects_existing_academic_sources_without_copying_them(self):
        source = (APP / "api" / "school_calendar.py").read_text(encoding="utf-8")
        for helper in (
            "_academic_period_items",
            "_assessment_items",
            "_cbt_items",
            "_school_event_items",
            "_teaching_items",
        ):
            self.assertIn(f"items.extend({helper}", source)
        self.assertIn("if cint(include_teaching):", source)
        self.assertIn('"source_type": source_type', source)

    def test_school_event_form_options_are_context_filtered(self):
        source = (APP / "api" / "school_calendar.py").read_text(encoding="utf-8")
        self.assertIn('filters={"school_branch": branch, "academic_year": academic_year}', source)
        self.assertIn('group_filters: dict = {BRANCH_FIELD: branch, "academic_year": academic_year, "disabled": 0}', source)
        self.assertIn('group_filters["program"] = program', source)

    def test_event_lifecycle_is_governed(self):
        source = (APP / "api" / "school_calendar.py").read_text(encoding="utf-8")
        self.assertIn("STATUS_TRANSITIONS", source)
        self.assertIn('if requested == "Cancelled":', source)
        self.assertIn('doc.check_permission("write")', source)
        self.assertIn('if doc.status in {"Completed", "Archived"}:', source)

    def test_calendar_workspace_has_month_week_agenda_and_teaching_overlay(self):
        source = (APP / "public" / "js" / "eduedge_school_calendar" / "EduEdgeSchoolCalendar.vue").read_text(encoding="utf-8")
        for mode in (
            '{ value: "month", label: "Month" }',
            '{ value: "week", label: "Week" }',
            '{ value: "agenda", label: "Agenda" }',
        ):
            self.assertIn(mode, source)
        self.assertIn("Show Teaching Schedule", source)
        self.assertIn("New School Event", source)
        self.assertIn('active-route="/app/eduedge-school-calendar"', source)

    def test_calendar_is_registered_in_navigation_and_access_manifest(self):
        navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text(encoding="utf-8")
        access = (APP / "access_control.py").read_text(encoding="utf-8")
        self.assertGreaterEqual(navigation.count('"/app/eduedge-school-calendar"'), 2)
        self.assertIn('menuItem(__("School Calendar & Events"), "/app/eduedge-school-calendar"', navigation)
        self.assertIn('"school_event": "EduEdge School Event"', access)
        self.assertIn('"/app/eduedge-school-calendar": (', access)

    def test_session_launch_uses_live_calendar_and_valid_cbt_handoffs(self):
        launch = (APP / "api" / "session_launch.py").read_text(encoding="utf-8")
        assessment = (APP / "api" / "session_launch_assessment.py").read_text(encoding="utf-8")
        self.assertIn('"key": "school_calendar"', launch)
        self.assertIn('"route": "/app/eduedge-school-calendar"', launch)
        self.assertIn('"route": "/app/eduedge-cbt-schedules"', assessment)
        self.assertNotIn("/app/eduedge-cbt-schedule-operations", assessment)


if __name__ == "__main__":
    unittest.main()
