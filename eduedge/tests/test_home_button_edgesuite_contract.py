from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
HOME = APP / "public" / "js" / "eduedge_home" / "EduEdgeHome.vue"


class TestHomeButtonEdgeSuiteContract(unittest.TestCase):
	def test_home_actions_use_edgesuite_primary_and_secondary_variants(self):
		text = HOME.read_text()
		self.assertIn('action-label="Open Academic Operations"', text)
		self.assertIn('class="edge-button edge-button--secondary eduedge-home-action"', text)
		self.assertIn('class="edge-button edge-button--primary eduedge-home-action"', text)

	def test_home_button_compatibility_style_is_theme_safe(self):
		text = HOME.read_text()
		style = text.split("<style scoped>", 1)[1].split("</style>", 1)[0]
		self.assertIn(":deep(.edge-button)", style)
		self.assertIn("box-shadow: none", style)
		self.assertIn(":focus-visible", style)
		self.assertIn("outline: 2px solid var(--primary)", style)
		self.assertNotRegex(style, re.compile(r"#[0-9a-fA-F]{3,8}\\b"))
		self.assertNotIn("!important", style)


if __name__ == "__main__":
	unittest.main()
