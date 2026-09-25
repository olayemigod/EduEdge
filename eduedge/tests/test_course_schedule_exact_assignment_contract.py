from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestCourseScheduleExactAssignmentContract(unittest.TestCase):
    def test_backend_requires_exact_subject_assignment_context(self):
        source = (APP / "education" / "instructor_assignments.py").read_text(encoding="utf-8")
        for token in (
            "def assert_schedule_instructor_assignment",
            '"program_offering": program_offering',
            '"course": course',
            '"assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)]',
            '"enabled": 1',
            "scope == CLASS_SCOPE",
            "scope == CLASS_ARM_SCOPE and row.student_group == student_group",
            "row.valid_from",
            "row.valid_to",
            "Class responsibilities without a",
            "Subject never authorise a Subject lesson",
        ):
            self.assertIn(token, source)

    def test_backend_keeps_branch_eligibility_as_separate_migration_safe_layer(self):
        branching = (APP / "education" / "branching.py").read_text(encoding="utf-8")
        operations = (APP / "education" / "academic_operations.py").read_text(encoding="utf-8")
        exact = (APP / "education" / "instructor_assignments.py").read_text(encoding="utf-8")
        self.assertIn("_before_validate_course_schedule(doc, method)", branching)
        self.assertIn("assert_schedule_instructor_assignment(doc)", branching)
        self.assertIn("validate_course_schedule_conflicts(doc)", branching)
        self.assertIn("assert_instructor_assignment(", operations)
        self.assertIn('if not frappe.db.exists(ASSIGNMENT_DOCTYPE, {"school_branch": branch}):', exact)

    def test_instructor_link_options_are_exact_and_effective_date_aware(self):
        source = (APP / "api" / "teaching_assignment_options.py").read_text(encoding="utf-8")
        for token in (
            "def course_schedule_instructor_query",
            "assignment.school_branch = %(branch)s",
            "assignment.program_offering = %(program_offering)s",
            "assignment.course = %(course)s",
            "assignment.assignment_type in %(assignment_types)s",
            "assignment.valid_from is null",
            "assignment.valid_to is null",
            "assignment.assignment_scope = %(class_scope)s",
            "assignment.student_group = %(student_group)s",
            "instructor.status = 'Active'",
            "assert_branch_access(branch)",
            "legacy_branch_instructor_query",
        ):
            self.assertIn(token, source)

    def test_limited_instructor_selector_is_self_scoped_in_exact_and_legacy_modes(self):
        source = (APP / "api" / "teaching_assignment_options.py").read_text(encoding="utf-8")
        for token in (
            "is_limited_instructor_user()",
            "resolve_exact_instructor_for_user()",
            "if limited_instructor and not exact_instructor:",
            '"exact_instructor": exact_instructor or None',
            "and instructor.name = %(exact_instructor)s",
            "def _limited_legacy_instructor_query",
            "eligibility_covers_period(",
            "if limited_instructor:",
            "return _limited_legacy_instructor_query(",
        ):
            self.assertIn(token, source)


    def test_first_schedule_student_group_selector_uses_assignment_not_existing_schedule(self):
        source = (APP / "api" / "academic_operations_review.py").read_text(encoding="utf-8")
        helper = source.split("def _limited_schedule_student_group_rows", 1)[1].split(
            "@frappe.whitelist()\n@frappe.validate_and_sanitize_search_inputs\ndef student_group_query",
            1,
        )[0]
        for token in (
            "resolve_exact_instructor_for_user()",
            "eligibility_covers_period(",
            "from `tabEduEdge Instructor Assignment` assignment",
            "assignment.instructor = %(exact_instructor)s",
            "assignment.program_offering = group_row.",
            "assignment.assignment_type in %(assignment_types)s",
            "assignment.enabled = 1",
            "assignment.valid_from is null",
            "assignment.valid_to is null",
            "assignment.student_group = group_row.name",
        ):
            self.assertIn(token, helper)
        self.assertNotIn("`tabCourse Schedule`", helper)

        query = source.split("def student_group_query", 1)[1].split(
            "@frappe.whitelist()\n@frappe.validate_and_sanitize_search_inputs\ndef course_query",
            1,
        )[0]
        self.assertIn("if is_limited_instructor_user():", query)
        self.assertIn("rows = _limited_schedule_student_group_rows(", query)


    def test_limited_subject_selector_matches_exact_assignment_scope(self):
        source = (APP / "api" / "academic_operations_review.py").read_text(encoding="utf-8")
        helper = source.split("def _limited_schedule_course_names", 1)[1].split(
            "@frappe.whitelist()\n@frappe.validate_and_sanitize_search_inputs\ndef course_query",
            1,
        )[0]
        for token in (
            "resolve_exact_instructor_for_user()",
            "eligibility_covers_period(",
            '"program_offering": group.get(OFFERING_FIELD)',
            '"course": ["in", program_course_names]',
            '"assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)]',
            '"enabled": 1',
            "scope == CLASS_SCOPE",
            "scope == CLASS_ARM_SCOPE and row.student_group == student_group",
            "row.valid_from",
            "row.valid_to",
        ):
            self.assertIn(token, helper)

        query = source.split("def course_query", 1)[1]
        self.assertIn("limited_instructor = is_limited_instructor_user()", query)
        self.assertIn("if limited_instructor:", query)
        self.assertIn("course_names = _limited_schedule_course_names(", query)
        self.assertIn("course_reader = frappe.get_all if limited_instructor else frappe.get_list", query)
        self.assertIn('fields=["name", "course_name"]', query)
        self.assertNotIn('"course_code": ["like"', query)
        self.assertNotIn('fields=["name", "course_name", "course_code"]', query)

        form = (APP / "public" / "js" / "education" / "course_schedule.js").read_text(encoding="utf-8")
        course_query = form.split('frm.set_query("course"', 1)[1].split('frm.set_query("instructor"', 1)[0]
        self.assertIn("student_group: frm.doc.student_group", course_query)
        self.assertIn("reference_date: frm.doc.schedule_date", course_query)


    def test_course_schedule_form_cascades_subject_context_into_instructor_options(self):
        source = (APP / "public" / "js" / "education" / "course_schedule.js").read_text(encoding="utf-8")
        self.assertIn("eduedge.api.teaching_assignment_options.course_schedule_instructor_query", source)
        for token in (
            "student_group: frm.doc.student_group",
            "course: frm.doc.course",
            "reference_date: frm.doc.schedule_date",
            "async course(frm)",
            'await frm.set_value("instructor", null)',
            "student_group(frm) { applyStudentGroupChange(frm); }",
        ):
            self.assertIn(token, source)

    def test_refresh_hydrates_saved_schedule_without_clearing_schedule_fields(self):
        source = (APP / "public" / "js" / "education" / "course_schedule.js").read_text(encoding="utf-8")
        self.assertIn("async function hydrateStudentGroupContext(frm)", source)
        self.assertIn("if (frm.doc.student_group) hydrateStudentGroupContext(frm);", source)
        self.assertIn("async function applyStudentGroupChange(frm)", source)
        self.assertIn('const fixedCourse = message.group_based_on === "Course" ? (message.course || null) : null;', source)
        hydrate_body = source.split("async function hydrateStudentGroupContext(frm)", 1)[1].split(
            "async function applyStudentGroupChange(frm)", 1
        )[0]
        self.assertNotIn("frm.set_value", hydrate_body)
        self.assertNotIn("instructor: null", hydrate_body)
        self.assertNotIn("room: null", hydrate_body)



    def test_limited_instructor_list_scope_matches_exact_schedule_ownership(self):
        source = (APP / "education" / "permissions.py").read_text(encoding="utf-8")
        for token in (
            "def _schedule_assignment_condition",
            "Branches that have not adopted Academic Instructor Assignments keep the legacy",
            "from `tabEduEdge Instructor Assignment` branch_assignment",
            "assignment.program_offering = student_group.",
            "assignment.course =",
            "assignment.assignment_type in",
            "assignment.enabled = 1",
            "assignment.valid_from is null",
            "assignment.valid_to is null",
            "from `tabEduEdge Instructor Branch Assignment` eligibility",
            "eligibility.enabled = 1",
            '_schedule_assignment_condition("`tabCourse Schedule`", resolved_user)',
            'where schedule.name = `tabStudent Attendance`.course_schedule',
            'where schedule.student_group = `tabStudent Group`.name',
            'select schedule.name',
            'where schedule.student_group = %s',
            'and ({ownership})',
            'limit 1',
        ):
            self.assertIn(token, source)

        schedule_query = source.split("def course_schedule_query", 1)[1].split(
            "def student_attendance_query", 1
        )[0]
        self.assertNotIn(
            'return _and_conditions(branch_condition, f"`tabCourse Schedule`.instructor in',
            schedule_query,
        )

        result_log = source.split("def result_publication_log_query", 1)[1].split(
            "def report_card_review_query", 1
        )[0]
        self.assertIn(
            '_owned_student_group_condition("publication.student_group", resolved_user)',
            result_log,
        )
        self.assertNotIn("schedule.instructor in", result_log)

        guardian = source.split("def guardian_query", 1)[1].split(
            "def has_education_branch_permission", 1
        )[0]
        self.assertIn('_owned_student_condition("student.name", resolved_user)', guardian)
        self.assertNotIn("schedule.instructor in", guardian)

        derived_scope = source.split("def _has_instructor_student_group_scope", 1)[1].split(
            "def _schedule_assignment_condition", 1
        )[0]
        for token in (
            'ownership = _schedule_assignment_condition("schedule", user)',
            "and ({ownership})",
        ):
            self.assertIn(token, derived_scope)
        self.assertNotIn("schedule.instructor in", derived_scope)

    def test_limited_instructor_identity_must_be_unique_in_list_and_runtime_scope(self):
        permissions = (APP / "education" / "permissions.py").read_text(encoding="utf-8")
        runtime = (APP / "api" / "academic_operations_safe.py").read_text(encoding="utf-8")

        instructor_sql = permissions.split("def _instructor_sql_values", 1)[1].split(
            "def _branch_condition", 1
        )[0]
        self.assertIn("resolve_exact_instructor_for_user(user)", instructor_sql)
        self.assertNotIn("get_user_instructor_names", instructor_sql)

        for token in (
            "resolve_exact_instructor_for_user(required=True)",
            "instructor_names = [exact_instructor] if exact_instructor else []",
            'filters["instructor"] = resolve_exact_instructor_for_user(required=True)',
        ):
            self.assertIn(token, runtime)

if __name__ == "__main__":
    unittest.main()