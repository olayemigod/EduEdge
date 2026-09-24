from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
PROFILE_API = APP / "api" / "instructor_profiles.py"
PEOPLE_GOVERNANCE = APP / "education" / "people_governance.py"
NATIVE_FORM = APP / "public" / "js" / "education" / "instructor.js"
INSTRUCTOR_UI = APP / "public" / "js" / "eduedge_instructors" / "EduEdgeInstructors.vue"
HOOKS = APP / "hooks.py"


class TestInstructorEmployeeInstitutionScopeContract(unittest.TestCase):
    def test_edgesuite_employee_options_exclude_explicit_cross_institution_departments(self):
        source = PROFILE_API.read_text(encoding="utf-8")
        for token in (
            "def _employee_department_scope",
            'filters={"company": company, INSTITUTION_FIELD: institution}',
            'INSTITUTION_FIELD: ["is", "not set"]',
            '"department": ["in", sorted(department_scope)]',
            '"department": ["is", "not set"]',
            "MAX_EMPLOYEE_OPTIONS",
            "Results remain bounded",
        ):
            self.assertIn(token, source)

    def test_employee_save_revalidates_company_and_explicit_department_institution(self):
        source = PROFILE_API.read_text(encoding="utf-8")
        for token in (
            '["status", "company", "department"]',
            "employee_context_changed = bool(",
            'employee != str(doc.get("employee") or "").strip()',
            'institution != str(doc.get(INSTITUTION_FIELD) or "").strip()',
            "employee_department_institution and employee_department_institution != institution",
            "Linked Employee Department must belong to the Instructor's Home Institution.",
        ):
            self.assertIn(token, source)

    def test_native_instructor_form_cascades_department_and_employee_from_home_institution(self):
        source = NATIVE_FORM.read_text(encoding="utf-8")
        hooks = HOOKS.read_text(encoding="utf-8")
        for token in (
            'frm.set_query("department"',
            "instructor_profile_department_query",
            'frm.set_query("employee"',
            "instructor_profile_employee_query",
            "eduedge_institution(frm)",
            "department: null",
            "employee: null",
        ):
            self.assertIn(token, source)
        self.assertIn('"Instructor": "public/js/education/instructor.js"', hooks)

    def test_native_queries_fail_closed_to_allowed_home_institutions(self):
        source = PROFILE_API.read_text(encoding="utf-8")
        for token in (
            "def instructor_profile_department_query",
            "def instructor_profile_employee_query",
            'allowed = {row["name"] for row in _allowed_institutions()}',
            "institution not in allowed",
            '_require_permission("read")',
        ):
            self.assertIn(token, source)

    def test_doc_event_validation_protects_non_edgesuite_writes_and_preserves_legacy_unchanged_mapping(self):
        source = PEOPLE_GOVERNANCE.read_text(encoding="utf-8")
        for token in (
            "_validate_instructor_employee_context(doc, institution)",
            "def _validate_instructor_employee_context",
            "context_changed = bool(",
            "if not context_changed:",
            "Linked Employee must belong to the Home Institution's Company.",
            "Linked Employee Department must belong to the Instructor's Home Institution.",
        ):
            self.assertIn(token, source)

    def test_edgesuite_copy_describes_institution_filtering(self):
        source = INSTRUCTOR_UI.read_text(encoding="utf-8")
        self.assertIn(
            "Employees explicitly classified under another Institution's HR Department are excluded.",
            source,
        )


if __name__ == "__main__":
    unittest.main()
