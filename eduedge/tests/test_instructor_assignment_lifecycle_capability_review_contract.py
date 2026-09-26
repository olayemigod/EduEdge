from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentLifecycleCapabilityReviewContract(unittest.TestCase):
    def test_shared_successor_review_state_is_explicit_and_fail_closed(self):
        source = (
            APP / "education" / "instructor_assignment_capabilities.py"
        ).read_text(encoding="utf-8")

        helper = source.split("def successor_capability_review_state", 1)[1].split(
            "def _blank_state", 1
        )[0]
        for token in (
            "COURSE_REQUIRED_TYPES",
            "capabilities_updated_on",
            "assignment_capability_enforcement_enabled()",
            '"applicable": applicable',
            '"pending": pending',
            '"reviewed": bool(applicable and reviewed_on)',
            '"capabilities_inherited": False',
            '"enforcement_enabled": enforcement_enabled',
            '"reviewed_on": str(reviewed_on or "")',
            "Operational capabilities are not inherited from the source assignment.",
        ):
            self.assertIn(token, helper)

        self.assertIn(
            "applicable = bool(resolved_type in COURSE_REQUIRED_TYPES and resolved_course)",
            helper,
        )
        self.assertIn("pending = bool(applicable and not reviewed_on)", helper)

    def test_replace_transfer_and_prepare_report_review_in_preview_replay_and_commit(self):
        cases = {
            "instructor_assignment_replacement.py": (
                "_replacement_plan",
                "_already_replaced",
                "replace_instructor_assignment",
            ),
            "instructor_assignment_transfer.py": (
                "_transfer_plan",
                "_already_transferred",
                "transfer_instructor_assignment",
            ),
            "instructor_assignment_preparation.py": (
                "_preparation_plan",
                "_existing_preparation",
                "prepare_instructor_assignment_for_next_period",
            ),
        }

        for filename, functions in cases.items():
            source = (APP / "api" / filename).read_text(encoding="utf-8")
            self.assertIn(
                "from eduedge.education.instructor_assignment_capabilities import successor_capability_review_state",
                source,
            )
            self.assertGreaterEqual(source.count('"capability_review": successor_capability_review_state('), 3)
            for function_name in functions:
                self.assertIn(f"def {function_name}", source)

    def test_lifecycle_successors_do_not_copy_operational_capabilities(self):
        capability_fields = (
            "can_view_subject_content",
            "can_manage_subject_topics",
            "can_author_cbt",
            "can_create_assessment_plans",
            "can_enter_marks",
        )
        for filename in (
            "instructor_assignment_replacement.py",
            "instructor_assignment_transfer.py",
            "instructor_assignment_preparation.py",
        ):
            source = (APP / "api" / filename).read_text(encoding="utf-8")
            for fieldname in capability_fields:
                self.assertNotIn(f".{fieldname} =", source)
                self.assertNotIn(f'.set("{fieldname}"', source)
            self.assertNotIn("CAPABILITY_FIELDS", source)

    def test_preparation_replay_reads_capability_review_audit_state(self):
        source = (
            APP / "api" / "instructor_assignment_preparation.py"
        ).read_text(encoding="utf-8")
        existing = source.split("def _existing_preparation", 1)[1].split(
            "def _preparation_plan", 1
        )[0]
        self.assertIn('"assignment_type"', existing)
        self.assertIn('"capabilities_updated_on"', existing)
        self.assertIn('"capability_review": successor_capability_review_state(row)', existing)

    def test_lifecycle_dialogs_surface_preview_and_completion_follow_up(self):
        cases = {
            "InstructorAssignmentReplacementDialog.vue": "Review the successor assignment's capabilities before operational use.",
            "InstructorAssignmentTransferDialog.vue": "Review the successor assignment's capabilities before operational use.",
            "InstructorAssignmentPreparationDialog.vue": "Review the future assignment's capabilities before its responsibility period begins.",
        }
        root = APP / "public" / "js" / "eduedge_ui" / "components"
        for filename, follow_up in cases.items():
            source = (root / filename).read_text(encoding="utf-8")
            for token in (
                "previewPlan.capability_review?.pending",
                "Capability review required",
                "Operational capabilities are not inherited from the source assignment.",
                "result.capability_review?.pending",
                follow_up,
            ):
                self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
