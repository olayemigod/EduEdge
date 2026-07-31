from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestEdgeSuiteKeyboardCommandsContract(unittest.TestCase):
	def test_keyboard_asset_registers_search_and_safe_save_commands(self):
		asset = (APP / "public/js/eduedge_keyboard_shortcuts.js").read_text()
		for expected in (
			"EdgeSuiteCommands",
			"registerSaveHandler",
			"activateSaveHandler",
			"saveCurrentContext",
			"openCommandPalette",
			'key === "s"',
			'key === "k"',
			"edgesuite:save-request",
			"edgesuite:command-palette-request",
			"form.save()",
			"form.doc.docstatus",
			"form.is_dirty()",
			"event.preventDefault()",
		):
			self.assertIn(expected, asset)

	def test_keyboard_asset_does_not_bypass_document_safety(self):
		asset = (APP / "public/js/eduedge_keyboard_shortcuts.js").read_text()
		for forbidden in (
			"ignore_permissions",
			"frappe.db.set_value",
			"frappe.client.save",
			"docstatus = 0",
			"form.doc.docstatus = 0",
		):
			self.assertNotIn(forbidden, asset)
		self.assertIn("Submitted documents cannot be changed", asset)
		self.assertIn("textarea, [contenteditable='true']", asset)

	def test_hooks_load_keyboard_asset_before_product_navigation(self):
		hooks = (APP / "hooks.py").read_text()
		keyboard = hooks.index('"/assets/eduedge/js/eduedge_keyboard_shortcuts.js"')
		menu = hooks.index('"eduedge_product_menu.bundle.js"')
		self.assertLess(keyboard, menu)


if __name__ == "__main__":
	unittest.main()
