from pathlib import Path
import ast
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSessionLaunchStepRegistryContract(unittest.TestCase):
    def test_all_current_session_launch_steps_are_registered_as_implemented(self):
        source = (APP / "api" / "session_launch.py").read_text(encoding="utf-8")
        ast.parse(source)
        for key in (
            "session_terms",
            "class_structure",
            "class_intakes",
            "class_arms",
            "student_progression",
            "admissions_enrollment",
            "academic_delivery",
            "assessment_cbt",
            "school_calendar",
            "operational_readiness",
            "final_review",
        ):
            anchor = source.index(f'"key": "{key}"')
            block = source[anchor: source.index("\n\t},", anchor) + 4]
            self.assertIn('"implemented": True', block, key)

    def test_registry_no_longer_describes_future_unimplemented_operations(self):
        source = (APP / "api" / "session_launch.py").read_text(encoding="utf-8")
        self.assertIn("Branch scope, learner placement, academic delivery, Assessment/CBT, calendar and attendance readiness", source)
        self.assertNotIn("Review enabled finance, boarding, transport, pickup, portal and notification capabilities", source)
        self.assertNotIn("Slice 2 will add selective bulk preparation", source)
        self.assertNotIn("Slice 2 will embed the validated rollover planner", source)


if __name__ == "__main__":
    unittest.main()
