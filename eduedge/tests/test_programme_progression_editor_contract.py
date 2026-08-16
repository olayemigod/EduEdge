from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestProgrammeProgressionEditorContract(unittest.TestCase):
    def test_programmes_api_exposes_and_saves_progression_fields(self):
        source = (APP / "api/programmes.py").read_text(encoding="utf-8")
        for token in (
            "PROGRAM_PROGRESSION_MODE_FIELD",
            "PROGRAM_SEQUENCE_FIELD",
            "PROGRAM_NEXT_FIELD",
            "PROGRAM_TERMINAL_FIELD",
            "PROGRAM_ALLOW_REPETITION_FIELD",
            "default_progression_mode",
            "get_programme_progression_options",
            'filters: dict[str, Any] = {INSTITUTION_FIELD: institution}',
            'filters["name"] = ["!=", str(programme).strip()]',
            'doc.set(PROGRAM_PROGRESSION_MODE_FIELD',
            'doc.set(PROGRAM_NEXT_FIELD',
            'doc.set(PROGRAM_TERMINAL_FIELD',
            'doc.set(PROGRAM_ALLOW_REPETITION_FIELD',
        ):
            self.assertIn(token, source)
        self.assertIn('@frappe.whitelist(methods=["POST"])\ndef save_programme', source)

    def test_edgesuite_editor_contains_progression_controls_and_cascades(self):
        component = (APP / "public/js/eduedge_programmes/EduEdgeProgrammes.vue").read_text(encoding="utf-8")
        for token in (
            "Academic Progression",
            "Progression Mode",
            "Progression Sequence",
            "Next {{ editorProgrammeSingular }}",
            "Terminal {{ editorProgrammeSingular }}",
            "Allow repetition",
            "loadProgressionOptions",
            "progressionModeChanged",
            "terminalProgressionChanged",
            "openStudentProgression",
            "Student Progression",
            "eduedge.api.programmes.get_programme_progression_options",
            "progression_mode: savedDraft.eduedge_progression_mode",
            "next_program: savedDraft.eduedge_next_program",
            "terminal_program: savedDraft.eduedge_terminal_program",
            "allow_repetition: savedDraft.eduedge_allow_repetition",
        ):
            self.assertIn(token, component)
        self.assertIn('if (!this.isProgramPromotion) this.draft.eduedge_next_program = "";', component)
        self.assertIn('if (Number(this.draft.eduedge_terminal_program || 0)) this.draft.eduedge_next_program = "";', component)

    def test_institution_type_drives_default_progression_mode(self):
        component = (APP / "public/js/eduedge_programmes/EduEdgeProgrammes.vue").read_text(encoding="utf-8")
        self.assertIn('["PRIMARY", "SECONDARY"].includes(type)', component)
        self.assertIn('["TERTIARY", "TRAINING_CENTRE"].includes(type)', component)
        self.assertIn("return PROGRAM_PROMOTION", component)
        self.assertIn("return LEVEL_PROGRESSION", component)
        self.assertIn("return MANUAL_PROGRESSION", component)


if __name__ == "__main__":
    unittest.main()
