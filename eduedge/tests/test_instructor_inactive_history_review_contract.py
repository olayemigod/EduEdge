from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
ASSIGNMENTS = APP / "api" / "instructor_assignments.py"
LINK_SEARCH = APP / "api" / "instructor_assignment_link_search.py"
REGISTER = APP / "api" / "instructor_assignment_register.py"
RUNTIME_API = APP / "api" / "instructor_assignment_runtime.py"
SEARCH_FIELDS = (
    APP
    / "public"
    / "js"
    / "eduedge_instructor_assignments"
    / "InstructorAssignmentSearchFields.vue"
)
PAGE = (
    APP
    / "public"
    / "js"
    / "eduedge_instructor_assignments"
    / "EduEdgeInstructorAssignments.vue"
)
VIEW_FIRST_RUNTIME = APP / "public" / "js" / "eduedge_instructor_assignment_register_filters.bundle.js"


class TestInstructorInactiveHistoryReviewContract(unittest.TestCase):
    def test_manager_history_list_does_not_force_active_status(self):
        source = ASSIGNMENTS.read_text(encoding="utf-8")
        block = source.split("def _instructors(*, include_history: bool = False)", 1)[1].split(
            "def _period_dates", 1
        )[0]

        for token in (
            "_manager_visible_instructor_names(include_history=include_history)",
            "if not include_history:",
            'filters["status"] = "Active"',
        ):
            self.assertIn(token, block)

        manager_branch = block.split("if _can_manage_assignments():", 1)[1].split("else:", 1)[0]
        self.assertIn("if not include_history:", manager_branch)

    def test_history_search_mode_can_return_permitted_inactive_instructors_for_managers(self):
        source = LINK_SEARCH.read_text(encoding="utf-8")
        block = source.split("def search_instructors(", 1)[1].split(
            "def search_assignment_offerings", 1
        )[0]

        for token in (
            "include_history: int | str = 0",
            "history_mode = bool(cint(include_history)) and manager",
            "_manager_visible_instructor_names(include_history=history_mode)",
            "if not history_mode:",
            '"status"',
        ):
            self.assertIn(token, block)

    def test_register_preserves_history_but_disables_planner_for_inactive_selection(self):
        source = REGISTER.read_text(encoding="utf-8")

        for token in (
            "_instructors(include_history=True)",
            'str(selected_instructor.get("status") or "") == "Active"',
            "authoring_available",
            "if instructor and authoring_available",
            "core._list_values(branches) if authoring_available else []",
            "core._list_values(offerings) if authoring_available else []",
            '"authoring_available": authoring_available',
            "register_allowed_names = permitted_names",
        ):
            self.assertIn(token, source)

    def test_runtime_history_page_accepts_permitted_inactive_manager_history_only(self):
        source = RUNTIME_API.read_text(encoding="utf-8")
        selected = source.split("def _selected_instructor", 1)[1].split(
            "@frappe.whitelist()", 1
        )[0]

        for token in (
            "manager = core._can_manage_assignments()",
            "_manager_visible_instructor_names(include_history=True)",
            'filters["status"] = "Active"',
            '"status"',
        ):
            self.assertIn(token, selected)

        manager_branch = selected.split("if manager:", 1)[1].split("else:", 1)[0]
        self.assertNotIn('filters["status"] = "Active"', manager_branch)

        for token in (
            "authoring_available",
            "if resolved_instructor and authoring_available",
            "legacy._list_values(branches) if authoring_available else []",
            '"authoring_available": authoring_available',
        ):
            self.assertIn(token, source)

    def test_combined_instructor_picker_explicitly_requests_history_mode(self):
        fields = SEARCH_FIELDS.read_text(encoding="utf-8")
        page = PAGE.read_text(encoding="utf-8")

        for token in (
            "includeInstructorHistory",
            "include_history: this.includeInstructorHistory ? 1 : 0",
        ):
            self.assertIn(token, fields)
        self.assertIn(':include-instructor-history="true"', page)

    def test_inactive_selected_instructor_is_review_only_in_edgesuite_ui(self):
        page = PAGE.read_text(encoding="utf-8")
        runtime = VIEW_FIRST_RUNTIME.read_text(encoding="utf-8")

        for token in (
            "canAuthorSelectedInstructor()",
            "this.data.authoring_available !== false",
            "Historical Instructor selected.",
            'v-if="canAuthorSelectedInstructor" class="rows-stack"',
            ':disabled="!canAuthorSelectedInstructor"',
        ):
            self.assertIn(token, page)

        for token in (
            "proxy.canAuthorSelectedInstructor",
            'button.textContent = !canAuthor',
            '"Historical Record"',
            "button.disabled = !canAuthor",
            "if (!proxy.canAuthorSelectedInstructor) return;",
            'row.status && row.status !== "Active"',
        ):
            self.assertIn(token, runtime)


if __name__ == "__main__":
    unittest.main()
