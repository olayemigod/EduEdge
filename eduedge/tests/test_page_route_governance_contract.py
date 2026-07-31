from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestPageRouteGovernanceContract(unittest.TestCase):
	def test_page_role_cleanup_and_audit_use_dynamic_discovery(self):
		baseline = (APP / "permissions_baseline.py").read_text()
		for expected in (
			"STANDARD_EDUEDGE_PAGES",
			"def get_eduedge_page_names()",
			'{"module": "EduEdge"}',
			'{"name": ["like", "eduedge-%"]}',
			"for page_name in get_eduedge_page_names()",
			"page_names = get_eduedge_page_names()",
			'"audited_pages": page_names',
		):
			self.assertIn(expected, baseline)
		for page in (
			"eduedge-my-profile",
			"eduedge-academic-foundation",
			"eduedge-institution-profile",
			"eduedge-institution-structure",
			"eduedge-institution-operations-settings",
			"eduedge-cbt-schedules",
			"eduedge-cbt-invigilation",
			"eduedge-cbt-marking",
			"eduedge-cbt-review-workbench",
			"eduedge-exam-templates",
			"eduedge-exam-template-builder",
			"eduedge-question-bank",
			"eduedge-question-responsibilities",
		):
			self.assertIn(f'"{page}"', baseline)

	def test_boot_and_desk_guard_fail_closed_only_for_installed_pages(self):
		boot = (APP / "boot.py").read_text()
		guard = (APP / "public/js/eduedge_keyboard_shortcuts.js").read_text()
		self.assertIn("def _get_eduedge_page_routes()", boot)
		self.assertIn('bootinfo["eduedge_page_routes"]', boot)
		for expected in (
			"installedEduEdgePageRoutes",
			"hasEduEdgePageRouteAccess",
			"enforceCurrentEduEdgePage",
			"Object.prototype.hasOwnProperty.call(routes, normalized)",
			"return false",
			"window.location.replace",
			"__eduedgePageRouteGuardBound",
		):
			self.assertIn(expected, guard)
		self.assertIn("if (!installedEduEdgePageRoutes().has(normalized)) return true", guard)


if __name__ == "__main__":
	unittest.main()
