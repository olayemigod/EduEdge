from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestUserBranchAccessScopeHardeningContract(unittest.TestCase):
    def test_user_branch_access_has_query_and_document_permission_hooks(self):
        hooks = (APP / "hooks.py").read_text(encoding="utf-8")
        self.assertIn(
            '"EduEdge User Branch Access": "eduedge.education.user_branch_access_permissions.user_branch_access_query"',
            hooks,
        )
        self.assertIn(
            '"EduEdge User Branch Access": "eduedge.education.user_branch_access_permissions.has_user_branch_access_permission"',
            hooks,
        )

    def test_scope_delegation_is_level_preserving_and_fail_closed(self):
        source = (APP / "education" / "user_branch_access_permissions.py").read_text(encoding="utf-8")
        for token in (
            "def get_assignable_access_scope",
            "_get_active_access_rows",
            "ASSIGNMENT_SCOPE_COMPANY",
            "ASSIGNMENT_SCOPE_INSTITUTION",
            "ASSIGNMENT_SCOPE_BRANCH",
            "does not infer broad",
            "def assert_user_branch_access_scope",
            "You cannot grant or change User Branch Access outside your governed access scope",
            "def user_branch_access_query",
            'return "(" + " or ".join(parts) + ")" if parts else "1=0"',
            "def assert_default_branch_change_scope",
            "default Branch outside your governed access scope",
            "def assignable_access_levels",
            'return [ASSIGNMENT_SCOPE_INSTITUTION, ASSIGNMENT_SCOPE_BRANCH]',
            'return [ASSIGNMENT_SCOPE_BRANCH]',
        ):
            self.assertIn(token, source)

    def test_controller_revalidates_scope_before_save(self):
        source = (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_user_branch_access"
            / "eduedge_user_branch_access.py"
        ).read_text(encoding="utf-8")
        self.assertIn("assert_user_branch_access_scope(self)", source)
        self.assertIn("assert_default_branch_change_scope(self)", source)
        self.assertLess(
            source.index("self._validate_scope()"),
            source.index("assert_user_branch_access_scope(self)"),
        )

    def test_quick_editor_does_not_enumerate_global_company_or_user_lists(self):
        source = (APP / "api" / "modal_records.py").read_text(encoding="utf-8")
        for token in (
            "assignable_company_names",
            "assignable_institution_names",
            "manageable_user_names",
            "assignable_access_levels",
            'field["options"] = access_levels',
            'config.get("doctype") == "EduEdge User Branch Access"',
            'filters["name"] = ["in", sorted(assignable)]',
            'filters["name"] = ["in", sorted(manageable)]',
        ):
            self.assertIn(token, source)

    def test_native_form_uses_scoped_link_queries(self):
        source = (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_user_branch_access"
            / "eduedge_user_branch_access.js"
        ).read_text(encoding="utf-8")
        for token in (
            "eduedge.api.user_branch_access.get_user_branch_access_authoring_context",
            'frm.set_df_property("access_scope", "options", levels.join("\\n"))',
            "eduedge.api.user_branch_access.user_branch_access_user_query",
            "eduedge.api.user_branch_access.user_branch_access_company_query",
            "eduedge.api.user_branch_access.user_branch_access_institution_query",
            "eduedge.api.education.school_branch_query",
        ):
            self.assertIn(token, source)

    def test_branch_governance_separates_coverage_from_identifiable_rows(self):
        source = (APP / "services" / "branch_governance.py").read_text(encoding="utf-8")
        for token in (
            "coverage_assignments = _get_access_rows(",
            "permission_aware=False",
            "permission_aware=True",
            "getter = frappe.get_list if permission_aware else frappe.get_all",
            '"assignments": assignments if include_assignment_details else []',
        ):
            self.assertIn(token, source)


    def test_internal_context_invalidation_does_not_use_self_service_cross_user_apis(self):
        source = (APP / "services" / "branch_context.py").read_text(encoding="utf-8")
        block = source.split("def invalidate_user_branch_context", 1)[1].split(
            "def _normalise_active_scope", 1
        )[0]
        self.assertIn("_get_active_access_rows(user)", block)
        self.assertIn('"EduEdge School Branch"', block)
        self.assertNotIn("get_allowed_school_branches(user=user)", block)
        self.assertNotIn("get_branch_access_profile(user=user)", block)
        self.assertIn("internal server routine", block)



if __name__ == "__main__":
    unittest.main()
