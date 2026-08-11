import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSchemeDeliveryContract(unittest.TestCase):
    def test_delivery_log_is_private_append_only_audit_record(self):
        doctype = json.loads((APP / "eduedge" / "doctype" / "eduedge_scheme_delivery_log" / "eduedge_scheme_delivery_log.json").read_text())
        self.assertEqual(doctype.get("permissions"), [])
        fields = {row["fieldname"] for row in doctype["fields"]}
        for fieldname in (
            "scheme_of_work", "scheme_version", "scheme_item_reference", "scheme_item_sequence",
            "delivery_status", "delivered_on", "periods_delivered", "school_branch", "program_offering",
            "student_group", "course", "topic", "instructor", "instructor_assignment", "logged_by", "logged_on",
            "topic_name_snapshot", "learning_objective_snapshot",
        ):
            self.assertIn(fieldname, fields)
        controller = (APP / "eduedge" / "doctype" / "eduedge_scheme_delivery_log" / "eduedge_scheme_delivery_log.py").read_text()
        self.assertIn("append-only", controller)
        self.assertIn("cannot be edited after creation", controller)
        self.assertIn("cannot be deleted", controller)
        self.assertIn("Scheme Item Reference does not belong", controller)

    def test_delivery_requires_approved_scheme_exact_assignment_and_date(self):
        source = (APP / "api" / "scheme_delivery.py").read_text()
        for token in (
            'scheme.status != "Approved"',
            "_resolve_delivery_assignment",
            '"school_branch": scheme.school_branch',
            '"program_offering": scheme.program_offering',
            '"course": scheme.course',
            '"assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)]',
            "_assignment_matches_scope",
            "row.valid_from",
            "row.valid_to",
            "View Subject Content",
            "cannot precede the Scheme academic period",
            "cannot extend beyond the Scheme academic period",
        ):
            self.assertIn(token, source)

    def test_delivery_status_is_governed_and_completion_terminal(self):
        source = (APP / "api" / "scheme_delivery.py").read_text()
        self.assertIn("STATUS_TRANSITIONS", source)
        self.assertIn('"Deferred": {"Resumed"}', source)
        self.assertIn('"Completed": set()', source)
        self.assertIn("This Scheme item is already Completed", source)
        self.assertIn("Delivery history is append-only", source)

    def test_delivery_state_reports_actionable_coverage_without_mutating_scheme(self):
        source = (APP / "api" / "scheme_delivery.py").read_text()
        self.assertIn("def get_scheme_delivery_state", source)
        self.assertIn('"coverage_percent"', source)
        self.assertIn('"completed_items"', source)
        self.assertIn('"pending_items"', source)
        self.assertIn('"periods_delivered"', source)
        self.assertNotIn("scheme.save()", source)
        self.assertNotIn("item.save()", source)

    def test_delivery_ui_uses_scoped_api_and_no_direct_database_writes(self):
        panel = (APP / "public" / "js" / "eduedge_scheme_of_work" / "SchemeDeliveryPanel.vue").read_text()
        root = (APP / "public" / "js" / "eduedge_scheme_of_work" / "EduEdgeSchemeOfWork.vue").read_text()
        self.assertIn("Teaching Progress", panel)
        self.assertIn("append-only", panel)
        self.assertIn("get_scheme_delivery_state", panel)
        self.assertIn("get_delivery_instructor_options", panel)
        self.assertIn("log_scheme_delivery", panel)
        self.assertIn('type: "POST"', panel)
        self.assertIn("SchemeDeliveryPanel", root)
        for forbidden in ("frappe.db.set_value", "frappe.db.insert", "frappe.db.delete_doc"):
            self.assertNotIn(forbidden, panel)


if __name__ == "__main__":
    unittest.main()
