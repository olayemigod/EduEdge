from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
API = APP / "api" / "branch_governance.py"
SERVICE = APP / "services" / "branch_governance.py"


class TestBranchGovernanceViewScopeHardeningContract(unittest.TestCase):
    def test_management_permissions_never_expand_governance_read_scope(self):
        source = API.read_text(encoding="utf-8")

        for token in (
            "Read scope always comes from the Branch Context service.",
            "permissions enable actions inside that scope; they must never widen it.",
            "include_all_branches=False",
            "can_manage_instructor_eligibility",
            "can_manage_accounting",
            "can_manage_enforcement",
        ):
            self.assertIn(token, source)

        context = source.split("context = _get_branch_governance_context(", 1)[1].split(
            'context["permissions"]', 1
        )[0]
        self.assertNotIn("can_manage_access\n", context.split("include_all_branches=", 1)[-1])
        self.assertNotIn("or can_manage_instructor_eligibility", context)
        self.assertNotIn("or can_manage_accounting", context)
        self.assertNotIn("or can_manage_enforcement", context)

    def test_service_normal_context_starts_from_authorized_branch_service(self):
        source = SERVICE.read_text(encoding="utf-8")

        for token in (
            "include_all_branches: bool = False",
            'allowed_branch_names = {row["name"] for row in get_allowed_school_branches()}',
            "_get_branch_rows(company=company, allowed_branch_names=allowed_branch_names)",
        ):
            self.assertIn(token, source)

    def test_enforcement_preflight_keeps_separate_all_branch_path(self):
        source = SERVICE.read_text(encoding="utf-8")

        self.assertIn("def set_branch_enforcement", source)
        self.assertIn("settings.has_permission(\"write\")", source)
        self.assertIn("get_branch_governance_context(include_all_branches=True)", source)


if __name__ == "__main__":
    unittest.main()
