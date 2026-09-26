from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestReportCardScoreStateContract(unittest.TestCase):
	def test_profiled_report_cards_preserve_score_state_display_codes(self):
		service = (APP / "education" / "profiled_report_cards.py").read_text()
		self.assertIn("def _component_display_value", service)
		self.assertIn('status_code = (component.get("status_code") or "").strip()', service)
		self.assertIn('row["display_value"] = _component_display_value(row)', service)

	def test_genuine_zero_is_rendered_as_zero_not_missing(self):
		service = (APP / "education" / "profiled_report_cards.py").read_text()
		self.assertIn('if flt(component.get("maximum_score")) <= 0:', service)
		self.assertIn('return str(int(value))', service)
		template = (APP / "templates" / "report_card.html").read_text()
		self.assertIn('component.display_value or "-"', template)

	def test_browser_preview_uses_snapshot_component_display_value(self):
		vue = (APP / "public" / "js" / "eduedge_report_cards" / "EduEdgeReportCards.vue").read_text()
		self.assertIn("component.display_value !== undefined", vue)
		self.assertIn("return component.display_value", vue)


if __name__ == "__main__":
	unittest.main()
