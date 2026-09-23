from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
API = APP / "api" / "academic_operations.py"
FORM = APP / "public" / "js" / "education" / "student_attendance.js"


class TestAttendanceMemberScopeHardeningContract(unittest.TestCase):
    def test_student_group_member_lookup_requires_record_read_permission(self):
        source = API.read_text(encoding="utf-8")
        block = source.split("def student_group_member_query", 1)[1].split(
            "@frappe.whitelist()\n@frappe.validate_and_sanitize_search_inputs\ndef instructor_query",
            1,
        )[0]

        for token in (
            'group_doc = frappe.get_doc("Student Group", student_group)',
            'group_doc.check_permission("read")',
            "branch = group_doc.get(BRANCH_FIELD)",
            "assert_branch_access(branch)",
            "from `tabStudent Group Student` group_student",
        ):
            self.assertIn(token, block)

        self.assertLess(
            block.index('group_doc.check_permission("read")'),
            block.index("return frappe.db.sql("),
        )
        self.assertNotIn(
            'frappe.db.get_value("Student Group", student_group, BRANCH_FIELD)',
            block,
        )

    def test_native_attendance_student_picker_uses_hardened_member_query(self):
        source = FORM.read_text(encoding="utf-8")
        self.assertIn(
            "eduedge.api.academic_operations.student_group_member_query",
            source,
        )
        self.assertIn("student_group: frm.doc.student_group", source)


    def test_attendance_register_requires_student_group_and_schedule_read_scope(self):
        source = API.read_text(encoding="utf-8")
        block = source.split("def get_attendance_register", 1)[1].split(
            "@frappe.whitelist()\n@guard_eduedge_action",
            1,
        )[0]

        for token in (
            'group = frappe.get_doc("Student Group", student_group)',
            'group.check_permission("read")',
            'is_limited_instructor_user(frappe.session.user)',
            "Limited Instructor attendance must be anchored to an exact Course Schedule.",
            'schedule_doc = frappe.get_doc("Course Schedule", course_schedule)',
            'schedule_doc.check_permission("read")',
        ):
            self.assertIn(token, block)

        self.assertNotIn(
            'frappe.db.get_value(\n\t\t"Student Group"',
            block,
        )
        self.assertNotIn(
            'frappe.db.get_value(\n\t\t\t"Course Schedule"',
            block,
        )

    def test_save_register_reuses_hardened_register_authorization(self):
        source = API.read_text(encoding="utf-8")
        block = source.split("def save_attendance_register", 1)[1].split(
            "@frappe.whitelist()\n@frappe.validate_and_sanitize_search_inputs\ndef student_group_query",
            1,
        )[0]
        self.assertIn(
            "register = get_attendance_register(student_group, date, course_schedule)",
            block,
        )


    def test_attendance_summary_uses_permission_aware_list_query(self):
        source = API.read_text(encoding="utf-8")
        block = source.split("def _get_attendance_summary", 1)[1].split(
            "@frappe.whitelist()\ndef get_attendance_register",
            1,
        )[0]
        self.assertIn('rows = frappe.get_list(', block)
        self.assertIn('"Student Attendance"', block)
        self.assertIn("limit_page_length=0", block)
        self.assertNotIn("frappe.get_all(", block)

    def test_register_write_does_not_ignore_doctype_permissions(self):
        source = API.read_text(encoding="utf-8")
        block = source.split("def save_attendance_register", 1)[1].split(
            "@frappe.whitelist()\n@frappe.validate_and_sanitize_search_inputs\ndef student_group_query",
            1,
        )[0]
        self.assertIn("doc.save()", block)
        self.assertIn("doc.submit()", block)
        self.assertNotIn("ignore_permissions", block)


if __name__ == "__main__":
    unittest.main()
