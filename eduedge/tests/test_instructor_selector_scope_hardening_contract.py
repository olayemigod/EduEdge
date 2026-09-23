from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
ASSIGNMENTS = APP / "api" / "instructor_assignments.py"
REGISTER = APP / "api" / "instructor_assignment_register.py"
LINK_SEARCH = APP / "api" / "instructor_assignment_link_search.py"


class TestInstructorSelectorScopeHardeningContract(unittest.TestCase):
    def test_manager_authoring_visibility_requires_permitted_enabled_branch_governance(self):
        source = ASSIGNMENTS.read_text(encoding="utf-8")

        for token in (
            "def _manager_visible_instructor_names",
            "allowed = core._allowed_branches()",
            '"EduEdge Instructor Branch Assignment"',
            '"school_branch": ["in", sorted(branch_names)]',
            '"enabled": 1',
            "branch_institution == home",
            "home in enabled_institutions",
        ):
            self.assertIn(token, source)

    def test_authoring_visibility_fails_closed_without_home_institution_or_enabled_institution(self):
        source = ASSIGNMENTS.read_text(encoding="utf-8")

        for token in (
            "if not meta.has_field(INSTITUTION_FIELD):",
            "return set()",
            "home_by_instructor",
            "enabled_institutions",
        ):
            self.assertIn(token, source)

    def test_register_visibility_retains_permitted_history(self):
        assignments = ASSIGNMENTS.read_text(encoding="utf-8")
        register = REGISTER.read_text(encoding="utf-8")

        history_block = assignments.split("if include_history:", 1)[1].split(
            'if not frappe.db.exists("DocType", "EduEdge Instructor Branch Assignment")',
            1,
        )[0]
        self.assertIn('"EduEdge Instructor Branch Assignment"', history_block)
        self.assertIn('"EduEdge Instructor Assignment"', history_block)
        self.assertIn('"school_branch": ["in", sorted(branch_names)]', history_block)
        self.assertIn("_instructors(include_history=True)", register)

    def test_full_page_planner_and_fuzzy_search_use_current_governed_visibility(self):
        assignments = ASSIGNMENTS.read_text(encoding="utf-8")
        search = LINK_SEARCH.read_text(encoding="utf-8")

        self.assertIn("def _instructors(*, include_history: bool = False)", assignments)
        self.assertIn(
            "_manager_visible_instructor_names(include_history=include_history)",
            assignments,
        )
        self.assertIn(
            "assignments._manager_visible_instructor_names(include_history=False)",
            search,
        )

    def test_limited_instructor_selection_remains_self_scoped(self):
        assignments = ASSIGNMENTS.read_text(encoding="utf-8")
        search = LINK_SEARCH.read_text(encoding="utf-8")

        for source in (assignments, search):
            self.assertIn("current_user_instructors()", source)
            self.assertIn('filters["name"] = ["in", own] if own else ["in", ["__none__"]]', source)

    def test_native_instructor_query_keeps_active_governance_revalidation(self):
        source = LINK_SEARCH.read_text(encoding="utf-8")
        native = source.split("def instructor_assignment_instructor_query", 1)[1].split(
            "@frappe.whitelist()", 1
        )[0]

        for token in (
            "search_instructors(",
            '"EduEdge Instructor Branch Assignment"',
            '"enabled": 1',
            "matching_branch",
        ):
            self.assertIn(token, native)


if __name__ == "__main__":
    unittest.main()
