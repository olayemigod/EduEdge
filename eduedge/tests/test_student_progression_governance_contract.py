from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestStudentProgressionGovernanceContract(unittest.TestCase):
    def test_progression_foundation_distinguishes_school_and_tertiary_models(self):
        source = (APP / "education/academic_progression.py").read_text(encoding="utf-8")
        for token in (
            'PROGRAM_PROMOTION = "Program Promotion"',
            'LEVEL_PROGRESSION = "Level Progression"',
            'PROGRAM_PROMOTION_TYPES = {"PRIMARY", "SECONDARY"}',
            'LEVEL_PROGRESSION_TYPES = {"TERTIARY", "TRAINING_CENTRE"}',
            'PROGRAM_NEXT_FIELD = "eduedge_next_program"',
            'PROGRAM_TERMINAL_FIELD = "eduedge_terminal_program"',
            'PROGRESSION_LEVEL_FIELD = "eduedge_progression_level"',
            "_validate_program_cycle",
            "initial_progression_level",
        ):
            self.assertIn(token, source)
        self.assertIn("Primary and Secondary Classes cannot use Level Progression", source)
        self.assertIn("Tertiary and Training Programmes progress through Academic Levels", source)

    def test_progression_prepares_destination_enrollment_as_draft_only(self):
        source = (APP / "api/student_progression.py").read_text(encoding="utf-8")
        prepare = source.split("def _prepare_target_enrollment", 1)[1].split("@frappe.whitelist", 1)[0]
        self.assertIn('frappe.new_doc("Program Enrollment")', prepare)
        self.assertIn("doc.insert()", prepare)
        self.assertNotIn("doc.submit()", prepare)
        self.assertNotIn("target.submit()", prepare)
        self.assertIn('"academic_term": ["is", "not set"]', source)
        self.assertIn("destination Program Enrollments", source)

    def test_finalization_requires_submitted_target_and_append_only_log(self):
        api = (APP / "api/student_progression.py").read_text(encoding="utf-8")
        log = (APP / "eduedge/doctype/eduedge_enrollment_status_log/eduedge_enrollment_status_log.py").read_text(encoding="utf-8")
        self.assertIn("if cint(prepared.docstatus) != 1", api)
        self.assertIn("Submit the prepared destination Program Enrollment before finalising progression", api)
        self.assertIn('"doctype": "EduEdge Enrollment Status Log"', api)
        self.assertIn("Enrollment Status Logs are append-only and cannot be edited", log)
        self.assertIn("Enrollment Status Logs are append-only and cannot be deleted", log)
        self.assertIn("Target Program Enrollment must be submitted before finalising progression", log)

    def test_source_history_is_not_mutated_or_resubmitted(self):
        source = (APP / "api/student_progression.py").read_text(encoding="utf-8")
        self.assertIn("Progression requires a submitted source Program Enrollment", source)
        for forbidden in (
            "source.save(",
            "source.submit(",
            "source.cancel(",
            "frappe.db.set_value(\"Program Enrollment\", source",
        ):
            self.assertNotIn(forbidden, source)

    def test_branch_institution_and_exact_target_context_fail_closed(self):
        source = (APP / "api/student_progression.py").read_text(encoding="utf-8")
        log = (APP / "eduedge/doctype/eduedge_enrollment_status_log/eduedge_enrollment_status_log.py").read_text(encoding="utf-8")
        for token in (
            "assert_branch_access(branch)",
            "Progression and internal transfer must remain within the same Institution",
            "No active sessional Programme Offering matches the destination",
            "More than one destination Programme Offering matches this progression",
            "Destination Class Arm / Group must belong to the destination Programme Offering and Branch",
        ):
            self.assertIn(token, source)
        self.assertIn("Automatic transfer is limited to Branches within the same Institution", log)
        self.assertIn("Target Class Arm / Group must belong to the destination Programme Offering", log)

    def test_results_and_cbt_are_evidence_not_rollover_copies(self):
        source = (APP / "api/student_progression.py").read_text(encoding="utf-8")
        self.assertIn('"submitted_assessment_results"', source)
        self.assertIn('"approved_cbt_results"', source)
        self.assertIn('"pending_cbt_results"', source)
        self.assertIn('"Assessment Result"', source)
        self.assertIn('"EduEdge CBT Result"', source)
        for forbidden in (
            'frappe.new_doc("Assessment Result")',
            'frappe.new_doc("Assessment Plan")',
            'frappe.new_doc("EduEdge CBT Result")',
            'frappe.new_doc("EduEdge CBT Exam Schedule")',
            'frappe.new_doc("EduEdge CBT Attempt")',
        ):
            self.assertNotIn(forbidden, source)

    def test_bulk_and_individual_operator_surface_and_navigation_are_present(self):
        component = (APP / "public/js/eduedge_student_progression/EduEdgeStudentProgression.vue").read_text(encoding="utf-8")
        navigation = (APP / "public/js/eduedge_ui/navigation.js").read_text(encoding="utf-8")
        product_menu = (APP / "public/js/eduedge_product_menu.bundle.js").read_text(encoding="utf-8")
        access = (APP / "access_control.py").read_text(encoding="utf-8")
        route = "/app/eduedge-student-progression"
        for text in ("Select visible", "Review one", "Preview Selected", "Prepare Draft Enrollments", "Finalize Selected"):
            self.assertIn(text, component)
        for source in (navigation, product_menu, access):
            self.assertIn(route, source)
        self.assertIn('item("Student Progression"', product_menu)

    def test_class_arm_rollover_preserves_structural_level_not_student_promotion(self):
        source = (APP / "api/class_arm_session_rollover.py").read_text(encoding="utf-8")
        self.assertIn("PROGRESSION_LEVEL_FIELD", source)
        self.assertIn("source_doc.get(PROGRESSION_LEVEL_FIELD)", source)
        self.assertIn("Class Arm rollover must not silently promote the structure itself", source)

    def test_state_changing_progression_endpoints_are_post_only(self):
        source = (APP / "api/student_progression.py").read_text(encoding="utf-8")
        for endpoint in (
            "preview_progression_batch",
            "prepare_progression_batch",
            "finalize_progression_batch",
        ):
            marker = f"def {endpoint}"
            self.assertIn(marker, source)
            before = source[: source.index(marker)]
            self.assertTrue(before.rstrip().endswith('@frappe.whitelist(methods=["POST"])'))


if __name__ == "__main__":
    unittest.main()
