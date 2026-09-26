from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAssessmentAssignmentSmartFiltersContract(unittest.TestCase):
    def _api(self):
        return (APP / "api" / "assessment_assignment_options.py").read_text(encoding="utf-8")

    def _client(self):
        return (APP / "public" / "js" / "education" / "assessment_plan.js").read_text(encoding="utf-8")

    def test_student_group_query_preserves_existing_behavior_until_capability_enforcement_is_enabled(self):
        source = self._api()
        for token in (
            "def assessment_plan_student_group_query",
            "if not (is_teacher_user() and assignment_capability_enforcement_enabled()):",
            "return student_group_query(doctype, txt, searchfield, start, page_len, filters)",
        ):
            self.assertIn(token, source)

    def test_enforced_student_group_query_is_exact_assignment_and_schedule_date_aware(self):
        source = self._api()
        for token in (
            "getdate(filters.get(\"schedule_date\") or nowdate())",
            "def _capability_group_names",
            '"can_create_assessment_plans"',
            "school_branch=branch",
            "on_date=reference_date",
            "row.get(\"assignment_scope\") == CLASS_SCOPE",
            "row.get(\"assignment_scope\") == CLASS_ARM_SCOPE",
            "allowed_groups",
        ):
            self.assertIn(token, source)

    def test_enforced_class_selector_bootstraps_before_any_course_schedule_exists(self):
        source = self._api()
        helper = source.split("def _capability_group_names", 1)[1].split(
            "@frappe.whitelist()",
            1,
        )[0]
        self.assertIn("get_user_capability_assignment_rows(", helper)
        self.assertIn("eligibility", (APP / "education" / "instructor_assignment_capabilities.py").read_text(encoding="utf-8"))
        self.assertIn('groups = frappe.get_all(', helper)
        self.assertNotIn('groups = frappe.get_list(', helper)

        selector = source.split("def assessment_plan_student_group_query", 1)[1].split(
            "@frappe.whitelist()\n@frappe.validate_and_sanitize_search_inputs\ndef assessment_plan_course_query",
            1,
        )[0]
        self.assertIn("allowed_groups = _capability_group_names(", selector)
        self.assertIn('rows = frappe.get_all(', selector)
        self.assertNotIn('rows = frappe.get_list(', selector)


    def test_course_query_cascades_from_group_offering_curriculum_and_exact_capability(self):
        source = self._api()
        for token in (
            "def assessment_plan_course_query",
            'student_group = str(filters.get("student_group")',
            "offering = _resolve_group_offering(group)",
            '"Program Course"',
            '"parent": group.program',
            "curriculum_courses &= set(allowed_courses)",
            '"can_create_assessment_plans"',
            "row.get(\"program_offering\") == offering",
            "_row_covers_group(row, student_group)",
        ):
            self.assertIn(token, source)

    def test_enforced_subject_selector_does_not_require_independent_view_capability(self):
        source = self._api()
        query = source.split("def assessment_plan_course_query", 1)[1]
        for token in (
            "capability_scoped = is_teacher_user() and assignment_capability_enforcement_enabled()",
            '"can_create_assessment_plans"',
            "curriculum_courses &= set(allowed_courses)",
            "course_reader = frappe.get_all if capability_scoped else frappe.get_list",
            "return course_reader(",
        ):
            self.assertIn(token, query)
        self.assertIn("can_view_subject_content", query)
        self.assertIn("independent can_view_subject_content capability", query)


    def test_assessment_criteria_api_fails_closed_without_exact_context_and_reloads_safely(self):
        source = self._api()
        criteria = source.split("def get_assessment_plan_criteria", 1)[1].split(
            "@frappe.whitelist()\n@frappe.validate_and_sanitize_search_inputs\ndef assessment_result_plan_query",
            1,
        )[0]
        for token in (
            "capability_scoped = is_teacher_user() and assignment_capability_enforcement_enabled()",
            "if not group_name or not branch:",
            "return []",
            '"can_create_assessment_plans"',
            "require_instructor_assignment_capability(",
            "student_group=group_name",
            "on_date=getdate(schedule_date or nowdate())",
            'frappe.get_doc("Course", subject).check_permission("read")',
            '"Course Assessment Criteria"',
        ):
            self.assertIn(token, criteria)

        hooks = (APP / "hooks.py").read_text(encoding="utf-8")
        self.assertIn(
            '"education.education.api.get_assessment_criteria": "eduedge.api.assessment_assignment_options.get_assessment_plan_criteria"',
            hooks,
        )

        client = self._client()
        for token in (
            "function load_eduedge_assessment_criteria(frm)",
            "frappe.after_ajax(() =>",
            '"eduedge.api.assessment_assignment_options.get_assessment_plan_criteria"',
            "school_branch: context.school_branch",
            "student_group: context.student_group",
            "schedule_date: context.schedule_date",
            'frm.clear_table("assessment_criteria")',
            'frm.add_child("assessment_criteria")',
            "criterion.weightage",
            "load_eduedge_assessment_criteria(frm);",
        ):
            self.assertIn(token, client)


    def test_default_off_teacher_course_query_still_uses_existing_assignment_scope(self):
        source = self._api()
        for token in (
            "else:",
            "allowed_courses = assigned_courses(",
            "branch=branch",
            "program_offering=offering",
            "student_group=student_group",
        ):
            self.assertIn(token, source)

    def test_assessment_result_plan_selector_uses_current_mark_entry_capability(self):
        source = self._api()
        query = source.split("def assessment_result_plan_query", 1)[1]
        for token in (
            "_resolve_branch(filters.get(BRANCH_FIELD))",
            'base_filters = {BRANCH_FIELD: branch, "docstatus": 1}',
            "capability_scoped = is_teacher_user() and assignment_capability_enforcement_enabled()",
            '"can_enter_marks"',
            "school_branch=branch",
            "on_date=nowdate()",
            "assignment_scope",
            "program_offering",
            "plan.student_group",
            "plan.course",
            "plan.docstatus = 1",
            "return frappe.db.sql(",
        ):
            self.assertIn(token, query)
        self.assertNotIn('"can_view_subject_content"', query)

        client = (APP / "public" / "js" / "education" / "assessment_result.js").read_text(encoding="utf-8")
        self.assertIn(
            'query: "eduedge.api.assessment_assignment_options.assessment_result_plan_query"',
            client,
        )
        self.assertIn("eduedge_school_branch: frm.doc.eduedge_school_branch", client)
        self.assertNotIn("docstatus: 1", client)


    def test_assessment_result_student_selector_is_plan_anchored(self):
        source = self._api()
        query = source.split("def assessment_result_student_query", 1)[1]
        for token in (
            'assessment_plan = str(filters.get("assessment_plan")',
            '"Assessment Plan"',
            '["name", "student_group", "course", BRANCH_FIELD, "docstatus"]',
            "int(plan.docstatus or 0) != 1",
            "plan.get(BRANCH_FIELD) != branch",
            "group_student.parent = %(student_group)s",
            "group_student.active = 1",
            "student.enabled = 1",
            '"can_enter_marks"',
            "user_has_instructor_assignment_capability(",
            "on_date=nowdate()",
            'plan_doc.check_permission("read")',
        ):
            self.assertIn(token, query)

        client = (APP / "public" / "js" / "education" / "assessment_result.js").read_text(encoding="utf-8")
        self.assertIn(
            'query: "eduedge.api.assessment_assignment_options.assessment_result_student_query"',
            client,
        )
        self.assertIn("assessment_plan: frm.doc.assessment_plan", client)
        self.assertNotIn("eduedge.api.academic_operations.student_query", client)


    def test_client_cascade_filters_and_clears_invalid_children(self):
        source = self._client()
        for token in (
            "assessment_plan_student_group_query",
            "assessment_plan_course_query",
            "schedule_date: frm.doc.schedule_date",
            "eduedge_school_branch(frm)",
            "academic_year(frm)",
            "academic_term(frm)",
            "student_group(frm)",
            "schedule_date(frm)",
            'frm.set_value("student_group", null)',
            'frm.set_value("course", null)',
        ):
            self.assertIn(token, source)

    def test_assessment_plan_cascade_preserves_stable_context(self):
        source = self._client()

        group_handler = source.split("student_group(frm)", 1)[1].split(
            "course(frm)", 1
        )[0]
        self.assertIn('frm.set_value("course", null)', group_handler)
        self.assertIn('frm.set_value("examiner", null)', group_handler)
        self.assertNotIn('frm.set_value("room", null)', group_handler)
        self.assertNotIn('frm.set_value("supervisor", null)', group_handler)

        date_handler = source.split("schedule_date(frm)", 1)[1]
        self.assertIn('frm.set_value("examiner", null)', date_handler)
        self.assertIn('frm.set_value("supervisor", null)', date_handler)
        self.assertNotIn('frm.set_value("student_group", null)', date_handler)
        self.assertNotIn('frm.set_value("course", null)', date_handler)
        self.assertNotIn('frm.set_value("room", null)', date_handler)


    def test_backend_before_validate_remains_authoritative_over_smart_queries(self):
        operations = (APP / "education" / "assessment_operations.py").read_text(encoding="utf-8")
        for token in (
            "before_validate_assessment_plan",
            "require_course_assignment(",
            'require_instructor_assignment_capability(\n\t\t\t"can_create_assessment_plans"',
            "_validate_linked_context(doc, group)",
        ):
            self.assertIn(token, operations)


if __name__ == "__main__":
    unittest.main()
