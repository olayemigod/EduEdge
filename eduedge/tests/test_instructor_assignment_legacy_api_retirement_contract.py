from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentLegacyAPIRetirementContract(unittest.TestCase):
    def test_legacy_public_endpoints_route_to_authoritative_instructor_service(self):
        hooks = (APP / "hooks.py").read_text(encoding="utf-8")
        expected = {
            "eduedge.api.teacher_assignments.get_teacher_assignments_page":
                "eduedge.api.instructor_assignments.get_instructor_assignments_page",
            "eduedge.api.teacher_assignments.preview_teacher_assignment_batch":
                "eduedge.api.instructor_assignments.preview_instructor_assignment_batch",
            "eduedge.api.teacher_assignments.save_teacher_assignment_batch":
                "eduedge.api.instructor_assignments.save_instructor_assignment_batch",
        }
        for legacy, authoritative in expected.items():
            self.assertIn(f'"{legacy}": "{authoritative}"', hooks)

    def test_authoritative_service_keeps_retired_global_payload_fail_closed(self):
        api = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
        for token in (
            "def _rows",
            "previous global Class × Class Arm × Subject assignment format has been retired",
            "use explicit Assignment Rows",
            "def _validate_batch_duplicates",
            "def _primary_conflicts",
            "Valid From cannot be earlier than the selected Class academic period",
            "Valid To cannot be later than the selected Class academic period",
            "Institution Subject will be added to the selected Class curriculum",
        ):
            self.assertIn(token, api)
        self.assertNotIn("skipped.append", api)

    def test_dependency_direction_does_not_create_circular_import(self):
        authoritative = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
        legacy = (APP / "api" / "teacher_assignments.py").read_text(encoding="utf-8")
        self.assertIn("from eduedge.api import teacher_assignments as core", authoritative)
        self.assertNotIn("from eduedge.api import instructor_assignments", legacy)
        self.assertNotIn("import eduedge.api.instructor_assignments", legacy)

    def test_live_assignment_ui_never_calls_legacy_api(self):
        component = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "EduEdgeInstructorAssignments.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("eduedge.api.instructor_assignment_runtime.get_instructor_assignments_page", component)
        self.assertIn("eduedge.api.instructor_assignments.preview_instructor_assignment_batch", component)
        self.assertIn("eduedge.api.instructor_assignments.save_instructor_assignment_batch", component)
        self.assertNotIn("eduedge.api.teacher_assignments", component)


if __name__ == "__main__":
    unittest.main()
