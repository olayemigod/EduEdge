from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSessionalSchemeLessonAlignmentContract(unittest.TestCase):
    def test_scheme_controller_resolves_term_from_institution_calendar(self):
        controller = (APP / "eduedge/doctype/eduedge_scheme_of_work/eduedge_scheme_of_work.py").read_text(encoding="utf-8")
        self.assertIn("assert_institution_calendar_context", controller)
        self.assertIn("Select the Academic Term / Semester for this Scheme of Work", controller)
        self.assertIn("academic_term=self.academic_term", controller)
        self.assertIn('self.period_start_date = calendar_context.get("period_start_date")', controller)
        self.assertIn('self.period_end_date = calendar_context.get("period_end_date")', controller)
        self.assertIn("if offering.academic_term", controller)
        self.assertIn("resolve_program_offering_period_dates(offering)", controller)

    def test_scheme_term_is_part_of_governed_version_and_duplicate_identity(self):
        controller = (APP / "eduedge/doctype/eduedge_scheme_of_work/eduedge_scheme_of_work.py").read_text(encoding="utf-8")
        self.assertIn('"academic_term",\n\t"version_no"', controller)
        self.assertIn('for fieldname in ("school_branch", "program_offering", "student_group", "course", "academic_term")', controller)
        self.assertIn('"academic_term": self.academic_term or ["is", "not set"]', controller)
        self.assertIn("same Branch, Class, Class Arm, Subject and Academic Term context", controller)

    def test_scheme_save_accepts_term_but_preserves_original_context_authorization(self):
        api = (APP / "api/scheme_of_work_sessional.py").read_text(encoding="utf-8")
        self.assertIn('EDITABLE_FIELDS = (*base.EDITABLE_FIELDS, "academic_term")', api)
        self.assertGreaterEqual(api.count("base._context_authorized(doc, write=True)"), 2)
        first_auth = api.index("base._context_authorized(doc, write=True)")
        editable_loop = api.index("for fieldname in EDITABLE_FIELDS")
        self.assertLess(first_auth, editable_loop)
        self.assertIn("doc.run_method(\"validate\")", api)

    def test_scheme_workbench_exposes_calendar_terms_below_sessional_offering(self):
        api = (APP / "api/scheme_of_work_workbench_sessional.py").read_text(encoding="utf-8")
        self.assertIn("get_enabled_institution_calendar", api)
        self.assertIn("PERIOD_DOCTYPE", api)
        self.assertIn('payload["terms"] = terms', api)
        self.assertIn('payload.setdefault("filters", {})["academic_term"] = requested_term', api)
        self.assertIn('"academic_term": academic_term', api)
        self.assertIn('and requested_term', api)
        self.assertIn("_historical_term_option", api)
        self.assertIn('"historical_scheme": True', api)

    def test_scheme_ui_requires_term_and_uses_sessional_endpoints(self):
        component = (APP / "public/js/eduedge_scheme_of_work/EduEdgeSchemeOfWork.vue").read_text(encoding="utf-8")
        for token in (
            "Term / Semester",
            'v-model="filters.academic_term"',
            "selectedTerm()",
            "scheme_of_work_workbench_sessional.get_scheme_workbench",
            "scheme_of_work_sessional.save_scheme",
            "academic_term: this.filters.academic_term",
            "Programme Offering and Class Arm are session-wide",
        ):
            self.assertIn(token, component)
        self.assertIn("this.filters.academic_term = row.academic_term", component)

    def test_lesson_plan_inherits_exact_scheme_period_and_term(self):
        lesson = (APP / "eduedge/doctype/eduedge_lesson_plan/eduedge_lesson_plan.py").read_text(encoding="utf-8")
        self.assertIn("self.academic_year = scheme.academic_year", lesson)
        self.assertIn("self.academic_term = scheme.academic_term", lesson)
        self.assertIn("start = getdate(self._scheme.period_start_date)", lesson)
        self.assertIn("end = getdate(self._scheme.period_end_date)", lesson)
        self.assertIn("Lesson Date cannot precede the Scheme academic period", lesson)
        self.assertIn("Lesson Date cannot extend beyond the Scheme academic period", lesson)

    def test_class_arm_rollover_does_not_copy_scheme_or_lesson_history(self):
        rollover = (APP / "api/class_arm_session_rollover.py").read_text(encoding="utf-8")
        create_block = rollover.split("def _create_destination_group", 1)[1].split("def _single_source_context", 1)[0]
        self.assertNotIn('frappe.new_doc("EduEdge Scheme of Work")', create_block)
        self.assertNotIn('frappe.new_doc("EduEdge Lesson Plan")', create_block)
        self.assertIn('frappe.new_doc("Student Group")', create_block)


if __name__ == "__main__":
    unittest.main()
