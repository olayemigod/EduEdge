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

if __name__ == "__main__":
    unittest.main()