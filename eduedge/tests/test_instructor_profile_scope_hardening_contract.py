from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
PROFILE_API = APP / "api" / "instructor_profiles.py"


class TestInstructorProfileScopeHardeningContract(unittest.TestCase):
    def _source(self) -> str:
        return PROFILE_API.read_text(encoding="utf-8")

    def test_direct_detail_requires_current_operational_scope(self):
        source = self._source()

        for token in (
            "def _scoped_branch_names",
            "selected_instructor_name = str(instructor or \"\").strip()",
            "operational_names is not None and selected_instructor_name not in operational_names",
            "The selected Instructor is outside the current Institution / Branch scope.",
            "_instructor_detail(selected_instructor_name, detail_branch_names)",
        ):
            self.assertIn(token, source)

        self.assertLess(
            source.index("selected_instructor_name = str(instructor or \"\").strip()"),
            source.index("_instructor_detail(selected_instructor_name, detail_branch_names)"),
        )

    def test_detail_child_rows_are_filtered_to_visible_branches(self):
        source = self._source()

        for token in (
            "def _instructor_detail(name: str, branch_names: set[str] | None = None)",
            'assignment_filters["school_branch"] = branch_filter',
            'eligibility_filters["school_branch"] = branch_filter',
            '"EduEdge Instructor Assignment"',
            '"EduEdge Instructor Branch Assignment"',
        ):
            self.assertIn(token, source)

        self.assertNotIn(
            'filters={"instructor": doc.name},\n\t\tfields=[\n\t\t\t"name", "assignment_title"',
            source,
        )

    def test_scoped_detail_does_not_leak_primary_branch_from_another_branch(self):
        source = self._source()

        for token in (
            "if branch_names is None:",
            "governed_primary = primary_branch(doc.name)",
            "row.school_branch",
            "if cint(row.enabled) and cint(row.is_primary)",
            "result[INSTRUCTOR_PRIMARY_BRANCH_FIELD] = governed_primary",
        ):
            self.assertIn(token, source)

    def test_existing_profile_write_checks_current_scope_before_mutation(self):
        source = self._source()

        for token in (
            "current_institution = str(doc.get(INSTITUTION_FIELD) or \"\").strip()",
            "current_institution not in allowed_institutions",
            "The selected Instructor is outside your available Institution scope.",
            '_operational_instructor_names("", "", allowed_branch_rows)',
            "The selected Instructor is outside your available academic scope.",
        ):
            self.assertIn(token, source)

        self.assertLess(
            source.index("current_institution = str(doc.get(INSTITUTION_FIELD) or \"\").strip()"),
            source.index("doc.set(INSTITUTION_FIELD, institution)"),
        )

    def test_save_response_is_scoped_to_target_institution_branches(self):
        source = self._source()

        for token in (
            "response_branches = {",
            'if row.get("institution") == institution',
            "return _instructor_detail(doc.name, response_branches)",
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
