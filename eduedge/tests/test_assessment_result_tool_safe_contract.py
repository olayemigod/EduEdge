from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAssessmentResultToolSafeContract(unittest.TestCase):
    def test_legacy_result_tool_routes_through_governed_endpoints(self):
        hooks = (APP / "hooks.py").read_text(encoding="utf-8")
        source = (APP / "api" / "assessment_result_tool_safe.py").read_text(encoding="utf-8")

        for token in (
            '"education.education.api.get_assessment_students": "eduedge.api.assessment_result_tool_safe.get_assessment_students"',
            '"education.education.api.get_assessment_details": "eduedge.api.assessment_result_tool_safe.get_assessment_details"',
            '"education.education.api.mark_assessment_result": "eduedge.api.assessment_result_tool_safe.mark_assessment_result"',
            '"education.education.api.submit_assessment_results": "eduedge.api.assessment_result_tool_safe.submit_assessment_results"',
            '"Assessment Result Tool": "public/js/education/assessment_result_tool.js"',
        ):
            self.assertIn(token, hooks)

        for token in (
            "def _authorized_plan",
            "_require_academic_operator()",
            "cint(plan.docstatus) != 1",
            "assert_branch_access(branch)",
            '"can_enter_marks"',
            "user_has_instructor_assignment_capability(",
            "on_date=nowdate()",
            "def _active_roster",
            "group_student.active = 1",
            "student.enabled = 1",
            "student.`{BRANCH_FIELD}` = %(branch)s",
            "def _assert_active_student",
            "result.save()",
            "doc.submit()",
        ):
            self.assertIn(token, source)

        for forbidden in (
            "ignore_permissions=True",
            "ignore_permissions = True",
            "frappe.flags.ignore_permissions",
        ):
            self.assertNotIn(forbidden, source)

    def test_tool_plan_selector_uses_current_mark_entry_scope(self):
        client = (APP / "public" / "js" / "education" / "assessment_result_tool.js").read_text(encoding="utf-8")
        options = (APP / "api" / "assessment_assignment_options.py").read_text(encoding="utf-8")
        self.assertIn("assessment_result_plan_query", client)
        plan_query = options.split("def assessment_result_plan_query", 1)[1].split(
            "@frappe.whitelist()\n@frappe.validate_and_sanitize_search_inputs\ndef assessment_result_student_query",
            1,
        )[0]
        self.assertIn('"can_enter_marks"', plan_query)
        self.assertIn("on_date=nowdate()", plan_query)
        self.assertIn("plan.docstatus = 1", plan_query)

    def test_tool_reads_are_plan_authorized_before_raw_roster_or_result_reads(self):
        source = (APP / "api" / "assessment_result_tool_safe.py").read_text(encoding="utf-8")
        students = source.split("def get_assessment_students", 1)[1].split("def get_assessment_details", 1)[0]
        self.assertLess(students.index("_authorized_plan("), students.index("_active_roster("))
        self.assertLess(students.index("_authorized_plan("), students.index('frappe.get_all(\n\t\t"Assessment Result"'))

        mark = source.split("def mark_assessment_result", 1)[1].split("def submit_assessment_results", 1)[0]
        self.assertLess(mark.index("_authorized_plan("), mark.index("_assert_active_student("))
        self.assertIn("result.save()", mark)

        submit = source.split("def submit_assessment_results", 1)[1]
        self.assertLess(submit.index("_authorized_plan("), submit.index("_active_roster("))
        self.assertIn("doc.submit()", submit)


if __name__ == "__main__":
    unittest.main()
