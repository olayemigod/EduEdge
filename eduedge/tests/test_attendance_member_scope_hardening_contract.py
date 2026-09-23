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


if __name__ == "__main__":
    unittest.main()
