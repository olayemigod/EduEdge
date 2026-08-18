from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSessionLaunchContract(unittest.TestCase):
    def test_launch_doctype_persists_resume_state_without_exposing_school_users_directly(self):
        path = APP / "eduedge/doctype/eduedge_academic_session_launch/eduedge_academic_session_launch.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        fields = {row["fieldname"]: row for row in payload["fields"] if row.get("fieldname")}
        for fieldname in (
            "institution",
            "academic_year",
            "source_academic_year",
            "status",
            "current_step_key",
            "current_step_label",
            "started_by",
            "started_on",
            "last_resumed_by",
            "last_resumed_on",
        ):
            self.assertIn(fieldname, fields)
        self.assertEqual(fields["institution"]["options"], "EduEdge Institution")
        self.assertEqual(fields["academic_year"]["options"], "Academic Year")
        self.assertEqual({row["role"] for row in payload["permissions"]}, {"System Manager"})

    def test_launch_api_is_resumable_and_derives_readiness_from_real_records(self):
        api = (APP / "api/session_launch.py").read_text(encoding="utf-8")
        for token in (
            "def get_session_launch_context",
            "def start_or_resume_session_launch",
            "def save_session_launch_progress",
            "def prepare_session_foundation",
            "ensure_institution_calendar",
            '"current_step_key"',
            '"last_resumed_by"',
            '"foundation_progress_percent"',
            '"class_intakes"',
            '"class_arms"',
            "student_progression",
            "admissions_enrollment",
        ):
            self.assertIn(token, api)
        self.assertIn("insert(ignore_permissions=True)", api)
        self.assertIn("_resolve_institution", api)
        self.assertIn("require_eduedge_access", api)

    def test_academic_sessions_mounts_session_launch_as_additive_guided_layer(self):
        page = (APP / "eduedge/page/eduedge_academic_sessions/eduedge_academic_sessions.js").read_text(encoding="utf-8")
        bundle = (APP / "public/js/eduedge_session_launch.bundle.js").read_text(encoding="utf-8")
        component = (APP / "public/js/eduedge_ui/components/EduEdgeSessionLaunchPanel.vue").read_text(encoding="utf-8")
        for token in (
            "eduedge_session_launch.bundle.js",
            "createEduEdgeSessionLaunchApp",
            "eduedge-session-launch-root",
            "Manual Academic Session management remains available below",
        ):
            self.assertIn(token, page)
        self.assertIn("createEduEdgeSessionLaunchApp", bundle)
        self.assertIn("eduedge_ui/components/EduEdgeSessionLaunchPanel.vue", bundle)
        for token in (
            "Academic Session Launch",
            "Save & Continue Later",
            "Resume Session Launch",
            "Prepare Session Foundation",
            "Leaving this page does not reset the launch",
            "current_step_key",
        ):
            self.assertIn(token, component)
        self.assertNotIn("<EdgeAppShell", component)

    def test_guided_navigation_only_leaves_after_progress_save_succeeds(self):
        component = (APP / "public/js/eduedge_ui/components/EduEdgeSessionLaunchPanel.vue").read_text(encoding="utf-8")
        self.assertIn("const saved = await this.saveCurrentStep(step.key)", component)
        self.assertIn("if (!saved) return", component)
        self.assertNotIn(".finally(() =>", component)


if __name__ == "__main__":
    unittest.main()
