from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestEdgeSuiteKeyboardCommandsContract(unittest.TestCase):
	def test_keyboard_bundle_registers_search_and_safe_save_commands(self):
		bundle = (APP / "public/js/eduedge_keyboard_shortcuts.bundle.js").read_text()
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
			self.assertIn(expected, bundle)

	def test_keyboard_bundle_does_not_bypass_document_safety(self):
		bundle = (APP / "public/js/eduedge_keyboard_shortcuts.bundle.js").read_text()
		for forbidden in (
			"ignore_permissions",
			"frappe.db.set_value",
			"frappe.client.save",
			"docstatus = 0",
			"form.doc.docstatus = 0",
		):
			self.assertNotIn(forbidden, bundle)
		self.assertIn("Submitted documents cannot be changed", bundle)
		self.assertIn("textarea, [contenteditable='true']", bundle)

	def test_hooks_load_keyboard_bundle_before_product_navigation(self):
		hooks = (APP / "hooks.py").read_text()
		keyboard = hooks.index('"eduedge_keyboard_shortcuts.bundle.js"')
		menu = hooks.index('"eduedge_product_menu.bundle.js"')
		self.assertLess(keyboard, menu)


if __name__ == "__main__":
	unittest.main()
