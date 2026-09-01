from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentTitleContract(unittest.TestCase):
    def test_assignment_titles_use_human_readable_academic_labels(self):
        controller = (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_instructor_assignment"
            / "eduedge_instructor_assignment.py"
        ).read_text(encoding="utf-8")
        for token in (
            "def _assignment_target_label",
            '"offering_title"',
            '"eduedge_display_name"',
            '"student_group_name"',
            "def _course_label",
            '"course_name"',
            "target = _assignment_target_label",
            "parts.append(_course_label(self.course))",
        ):
            self.assertIn(token, controller)

    def test_existing_assignment_titles_are_backfilled_idempotently(self):
        patches = (APP / "patches.txt").read_text(encoding="utf-8")
        patch = (
            APP
            / "patches"
            / "v0_9"
            / "normalize_instructor_assignment_titles.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "eduedge.patches.v0_9.normalize_instructor_assignment_titles",
            patches,
        )
        for token in (
            "_assignment_target_label",
            "_course_label",
            '"assignment_title"',
            "update_modified=False",
            'frappe.clear_cache(doctype="EduEdge Instructor Assignment")',
        ):
            self.assertIn(token, patch)
        self.assertNotIn("delete_doc", patch)
        self.assertNotIn("doc.save(", patch)


if __name__ == "__main__":
    unittest.main()
