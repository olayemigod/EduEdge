from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentCapabilitiesContract(unittest.TestCase):
    def _resolver(self):
        return (APP / "education" / "instructor_assignment_capabilities.py").read_text(encoding="utf-8")

    def _api(self):
        return (APP / "api" / "instructor_assignment_capabilities.py").read_text(encoding="utf-8")

    def _controller(self):
        return (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_instructor_assignment"
            / "eduedge_instructor_assignment.py"
        ).read_text(encoding="utf-8")

    def test_capability_fields_are_explicit_read_only_and_default_fail_closed(self):
        metadata = json.loads(
            (
                APP
                / "eduedge"
                / "doctype"
                / "eduedge_instructor_assignment"
                / "eduedge_instructor_assignment.json"
            ).read_text(encoding="utf-8")
        )
        fields = {row["fieldname"]: row for row in metadata["fields"]}
        for fieldname in (
            "can_view_subject_content",
            "can_manage_subject_topics",
            "can_author_cbt",
            "can_create_assessment_plans",
            "can_enter_marks",
        ):
            self.assertIn(fieldname, fields)
            self.assertEqual(fields[fieldname].get("default"), "0")
            self.assertEqual(fields[fieldname].get("read_only"), 1)
        for fieldname in (
            "capabilities_updated_on",
            "capabilities_updated_by",
            "capabilities_update_reason",
        ):
            self.assertIn(fieldname, fields)
            self.assertEqual(fields[fieldname].get("read_only"), 1)
        self.assertIn("Question review and final approval governance remain separate", fields["capability_section"]["description"])

    def test_identity_resolution_requires_exactly_one_active_instructor_without_granting_access(self):
        source = (APP / "education" / "instructor_scope.py").read_text(encoding="utf-8")
        for token in (
            "def get_active_instructor_names_for_user",
            'filters={"user_id": resolved_user, "status": "Active"}',
            'filters={"employee": ["in", employees], "status": "Active"}',
            "def resolve_exact_instructor_for_user",
            "if len(instructors) == 1",
            "more than one active Instructor",
            "This helper intentionally does not grant access",
        ):
            self.assertIn(token, source)

    def test_capability_resolver_is_exact_effective_and_never_infers_from_branch_eligibility(self):
        source = self._resolver()
        for token in (
            "def get_matching_instructor_capability_assignments",
            '"instructor": instructor',
            '"school_branch": branch',
            '"program_offering": offering',
            '"course": subject',
            '"assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)]',
            '"enabled": 1',
            "getdate(valid_from) > on_date",
            "getdate(valid_to) < on_date",
            "scope == CLASS_SCOPE",
            "scope == CLASS_ARM_SCOPE",
            "assigned_group == student_group",
            'return "ambiguous", "", []',
            "No capability is inferred",
        ):
            self.assertIn(token, source)
        self.assertNotIn("EduEdge Instructor Branch Assignment", source)
        self.assertNotIn("Question Responsibility Assignment", source)

    def test_capability_state_unions_only_matching_exact_assignments(self):
        source = self._resolver()
        for token in (
            "def get_instructor_assignment_capability_state",
            'state["assignment_names"]',
            "for row in rows",
            "for fieldname in CAPABILITY_FIELDS",
            "bool(state[fieldname] or cint(row.get(fieldname)))",
            "def user_has_instructor_assignment_capability",
            "if capability not in CAPABILITY_FIELDS",
        ):
            self.assertIn(token, source)

    def test_manager_update_is_post_only_permission_branch_and_history_safe(self):
        source = self._api()
        for token in (
            '@frappe.whitelist(methods=["POST"])',
            "def update_instructor_assignment_capabilities",
            "_require_assignment_manager()",
            'require_eduedge_access(feature_key="academics", action="update_instructor_assignment_capabilities")',
            'doc.check_permission("write")',
            "assert_branch_access(doc.school_branch)",
            "for update",
            "frappe.db.savepoint(savepoint)",
            "frappe.db.rollback(save_point=savepoint)",
            "Disabled assignments cannot grant operational capabilities.",
            "Only Subject-bearing Instructor Assignments can grant operational capabilities.",
            "Historical End, Replace or Transfer assignments cannot have capabilities changed.",
            "Expired Instructor Assignments cannot have capabilities changed.",
            '"branch_eligibility_changed": False',
        ):
            self.assertIn(token, source)

    def test_operational_capabilities_require_content_visibility_and_are_audited(self):
        source = self._api()
        for token in (
            "View Subject Content must be enabled before operational Subject capabilities can be granted.",
            "doc.capabilities_updated_on = now_datetime()",
            "doc.capabilities_updated_by = frappe.session.user",
            "doc.capabilities_update_reason = resolved_reason",
            "in_eduedge_assignment_capability_update",
            "doc.add_comment(",
            "Instructor Assignment capabilities updated",
            '"action": "already-configured"',
            '"action": "capabilities-updated"',
        ):
            self.assertIn(token, source)

    def test_controller_blocks_direct_capability_mutation_and_class_responsibility_grants(self):
        source = self._controller()
        for token in (
            "CAPABILITY_FIELDS",
            "CAPABILITY_AUDIT_FIELDS",
            "self._validate_capability_state()",
            "in_eduedge_assignment_capability_update",
            "Operational Subject capabilities can be granted only to Subject-bearing Instructor Assignments.",
            "Operational capability fields are maintained by EduEdge assignment capability actions.",
            "View Subject Content must be enabled before operational Subject capabilities can be granted.",
        ):
            self.assertIn(token, source)

    def test_current_user_read_api_is_authenticated_and_context_explicit(self):
        source = self._api()
        for token in (
            "def get_my_instructor_assignment_capabilities",
            'frappe.session.user == "Guest"',
            'require_eduedge_access(feature_key="academics", action="view_my_instructor_assignment_capabilities")',
            "school_branch: str",
            "program_offering: str",
            "course: str",
            "student_group: str | None = None",
            "on_date: str | None = None",
        ):
            self.assertIn(token, source)

    def test_question_review_and_final_approval_governance_is_not_rewritten(self):
        resolver = self._resolver()
        api = self._api()
        combined = resolver + api
        for forbidden in (
            "can_subject_review",
            "can_final_approve",
            "EduEdge Question Responsibility Assignment",
            "save_assignment(",
            "set_enabled(",
        ):
            self.assertNotIn(forbidden, combined)


if __name__ == "__main__":
    unittest.main()
