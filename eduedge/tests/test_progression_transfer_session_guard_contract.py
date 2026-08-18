from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestProgressionTransferSessionGuardContract(unittest.TestCase):
    def test_same_session_transfer_is_rejected_before_native_enrollment_validation(self):
        branching = (APP / "education/branching.py").read_text(encoding="utf-8")
        hook = branching.split("def before_validate_program_enrollment", 1)[1].split(
            "def _validate_progression_transfer_session", 1
        )[0]
        guard = branching.split("def _validate_progression_transfer_session", 1)[1].split(
            "def _prepare_native_required_courses_for_progression", 1
        )[0]

        self.assertIn("_validate_progression_transfer_session(doc)", hook)
        self.assertLess(
            hook.index("_validate_progression_transfer_session(doc)"),
            hook.index("validate_program_enrollment(doc)"),
        )
        self.assertIn('doc.get(PROGRESSION_OUTCOME_FIELD) != "Transfer"', guard)
        self.assertIn('source.academic_year == doc.academic_year', guard)
        self.assertIn("Mid-session Branch transfer cannot create a second Program Enrollment", guard)
        self.assertIn("Progression transfer requires a later Academic Session", guard)

    def test_progression_ui_only_offers_later_sessions_for_transfer_destination(self):
        component = (APP / "public/js/eduedge_student_progression/EduEdgeStudentProgression.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("laterAcademicYears()", component)
        self.assertIn('v-for="row in laterAcademicYears"', component)
        self.assertIn('needsDestination() { return ["Promote", "Repeat", "Transfer"]', component)


if __name__ == "__main__":
    unittest.main()
