from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
REPORT_CARDS = APP / "public" / "js" / "eduedge_report_cards" / "EduEdgeReportCards.vue"


class TestReportCardUiHardeningContract(unittest.TestCase):
	def test_report_card_page_uses_edgesuite_shell_and_semantic_theme_tokens(self):
		text = REPORT_CARDS.read_text()
		for component in (
			"EdgeAppShell",
			"EdgePageLayout",
			"EdgePageHeader",
			"EdgeFilterBar",
			"EdgeDashboardLayout",
			"EdgeStatCard",
			"EdgeStatusBadge",
		):
			self.assertIn(component, text)
		style = text.split("<style scoped>", 1)[1].split("</style>", 1)[0]
		self.assertIn("var(--control-bg)", style)
		self.assertIn("var(--border-color)", style)
		self.assertIn("var(--text-muted)", style)
		self.assertIn("var(--primary)", style)
		self.assertNotRegex(style, re.compile(r"#[0-9a-fA-F]{3,8}\b"))
		self.assertNotIn("!important", style)

	def test_native_form_controls_are_theme_safe_and_keyboard_visible(self):
		text = REPORT_CARDS.read_text()
		style = text.split("<style scoped>", 1)[1].split("</style>", 1)[0]
		self.assertIn(".eduedge-report-filters .form-control", style)
		self.assertIn(".eduedge-field .form-control", style)
		self.assertIn("background: var(--control-bg)", style)
		self.assertIn("color: var(--text-color, inherit)", style)
		self.assertIn("border-color: var(--border-color)", style)
		self.assertIn(":focus-visible", style)
		self.assertIn("outline: 2px solid var(--primary)", style)
		self.assertIn(".eduedge-student-row:focus-visible", style)

	def test_result_table_remains_horizontally_scrollable_on_narrow_screens(self):
		text = REPORT_CARDS.read_text()
		style = text.split("<style scoped>", 1)[1].split("</style>", 1)[0]
		self.assertIn(".eduedge-result-table-wrap { overflow-x: auto;", style)
		self.assertIn("@media (max-width: 900px)", style)
		self.assertIn("@media (max-width: 640px)", style)


if __name__ == "__main__":
	unittest.main()
