from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestTopbarContextSwitcherContract(unittest.TestCase):
	def setUp(self):
		self.source = (APP / "public" / "js" / "eduedge_shell_identity.bundle.js").read_text(encoding="utf-8")

	def test_native_branch_chip_becomes_keyboard_accessible_switcher(self):
		for token in (
			"findNativeBranchControl",
			"bindBranchSwitcher",
			'eduedge-context-switcher',
			'control.setAttribute("role", "button")',
			'control.setAttribute("tabindex", "0")',
			'control.addEventListener("click"',
			'control.addEventListener("keydown"',
			'["Enter", " "]',
		):
			self.assertIn(token, self.source)

	def test_dialog_cascades_institution_to_permission_scoped_branches(self):
		for token in (
			'"eduedge.api.branch_context.get_active_branch_context"',
			'"eduedge.api.branch_context.switch_school_branch"',
			"Switch Institution and Branch",
			"institutionOptions(payload)",
			"branchOptions(payload, institution)",
			"Only Branches permitted for your user are shown.",
			"payload.allowed_branches",
			"payload.allowed_institutions",
		):
			self.assertIn(token, self.source)

	def test_switch_is_post_only_and_reloads_current_page_to_clear_stale_context(self):
		for token in (
			'type: "POST"',
			"company: branchRow.company || institutionRow.company || undefined",
			"institution,",
			"window.location.reload()",
			"applyInstitutionContext(switched.institution_context)",
		):
			self.assertIn(token, self.source)

	def test_duplicate_branch_context_is_removed_from_injected_strip(self):
		self.assertIn("contextMarkup({ includeBranch: false })", self.source)
		self.assertIn("contextMarkup({ includeBranch: true })", self.source)
		self.assertIn("strip.querySelector('[data-eduedge-context=\"branch\"]')", self.source)
		self.assertIn("bindBranchSwitcher(topbar, identity)", self.source)

	def test_authorised_all_branch_scope_is_preserved(self):
		for token in (
			"payload.can_view_all_branches",
			"payload.all_branch_institutions",
			"payload.all_branches_key",
			"All Branches —",
		):
			self.assertIn(token, self.source)


if __name__ == "__main__":
	unittest.main()
