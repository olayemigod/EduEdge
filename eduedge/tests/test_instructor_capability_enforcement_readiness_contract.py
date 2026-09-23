from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorCapabilityEnforcementReadinessContract(unittest.TestCase):
    def test_global_switch_is_protected_by_readiness_workflow(self):
        controller = (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_settings"
            / "eduedge_settings.py"
        ).read_text(encoding="utf-8")
        for token in (
            "self._validate_capability_enforcement_change()",
            "def _validate_capability_enforcement_change",
            "get_doc_before_save()",
            "in_eduedge_capability_enforcement_change",
            "must be changed from EduEdge Settings Center after readiness review",
        ):
            self.assertIn(token, controller)

    def test_activation_requires_settings_write_and_full_branch_scope(self):
        source = (APP / "api" / "instructor_assignment_capabilities.py").read_text(encoding="utf-8")
        for token in (
            "GLOBAL_CAPABILITY_ADMIN_ROLES",
            "def _capability_enforcement_has_full_scope",
            'filters={"enabled": 1}',
            "get_allowed_school_branches(user=resolved_user)",
            'frappe.has_permission("EduEdge Settings", "write", user=resolved_user)',
            "visibility across every enabled Branch / Campus",
        ):
            self.assertIn(token, source)

    def test_readiness_blocks_identity_drift_and_unreviewed_current_assignments(self):
        source = (APP / "api" / "instructor_assignment_capabilities.py").read_text(encoding="utf-8")
        for token in (
            "def _limited_instructor_user_rows",
            '"Has Role"',
            "LIMITED_INSTRUCTOR_ROLES",
            "INSTRUCTOR_SCOPE_BYPASS_ROLES",
            "def _identity_readiness",
            "More than one active Employee is linked to this User.",
            "More than one active Instructor resolves from this User.",
            "def _capability_enforcement_readiness",
            '"current_unreviewed_assignments"',
            '"current_branch_eligibility_blockers"',
            "eligibility_covers_period(",
            "Current Subject responsibility has not had its capabilities explicitly reviewed.",
            "Future Subject responsibility has not had its capabilities explicitly reviewed.",
        ):
            self.assertIn(token, source)

    def test_enforcement_change_is_confirmed_post_only_and_fails_closed(self):
        source = (APP / "api" / "instructor_assignment_capabilities.py").read_text(encoding="utf-8")
        for token in (
            '@frappe.whitelist(methods=["POST"])',
            "def set_instructor_assignment_capability_enforcement",
            "_require_capability_enforcement_admin()",
            "if not cint(confirmed)",
            'if target and not readiness.get("ready")',
            "Capability enforcement cannot be enabled until readiness blockers are resolved.",
            "settings.check_permission(\"write\")",
            "frappe.flags.in_eduedge_capability_enforcement_change = True",
            "settings.save()",
        ):
            self.assertIn(token, source)

    def test_settings_center_exposes_special_readiness_surface_not_generic_toggle(self):
        api = (APP / "api" / "settings_center.py").read_text(encoding="utf-8")
        page = (
            APP
            / "public"
            / "js"
            / "eduedge_settings_center"
            / "EduEdgeSettingsCenter.vue"
        ).read_text(encoding="utf-8")
        for token in (
            '"assignment_capabilities": {',
            '"fields": []',
            "get_capability_enforcement_settings_summary()",
            '"capability_enforcement"',
        ):
            self.assertIn(token, api)
        self.assertNotIn('"fieldname": "enforce_instructor_assignment_capabilities"', api)
        for token in (
            "Exact Instructor Assignment capability enforcement",
            "current_unreviewed_assignments",
            "current_branch_eligibility_blockers",
            "get_instructor_assignment_capability_enforcement_readiness",
            "set_instructor_assignment_capability_enforcement",
            'type: "POST"',
            "<EdgeModal",
            "Readiness checks have passed.",
            "Open Instructor Assignments",
        ):
            self.assertIn(token, page)
        self.assertNotIn("frappe.confirm", page)

    def test_explicit_all_zero_capability_policy_can_be_reviewed_and_audited(self):
        api = (APP / "api" / "instructor_assignment_capabilities.py").read_text(encoding="utf-8")
        dialog = (
            APP
            / "public"
            / "js"
            / "eduedge_ui"
            / "components"
            / "InstructorAssignmentCapabilityDialog.vue"
        ).read_text(encoding="utf-8")
        for token in (
            "if before == resolved_capabilities and doc.capabilities_updated_on:",
            "reviewed_without_value_change = not changed",
            '"capabilities-reviewed" if reviewed_without_value_change else "capabilities-updated"',
            "explicitly reviewed with no capability grants",
        ):
            self.assertIn(token, api)
        for token in (
            "needsExplicitReview()",
            "(this.hasChanges || this.needsExplicitReview)",
            "Mark Reviewed",
            'result.action === "capabilities-reviewed"',
        ):
            self.assertIn(token, dialog)

    def test_runtime_identity_fails_closed_on_duplicate_active_employee_mapping(self):
        source = (APP / "education" / "instructor_scope.py").read_text(encoding="utf-8")
        for token in (
            "Exact teaching identity is User -> one active Employee -> one active Instructor.",
            "if len(employees) != 1:",
            "return []",
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
