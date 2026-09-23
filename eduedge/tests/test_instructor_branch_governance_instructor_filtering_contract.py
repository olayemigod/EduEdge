from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
MODAL_API = APP / "api" / "modal_records.py"
NATIVE_FORM = (
    APP
    / "eduedge"
    / "doctype"
    / "eduedge_instructor_branch_assignment"
    / "eduedge_instructor_branch_assignment.js"
)
CONTROLLER = (
    APP
    / "eduedge"
    / "doctype"
    / "eduedge_instructor_branch_assignment"
    / "eduedge_instructor_branch_assignment.py"
)


class TestInstructorBranchGovernanceInstructorFilteringContract(unittest.TestCase):
    def test_quick_editor_only_offers_classified_active_instructors(self):
        source = MODAL_API.read_text(encoding="utf-8")

        for token in (
            "def _instructor_eligibility_options",
            'frappe.has_permission("Instructor", "read")',
            "get_allowed_institutions(company=company)",
            '"status": "Active"',
            'INSTITUTION_FIELD: ["in", sorted(institution_map)]',
            "institution_name",
        ):
            self.assertIn(token, source)

    def test_missing_or_disabled_home_institution_is_not_offered(self):
        source = MODAL_API.read_text(encoding="utf-8")

        self.assertIn("if not institution_map:", source)
        self.assertIn("return []", source)
        self.assertNotIn(
            "if is_instructor_eligibility and company and frappe.get_meta",
            source,
        )

    def test_quick_editor_rejects_stale_or_out_of_scope_instructor_preset(self):
        source = MODAL_API.read_text(encoding="utf-8")

        for token in (
            'doctype == "EduEdge Instructor Branch Assignment" and values.get("instructor")',
            "requested_instructor",
            "_instructor_eligibility_options(",
            'values["instructor"] = ""',
            'values["school_branch"] = ""',
        ):
            self.assertIn(token, source)

    def test_quick_editor_and_native_form_share_same_query_contract(self):
        api = MODAL_API.read_text(encoding="utf-8")
        native = NATIVE_FORM.read_text(encoding="utf-8")

        for token in (
            "def instructor_branch_assignment_instructor_query",
            'frappe.has_permission("EduEdge Instructor Branch Assignment", "create")',
            'frappe.has_permission("EduEdge Instructor Branch Assignment", "write")',
            "_instructor_eligibility_options",
        ):
            self.assertIn(token, api)

        self.assertIn(
            "eduedge.api.modal_records.instructor_branch_assignment_instructor_query",
            native,
        )
        self.assertNotIn('filters: { status: "Active" }', native)

    def test_branch_choices_still_cascade_from_selected_home_institution(self):
        modal = MODAL_API.read_text(encoding="utf-8")
        native = NATIVE_FORM.read_text(encoding="utf-8")

        self.assertIn(
            'institution = frappe.db.get_value("Instructor", instructor, INSTITUTION_FIELD) or institution',
            modal,
        )
        self.assertIn(
            "get_allowed_school_branches(company=company, institution=institution)",
            modal,
        )
        self.assertIn("refreshInstructorInstitution", native)
        self.assertIn(
            'query: "eduedge.api.education.school_branch_query"',
            native,
        )

    def test_backend_still_rejects_invalid_home_institution_combinations(self):
        source = CONTROLLER.read_text(encoding="utf-8")

        for token in (
            "Set the Instructor's Home Institution before enabling or widening Branch Eligibility",
            "The Instructor Home Institution must be enabled before Branch Eligibility can be enabled or widened",
            "School Branch / Campus must belong to the Instructor's Home Institution",
            "Cross-campus eligibility is allowed within the same Institution",
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
