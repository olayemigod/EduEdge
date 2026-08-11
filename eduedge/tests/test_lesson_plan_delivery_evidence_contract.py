import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestLessonPlanDeliveryEvidenceContract(unittest.TestCase):
    def test_delivery_log_can_link_approved_lesson_plan_and_evidence(self):
        doctype = json.loads((APP / "eduedge" / "doctype" / "eduedge_scheme_delivery_log" / "eduedge_scheme_delivery_log.json").read_text())
        fields = {row["fieldname"]: row for row in doctype["fields"]}
        self.assertEqual(fields["lesson_plan"]["fieldtype"], "Link")
        self.assertEqual(fields["lesson_plan"]["options"], "EduEdge Lesson Plan")
        self.assertEqual(fields["evidence"]["fieldtype"], "Attach")
        self.assertTrue(fields["lesson_plan"].get("read_only"))
        self.assertTrue(fields["evidence"].get("read_only"))

    def test_delivery_api_requires_exact_approved_plan_context_when_plan_is_linked(self):
        source = (APP / "api" / "scheme_delivery.py").read_text(encoding="utf-8")
        for token in (
            'LESSON_DOCTYPE = "EduEdge Lesson Plan"',
            'lesson.status != "Approved"',
            "lesson.scheme_of_work != scheme.name",
            "lesson.scheme_item_reference != item_reference",
            "lesson.school_branch != scheme.school_branch",
            "lesson.program_offering != scheme.program_offering",
            '(lesson.student_group or "") != (scheme.student_group or "")',
            "lesson.course != scheme.course",
            "lesson.instructor != instructor",
            "getdate(lesson.lesson_date) == getdate(delivered_on)",
            "_validate_delivery_lesson_plan",
            "log.lesson_plan = lesson_plan_name",
        ):
            self.assertIn(token, source)

    def test_lesson_plan_options_are_exact_and_bounded_not_all_lesson_plans(self):
        source = (APP / "api" / "scheme_delivery.py").read_text(encoding="utf-8")
        self.assertIn("def _lesson_plan_options", source)
        self.assertIn('"scheme_of_work": scheme.name', source)
        self.assertIn('"scheme_item_reference": item_reference', source)
        self.assertIn('"instructor": instructor', source)
        self.assertIn('"lesson_date": getdate(delivered_on)', source)
        self.assertIn('"status": "Approved"', source)
        self.assertIn("limit_page_length=50", source)
        self.assertIn("get_delivery_lesson_plan_options", source)

    def test_scheme_delivery_ui_surfaces_lesson_plan_and_teaching_evidence(self):
        source = (APP / "public" / "js" / "eduedge_ui" / "components" / "SchemeDeliveryPanel.vue").read_text(encoding="utf-8")
        for token in (
            "Approved Lesson Plan",
            "Teaching Evidence",
            "Attach Evidence",
            "get_delivery_lesson_plan_options",
            "lesson_plan: this.form.lesson_plan || undefined",
            "evidence: this.form.evidence || undefined",
            "new frappe.ui.FileUploader",
            "Open Lesson Plan",
            "Open Evidence",
        ):
            self.assertIn(token, source)
        self.assertNotIn("frappe.db.set_value", source)
        self.assertNotIn("frappe.db.insert", source)

    def test_delivery_history_remains_append_only(self):
        source = (APP / "api" / "scheme_delivery.py").read_text(encoding="utf-8")
        self.assertIn("Delivery history is append-only", source)
        self.assertNotIn("frappe.delete_doc(LOG_DOCTYPE", source)
        self.assertNotIn("frappe.db.set_value(LOG_DOCTYPE", source)


if __name__ == "__main__":
    unittest.main()
