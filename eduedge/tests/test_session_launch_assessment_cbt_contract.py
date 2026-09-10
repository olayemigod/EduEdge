from pathlib import Path
import ast
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSessionLaunchAssessmentCbtContract(unittest.TestCase):
    def test_readiness_service_is_read_only_and_permission_aware(self):
        path = APP / "api" / "session_launch_assessment.py"
        source = path.read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn("_require_manager", source)
        self.assertIn("_get_launch_by_name", source)
        self.assertIn('_require_manager("get_session_launch_assessment_cbt_readiness")', source)
        self.assertIn('_require_read("Assessment Plan")', source)
        self.assertNotIn('_require_read(LAUNCH_DOCTYPE)', source)
        self.assertNotIn('doc.check_permission("read")', source)
        self.assertIn('"cbt_optional": True', source)
        self.assertIn('"status": "Not Planned"', source)
        self.assertNotIn(".insert(", source)
        self.assertNotIn(".save(", source)
        self.assertNotIn("frappe.db.set_value", source)

    def test_assessment_readiness_requires_submitted_class_arm_coverage(self):
        source = (APP / "api" / "session_launch_assessment.py").read_text(encoding="utf-8")
        self.assertIn('planned_groups = {row.get("student_group") for row in submitted', source)
        self.assertIn('missing_groups = [row for row in class_arms if row["name"] not in planned_groups]', source)
        self.assertIn('missing_examiner = [row for row in submitted if not row.get("examiner_name")]', source)

    def test_configured_cbt_checks_operational_prerequisites(self):
        source = (APP / "api" / "session_launch_assessment.py").read_text(encoding="utf-8")
        for required in (
            'missing.append("Class Arm")',
            'missing.append("Subject")',
            'missing.append("submitted Assessment Plan")',
            'missing.append("Examination Centre")',
            'missing.append("Primary Invigilator")',
            'missing.append("Ready status")',
            'Candidate coverage',
        ):
            self.assertIn(required, source)

    def test_session_launch_embeds_step_eight_panel(self):
        source = (APP / "public" / "js" / "eduedge_ui" / "components" / "EduEdgeSessionLaunchPanel.vue").read_text(encoding="utf-8")
        panel = (APP / "public" / "js" / "eduedge_ui" / "components" / "EduEdgeSessionAssessmentPanel.vue").read_text(encoding="utf-8")
        self.assertIn('import EduEdgeSessionAssessmentPanel from "./EduEdgeSessionAssessmentPanel.vue";', source)
        self.assertIn('"academic_delivery", "assessment_cbt"', source)
        self.assertIn("activeStepKey === 'assessment_cbt'", source)
        self.assertIn('eduedge.api.session_launch_assessment.get_assessment_cbt_readiness', panel)
        self.assertIn('No planned CBT is neutral', panel)
        self.assertIn("$emit('save-step', 'assessment_cbt')", panel)


if __name__ == "__main__":
    unittest.main()
