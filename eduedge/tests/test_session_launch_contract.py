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

    def test_academic_sessions_route_uses_same_page_tabs_for_guided_and_manual_modes(self):
        page = (APP / "eduedge/page/eduedge_academic_sessions/eduedge_academic_sessions.js").read_text(encoding="utf-8")
        bundle = (APP / "public/js/eduedge_session_launch.bundle.js").read_text(encoding="utf-8")
        root = (APP / "public/js/eduedge_session_launch/EduEdgeSessionLaunch.vue").read_text(encoding="utf-8")
        panel = (APP / "public/js/eduedge_ui/components/EduEdgeSessionLaunchPanel.vue").read_text(encoding="utf-8")
        for token in (
            'params.get("mode") === "manual"',
            '"eduedge_session_launch.bundle.js"',
            '"eduedge_academic_sessions.bundle.js"',
            "createEduEdgeSessionLaunchApp",
            "createEduEdgeAcademicSessionsApp",
            "Guided Session Launch",
            "Manual Session & Term Management",
            "switchMode",
            "history.replaceState",
            "eduedge:academic-session-tab",
            "removeEventListener",
        ):
            self.assertIn(token, page)
        self.assertIn("createEduEdgeSessionLaunchApp", bundle)
        self.assertIn("<EdgeAppShell", root)
        self.assertIn("EduEdgeSessionLaunchPanel", root)
        self.assertNotIn("<EdgeAppShell", panel)
        for token in (
            "Academic Session Launch",
            "New Academic Session",
            "Add Term to Selected Session",
            "Save & Continue Later",
            "Resume Session Launch",
            "Prepare Session Foundation",
            "Leaving this page does not reset the launch",
            'detail: { mode: "manual" }',
            "EduEdgeSessionStructurePanel",
            "EduEdgeSessionLearnersPanel",
        ):
            self.assertIn(token, panel)
        self.assertNotIn('window.location.href = "/app/eduedge-academic-sessions?mode=manual"', panel)

    def test_session_tabs_live_inside_edgesuite_layout_and_custom_headings_follow_theme(self):
        page = (APP / "eduedge/page/eduedge_academic_sessions/eduedge_academic_sessions.js").read_text(encoding="utf-8")
        for token in (
            "const placeTabs = ($root) =>",
            'find(".edge-page-layout")',
            'children(".edge-page-layout__header")',
            'children(".edge-page-layout__content")',
            "$tabs.insertAfter($header)",
            "$tabs.prependTo($content)",
            "$tabs.detach()",
            ".session-launch-shell,.eduedge-session-mode-host .session-structure-shell{color:var(--text-color)}",
            ".eduedge-session-mode-host h1,.eduedge-session-mode-host h2,.eduedge-session-mode-host h3,.eduedge-session-mode-host h4{color:var(--text-color)!important}",
        ):
            self.assertIn(token, page)
        self.assertNotIn('class="eduedge-session-mode-tabs" role="tablist" aria-label="Academic Session workspace mode">\n\t\t\t<button', page.split("const $host", 1)[1] if "const $host" in page else "")

    def test_launch_steps_are_full_width_and_reviews_open_in_new_tab_with_destination_context(self):
        component = (APP / "public/js/eduedge_ui/components/EduEdgeSessionLaunchPanel.vue").read_text(encoding="utf-8")
        self.assertIn("grid-template-columns:minmax(0,1fr)", component)
        self.assertIn('window.open("about:blank", "_blank")', component)
        self.assertIn('params.set("academic_year", this.targetAcademicYear)', component)
        self.assertIn('params.set("destination_academic_year", this.targetAcademicYear)', component)
        self.assertIn('params.set("source_academic_year", this.sourceAcademicYear)', component)

    def test_guided_navigation_only_opens_review_after_progress_save_succeeds(self):
        component = (APP / "public/js/eduedge_ui/components/EduEdgeSessionLaunchPanel.vue").read_text(encoding="utf-8")
        self.assertIn("const saved = await this.saveCurrentStep(step.key)", component)
        self.assertIn("if (!saved) {", component)
        self.assertIn("reviewTab?.close()", component)
        self.assertNotIn(".finally(() =>", component)

    def test_session_structure_flow_lists_real_rows_and_reuses_validated_creation_services(self):
        api = (APP / "api/session_launch_structure.py").read_text(encoding="utf-8")
        component = (APP / "public/js/eduedge_ui/components/EduEdgeSessionStructurePanel.vue").read_text(encoding="utf-8")
        for token in (
            "def get_session_structure_context",
            "def create_selected_class_intakes",
            "def carry_forward_selected_class_arms",
            "save_programme_offering(",
            "preview_class_arm_session_rollover(",
            "execute_selected_class_arm_session_rollover(",
            '"students_to_carry"',
            '"missing_intakes"',
            '"arms_ready_to_create"',
        ):
            self.assertIn(token, api)
        for token in (
            "Class Structure",
            "intended Classes",
            "Create Selected",
            "Carry Forward Selected",
            "Students to carry automatically",
            "Review Classes in new tab",
            "destination_academic_year",
        ):
            self.assertIn(token, component)
        self.assertNotIn("<EdgeAppShell", component)

    def test_guided_learner_flow_reuses_progression_admission_and_enrollment_services(self):
        api = (APP / "api/session_launch_learners.py").read_text(encoding="utf-8")
        component = (APP / "public/js/eduedge_ui/components/EduEdgeSessionLearnersPanel.vue").read_text(encoding="utf-8")
        launch = (APP / "public/js/eduedge_ui/components/EduEdgeSessionLaunchPanel.vue").read_text(encoding="utf-8")
        for token in (
            "def get_session_learner_context",
            "def get_guided_progression_options",
            "def prepare_guided_progression",
            "def finalize_guided_progression",
            "def create_guided_admission_cycle",
            "def create_guided_enrollment_draft",
            "get_student_progression_page(",
            "get_progression_destination_options(",
            "prepare_progression_batch(",
            "finalize_progression_batch(",
            "save_admission(",
            "save_student_enrollment(",
            "submit=0",
            "Use Student Progression instead",
        ):
            self.assertIn(token, api)
        self.assertNotIn("submit=1", api)
        for token in (
            "Student Progression",
            "Admissions & Enrollment",
            "Prepare Draft",
            "Open Draft",
            "Finalize",
            "Create Admission Cycle",
            "New Enrollment Draft",
            "Returning Students must use Student Progression",
            "Review Applicants in new tab",
            "Review Enrollments in new tab",
            "destination_academic_year",
            "color:var(--text-color)",
        ):
            self.assertIn(token, component)
        self.assertIn('"student_progression", "admissions_enrollment"', launch)
        self.assertIn("EduEdgeSessionLearnersPanel", launch)
        self.assertNotIn("<EdgeAppShell", component)


if __name__ == "__main__":
    unittest.main()
