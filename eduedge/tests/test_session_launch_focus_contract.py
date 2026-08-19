from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSessionLaunchFocusContract(unittest.TestCase):
    def test_session_launch_defaults_to_one_focused_step_with_optional_overview(self):
        component = (
            APP / "public/js/eduedge_ui/components/EduEdgeSessionLaunchPanel.vue"
        ).read_text(encoding="utf-8")
        for token in (
            'aria-label="Session Launch step navigator"',
            'activeStepKey: ""',
            'showAllSteps: false',
            'const savedStep = this.launch.current_step_key || "session_terms"',
            'this.activeStepKey = validStepKeys.has(savedStep)',
            'selectStep(stepKey)',
            'previousStep()',
            'nextStep()',
            'toggleShowAllSteps()',
            '"Show all steps"',
            '"Focus current step"',
            '"Previous"',
            '"Next"',
        ):
            self.assertIn(token, component)

    def test_focused_mode_does_not_mount_every_major_workflow_panel(self):
        component = (
            APP / "public/js/eduedge_ui/components/EduEdgeSessionLaunchPanel.vue"
        ).read_text(encoding="utf-8")
        for token in (
            "showAllSteps || activeStepKey === 'session_terms'",
            "showAllSteps || structureStepActive",
            "showAllSteps || learnerStepActive",
            "showAllSteps || activeStepKey === 'academic_delivery'",
            "visibleFutureOverviewSteps",
        ):
            self.assertIn(token, component)

    def test_structure_and_learner_sibling_cards_are_hidden_for_exact_step_focus(self):
        component = (
            APP / "public/js/eduedge_ui/components/EduEdgeSessionLaunchPanel.vue"
        ).read_text(encoding="utf-8")
        for token in (
            "focus-class_structure",
            "focus-class_intakes",
            "focus-class_arms",
            "focus-student_progression",
            "focus-admissions_enrollment",
            ":deep(.session-structure-card:nth-of-type(2))",
            ":deep(.session-learners-card:nth-of-type(2))",
        ):
            self.assertIn(token, component)

    def test_step_navigation_does_not_change_persisted_progress_until_save(self):
        component = (
            APP / "public/js/eduedge_ui/components/EduEdgeSessionLaunchPanel.vue"
        ).read_text(encoding="utf-8")
        select_block = component.split("selectStep(stepKey) {", 1)[1].split("previousStep()", 1)[0]
        self.assertIn("this.activeStepKey = stepKey", select_block)
        self.assertNotIn("SAVE_METHOD", select_block)
        self.assertIn("this.activeStepKey = stepKey", component.split("async saveCurrentStep(stepKey)", 1)[1])


if __name__ == "__main__":
    unittest.main()
