from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSessionLaunchSubjectQuickCreateContract(unittest.TestCase):
    def test_subject_quick_create_stays_inside_session_launch_and_reuses_canonical_course_save(self):
        panel = (
            APP / "public/js/eduedge_ui/components/EduEdgeSessionDeliveryPanel.vue"
        ).read_text(encoding="utf-8")
        curriculum = (APP / "api/curriculum_management.py").read_text(encoding="utf-8")

        for token in (
            'const SAVE_COURSE_METHOD = "eduedge.api.curriculum_management.save_course"',
            "field.new_doc = () =>",
            "this.quickCreateSubject(row, dialog, field)",
            "quickCreateSubject(row, parentDialog, subjectField)",
            'title: __("New Institution Subject")',
            'primary_action_label: __("Create & Select Subject")',
            "branch: row.branch",
            "program_offering: row.program_offering",
            "course_name: values.course_name",
            'await parentDialog.set_value("subject", course.name)',
            'frappe.show_alert({ message: __("Subject created and selected")',
        ):
            self.assertIn(token, panel)

        quick_create = panel.split("quickCreateSubject(row, parentDialog, subjectField) {", 1)[1].split("assignTeaching()", 1)[0]
        self.assertLess(
            quick_create.index("dialog.hide()"),
            quick_create.index('await parentDialog.set_value("subject", course.name)'),
        )
        self.assertIn("if (dialog.is_visible) dialog.enable_primary_action()", quick_create)

        self.assertIn("def save_course(payload", curriculum)
        self.assertIn("doc.set(INSTITUTION_FIELD, institution)", curriculum)
        self.assertNotIn('frappe.set_route("Form", "Course"', panel)
        self.assertNotIn('window.open("/app/course', panel)


if __name__ == "__main__":
    unittest.main()
