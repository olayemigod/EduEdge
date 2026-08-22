from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestTeachingScheduleGuidedCreateContract(unittest.TestCase):
    def test_teaching_schedule_stays_in_edgesuite_for_create(self):
        page = (APP / "public/js/eduedge_teaching_schedule/EduEdgeTeachingSchedule.vue").read_text(encoding="utf-8")
        self.assertIn("TeachingScheduleCreateDialog", page)
        self.assertIn("this.createDialogOpen = true", page)
        self.assertNotIn('window.location.href = "/app/course-schedule/new-course-schedule"', page)
        self.assertNotIn('window.open("/app/course-schedule/new-course-schedule"', page)
        self.assertIn('window.open(`/app/course-schedule/${encodeURIComponent(name)}`, "_blank", "noopener")', page)
        self.assertIn('window.open("/app/course-schedule", "_blank", "noopener")', page)
        self.assertIn("row.course_name || row.course", page)
        self.assertIn("row.instructor_name || row.instructor", page)
        self.assertIn("row.room_name || row.room", page)

    def test_guided_dialog_uses_searchable_cascading_fields_without_native_resource_links(self):
        dialog = (APP / "public/js/eduedge_teaching_schedule/TeachingScheduleCreateDialog.vue").read_text(encoding="utf-8")
        for token in (
            "<EdgeModal",
            "New Teaching Schedule",
            "<EdgeLinkField",
            "search_teaching_schedule_offerings",
            "search_teaching_schedule_class_arms",
            "search_teaching_schedule_courses",
            "search_teaching_schedule_instructors",
            "search_teaching_schedule_rooms",
            "create_teaching_schedule",
            "this.clearStudentGroup()",
            "this.clearCourse()",
            "this.clearInstructor()",
            "Only Subjects configured on the selected Class curriculum are shown.",
            "Only an Instructor with a valid teaching responsibility",
            "Rooms are restricted to the selected Branch / Campus.",
        ):
            self.assertIn(token, dialog)
        self.assertNotIn("/app/course/", dialog.lower())
        self.assertNotIn("/app/instructor/", dialog.lower())
        self.assertNotIn("frappe.new_doc", dialog)

    def test_room_can_be_created_and_selected_without_leaving_schedule_dialog(self):
        dialog = (APP / "public/js/eduedge_teaching_schedule/TeachingScheduleCreateDialog.vue").read_text(encoding="utf-8")
        room_api = (APP / "api/teaching_schedule_rooms.py").read_text(encoding="utf-8")
        for token in (
            "Create New Room",
            "Create & Select Room",
            "roomQuickCreateOpen",
            "roomDraft.room_name",
            "roomDraft.room_number",
            "roomDraft.seating_capacity",
            "eduedge.api.teaching_schedule_rooms.create_teaching_schedule_room",
            "this.draft.room = room?.value || room?.name",
            "Room created and selected",
            "Existing Branch Room selected",
        ):
            self.assertIn(token, dialog)
        for token in (
            'def create_teaching_schedule_room(',
            'frappe.has_permission("Room", "create")',
            '{BRANCH_FIELD: resolved_branch, "room_name": cleaned_name}',
            '"doctype": "Room"',
            'BRANCH_FIELD: resolved_branch',
            '"created": False',
            '"created": True',
            "doc.insert()",
        ):
            self.assertIn(token, room_api)
        self.assertNotIn("ignore_permissions=True", room_api)
        self.assertNotIn("doc.flags.ignore_permissions", room_api)

    def test_create_api_keeps_native_course_schedule_validation_authoritative(self):
        api = (APP / "api/teaching_schedule.py").read_text(encoding="utf-8")
        for token in (
            'def search_teaching_schedule_offerings(',
            'def search_teaching_schedule_class_arms(',
            'def search_teaching_schedule_courses(',
            'def search_teaching_schedule_instructors(',
            'def search_teaching_schedule_rooms(',
            'def create_teaching_schedule(',
            'frappe.has_permission("Course Schedule", "create")',
            '"Program Course"',
            'course_schedule_instructor_query(',
            'room_branch = frappe.db.get_value("Room", room, BRANCH_FIELD)',
            '"doctype": "Course Schedule"',
            'doc.insert()',
        ):
            self.assertIn(token, api)
        self.assertNotIn("doc.insert(ignore_permissions=True)", api)
        self.assertNotIn("doc.flags.ignore_permissions", api)

    def test_schedule_searches_are_bounded_and_context_scoped(self):
        api = (APP / "api/teaching_schedule.py").read_text(encoding="utf-8")
        self.assertIn("MAX_LINK_RESULTS = 50", api)
        self.assertIn('filters={"school_branch": resolved_branch, "academic_year": academic_year, "is_active": 1}', api)
        self.assertIn('filters={BRANCH_FIELD: resolved_branch}', api)
        self.assertIn('filters: dict = {"name": ["in", course_names]}', api)
        self.assertIn("filters=filters", api)
        self.assertIn("_validate_offering_date", api)
        self.assertIn("_schedule_group", api)


if __name__ == "__main__":
    unittest.main()
