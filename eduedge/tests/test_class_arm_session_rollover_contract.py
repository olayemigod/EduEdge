from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestClassArmSessionRolloverContract(unittest.TestCase):
    def test_bulk_rollover_is_explicitly_selective_and_single_rollover_exists(self):
        api = (APP / "api/class_arm_session_rollover.py").read_text(encoding="utf-8")
        ui = (APP / "public/js/eduedge_class_arms/EduEdgeClassArms.vue").read_text(encoding="utf-8")

        for endpoint in (
            "preview_class_arm_session_rollover",
            "execute_selected_class_arm_session_rollover",
            "preview_single_class_arm_session_rollover",
            "execute_single_class_arm_session_rollover",
        ):
            self.assertIn(f"def {endpoint}", api)
        self.assertGreaterEqual(api.count('@frappe.whitelist(methods=["POST"])'), 4)
        self.assertIn("class_arm_identities", api)
        self.assertIn("_selected_plan_rows", api)
        self.assertIn("Carry {{ classArmSingular }} Forward", ui)
        self.assertIn("Bulk Carry Class Arms Forward", ui)
        self.assertIn("Select all ready", ui)
        self.assertIn("Clear selection", ui)
        self.assertIn("selected_class_arm_identities", ui)
        self.assertIn("execute_selected_class_arm_session_rollover", ui)

    def test_single_action_rejects_historical_term_bound_class_arms(self):
        api = (APP / "api/class_arm_session_rollover.py").read_text(encoding="utf-8")
        self.assertIn("Historical term-bound Class Arms cannot be carried forward individually", api)
        self.assertIn("if doc.academic_term", api)
        self.assertIn("if cint(doc.disabled)", api)
        self.assertIn("_structural_session_rollover_plan", api)

    def test_rollover_prepares_empty_student_group_structure_and_preserves_lineage(self):
        api = (APP / "api/class_arm_session_rollover.py").read_text(encoding="utf-8")
        create_block = api.split("def _create_destination_group", 1)[1].split("def _single_source_context", 1)[0]
        self.assertIn('frappe.new_doc("Student Group")', create_block)
        self.assertIn("previous_student_group=source_doc.name", create_block)
        self.assertNotIn("_merge_students", create_block)
        self.assertIn("Deliberately leave the destination roster empty", create_block)
        self.assertIn('"student_roster_carried_forward": False', api)
        self.assertIn('"student_progression_required": True', api)
        for forbidden in (
            'frappe.new_doc("Assessment Plan")',
            'frappe.new_doc("Assessment Result")',
            'frappe.new_doc("EduEdge CBT Exam Schedule")',
            'frappe.new_doc("EduEdge CBT Result")',
            'frappe.new_doc("EduEdge CBT Attempt")',
        ):
            self.assertNotIn(forbidden, create_block)

    def test_structural_plan_does_not_depend_on_destination_enrollment_eligibility(self):
        api = (APP / "api/class_arm_session_rollover.py").read_text(encoding="utf-8")
        plan_block = api.split("def _structural_rollover_row", 1)[1].split("def _create_destination_group", 1)[0]
        self.assertNotIn("_eligible_students", plan_block)
        self.assertIn("source_student_count", plan_block)
        self.assertIn("students_pending_progression", plan_block)
        self.assertIn('"eligible_students": []', plan_block)
        self.assertIn('"students_to_carry": 0', plan_block)

    def test_class_arm_rollover_uses_authoritative_academic_session_discovery(self):
        api = (APP / "api/class_arms.py").read_text(encoding="utf-8")
        options_block = api.split("def _academic_year_options", 1)[1].split("@frappe.whitelist()", 1)[0]
        permission_block = api.split("def _assert_year_read", 1)[1].split('@frappe.whitelist(methods=["POST"])', 1)[0]
        self.assertIn("Academic Year is a global academic master", options_block)
        self.assertIn('frappe.has_permission("Academic Year", "read")', options_block)
        self.assertIn("frappe.get_all(", options_block)
        self.assertNotIn("frappe.get_list(", options_block)
        self.assertIn('frappe.has_permission("Academic Year", "read")', permission_block)
        self.assertIn('frappe.db.exists("Academic Year", name)', permission_block)
        self.assertNotIn('frappe.get_doc("Academic Year", name).check_permission("read")', permission_block)

    def test_downstream_history_is_explicitly_not_copied(self):
        api = (APP / "api/class_arm_session_rollover.py").read_text(encoding="utf-8")
        ui = (APP / "public/js/eduedge_class_arms/EduEdgeClassArms.vue").read_text(encoding="utf-8")
        for token in (
            '"assessment_plans_carried_forward": False',
            '"assessment_results_carried_forward": False',
            '"cbt_schedules_carried_forward": False',
            '"cbt_attempts_or_results_carried_forward": False',
        ):
            self.assertIn(token, api)
        self.assertIn("Existing Assessment Plans, Assessment Results, Result Publications, CBT Schedules, attempts and CBT Results remain historical", ui)

    def test_assessment_and_cbt_keep_term_context_below_sessional_student_group(self):
        assessment = (APP / "education/assessment_operations.py").read_text(encoding="utf-8")
        cbt_schedule = (APP / "eduedge/doctype/eduedge_cbt_exam_schedule/eduedge_cbt_exam_schedule.py").read_text(encoding="utf-8")
        result_sync = (APP / "cbt/result_sync.py").read_text(encoding="utf-8")

        # A sessional Student Group has no Academic Term. Assessment/CBT records may
        # still carry their own valid Term; mismatch is checked only when the group
        # itself is a grandfathered term-bound record.
        self.assertIn("if plan_value and group_value and plan_value != group_value", assessment)
        self.assertIn('if self.get(fieldname) and group_value and self.get(fieldname) != group_value', cbt_schedule)
        self.assertIn("if plan.student_group != schedule.student_group or plan.course != schedule.course", result_sync)
        self.assertIn("Assessment Plan class or subject no longer matches the CBT schedule", result_sync)

    def test_execute_replans_before_mutating_destination(self):
        api = (APP / "api/class_arm_session_rollover.py").read_text(encoding="utf-8")
        execute_block = api.split("def execute_selected_class_arm_session_rollover", 1)[1].split("def execute_all_class_arm_session_rollover", 1)[0]
        self.assertIn("_structural_session_rollover_plan", execute_block)
        self.assertIn("_selected_plan_rows", execute_block)
        self.assertIn("_create_destination_group", execute_block)
        self.assertIn("existing = frappe.db.exists", api)
        self.assertIn("for_update=True", api)


if __name__ == "__main__":
    unittest.main()
