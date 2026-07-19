from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSetupCenterActionContract(unittest.TestCase):
	def test_new_records_prefer_quick_editors_with_safe_fallbacks(self):
		service = (APP / "services/setup_readiness.py").read_text(encoding="utf-8")
		page = (
			APP / "public/js/eduedge_setup_center/EduEdgeSetupCenter.vue"
		).read_text(encoding="utf-8")

		self.assertIn('action_type="new_doc"', service)
		self.assertIn('doctype="EduEdge School Branch"', service)
		self.assertIn('doctype="EduEdge Program Offering"', service)
		self.assertNotIn('/app/eduedge-school-branch/new', service)
		self.assertNotIn('/app/eduedge-program-offering/new', service)
		self.assertIn('@click="runAction(action)"', page)
		self.assertIn("QUICK_RESOURCES", page)
		self.assertIn("openRecordModal", page)
		self.assertIn("<EdgeFormDialog", page)
		self.assertIn('frappe.new_doc(action.doctype)', page)
		self.assertIn(':key="action.key || action.route || action.label"', page)

	def test_recommended_actions_include_guidance_and_semantic_icons(self):
		service = (APP / "services/setup_readiness.py").read_text(encoding="utf-8")
		page = (
			APP / "public/js/eduedge_setup_center/EduEdgeSetupCenter.vue"
		).read_text(encoding="utf-8")

		for expected in (
			'"description": description',
			'"icon": icon',
			'"key": key',
			"eduedge-setup-action__copy",
			"eduedge-ready-message",
		):
			self.assertIn(expected, service + page)


if __name__ == "__main__":
	unittest.main()
