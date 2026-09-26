from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
ASSIGNMENTS = APP / "api" / "instructor_assignments.py"
REGISTER = APP / "api" / "instructor_assignment_register.py"
LINK_SEARCH = APP / "api" / "instructor_assignment_link_search.py"
RUNTIME = APP / "api" / "instructor_assignment_runtime.py"


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

    def test_direct_authoring_context_rejects_manager_instructor_outside_current_governed_scope(self):
        source = LINK_SEARCH.read_text(encoding="utf-8")
        availability = source.split("def _assert_search_instructor_available", 1)[1].split(
            "def _offering_available_for_instructor", 1
        )[0]

        for token in (
            "assignments._can_manage_assignments()",
            "assignments._manager_visible_instructor_names(include_history=False)",
            "if resolved not in visible",
            "The selected Instructor is not available to your user.",
        ):
            self.assertIn(token, availability)

    def test_runtime_history_page_rejects_manager_instructor_outside_permitted_history_scope(self):
        source = RUNTIME.read_text(encoding="utf-8")
        selected = source.split("def _selected_instructor", 1)[1].split(
            "@frappe.whitelist()", 1
        )[0]

        for token in (
            "core._can_manage_assignments()",
            "core._manager_visible_instructor_names(include_history=True)",
            "if resolved not in visible",
            "The selected Instructor is not available to your user.",
        ):
            self.assertIn(token, selected)

    def test_assignment_selector_labels_do_not_require_institution_master_read(self):
        source = ASSIGNMENTS.read_text(encoding="utf-8")
        instructor_block = source.split("def _instructors", 1)[1].split(
            "def _period_dates", 1
        )[0]

        self.assertIn("for branch in core._allowed_branches()", instructor_block)
        self.assertIn('branch.get("institution_name")', instructor_block)
        self.assertNotIn('"EduEdge Institution"', instructor_block)

    def test_native_branch_query_revalidates_selected_instructor_before_eligibility_lookup(self):
        source = LINK_SEARCH.read_text(encoding="utf-8")
        native = source.split("def instructor_assignment_branch_query", 1)[1].split(
            "@frappe.whitelist()", 1
        )[0]

        self.assertIn("_assert_search_instructor_available(instructor)", native)
        self.assertIn("eligible_branch_names(resolved_instructor", native)
        self.assertNotIn("eligible_branch_names(instructor, within=allowed.keys())", native)

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
