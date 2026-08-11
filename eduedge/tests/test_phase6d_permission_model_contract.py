import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


def _doctype_permissions(relative_path: str) -> dict[str, dict]:
    payload = json.loads((APP / relative_path).read_text(encoding="utf-8"))
    return {row["role"]: row for row in payload.get("permissions") or []}


class TestPhase6DPermissionModelContract(unittest.TestCase):
    def test_academic_administrator_can_read_program_offering_and_manage_assignments(self):
        offering = _doctype_permissions(
            "eduedge/doctype/eduedge_program_offering/eduedge_program_offering.json"
        )
        assignment = _doctype_permissions(
            "eduedge/doctype/eduedge_instructor_assignment/eduedge_instructor_assignment.json"
        )
        self.assertTrue(offering["Academic Administrator"].get("read"))
        for right in ("read", "create", "write", "report"):
            self.assertTrue(assignment["Academic Administrator"].get(right), right)

    def test_teacher_and_instructor_assignment_access_is_read_only_at_doctype_level(self):
        assignment = _doctype_permissions(
            "eduedge/doctype/eduedge_instructor_assignment/eduedge_instructor_assignment.json"
        )
        for role in ("Teacher", "Instructor"):
            self.assertTrue(assignment[role].get("read"))
            self.assertFalse(assignment[role].get("create"))
            self.assertFalse(assignment[role].get("write"))
            self.assertFalse(assignment[role].get("delete"))

    def test_scheme_and_lesson_plan_direct_permissions_remain_management_only(self):
        scheme = _doctype_permissions(
            "eduedge/doctype/eduedge_scheme_of_work/eduedge_scheme_of_work.json"
        )
        lesson = _doctype_permissions(
            "eduedge/doctype/eduedge_lesson_plan/eduedge_lesson_plan.json"
        )
        for permissions in (scheme, lesson):
            self.assertIn("Academic Administrator", permissions)
            self.assertTrue(permissions["Academic Administrator"].get("read"))
            self.assertTrue(permissions["Academic Administrator"].get("write"))
            self.assertNotIn("Teacher", permissions)
            self.assertNotIn("Instructor", permissions)

    def test_routes_are_manifest_gated_while_exact_context_apis_remain_authoritative(self):
        access = (APP / "access_control.py").read_text(encoding="utf-8")
        for token in (
            '"/app/eduedge-instructor-assignments": (("instructor_assignment", "read"),)',
            '"/app/eduedge-schemes-of-work": (("course", "read"),)',
            '"/app/eduedge-lesson-plans": (("instructor_assignment", "read"),)',
            '"/app/eduedge-academic-readiness": (("program_offering", "read"),)',
            "workbench APIs remain the authoritative exact Branch/Class/Subject permission gate",
            "APIs separately enforce exact Instructor identity",
            "API separately enforces academic-management roles and Branch access",
        ):
            self.assertIn(token, access)


if __name__ == "__main__":
    unittest.main()
