from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
COMMAND_PALETTE_CSS = APP / "public/css/eduedge_compact_navigation.css"


class TestEdgeSuiteKeyboardCommandsContract(unittest.TestCase):
	def test_keyboard_asset_registers_search_and_safe_save_commands(self):
		asset = (APP / "public/js/eduedge_keyboard_shortcuts.js").read_text()
		for expected in (
			'COMMAND_VERSION = "1.0.0"',
			"EdgeSuiteCommands?.version",
			"registry.version = COMMAND_VERSION",
			"registerSaveHandler",
			"activateSaveHandler",
			"saveCurrentContext",
			"openCommandPalette",
			"findVisibleSaveControl",
			"invokeVisibleSaveControl",
			"data-edgesuite-save",
			"control.click()",
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
		self.assertIn(".modal.show", asset)
		self.assertIn('new Set(["save", "save changes", "update", "apply changes"])', asset)

	def test_hooks_load_keyboard_asset_before_product_navigation(self):
		hooks = (APP / "hooks.py").read_text()
		keyboard = hooks.index('"/assets/eduedge/js/eduedge_keyboard_shortcuts.js"')
		menu = hooks.index('"eduedge_product_menu.bundle.js"')
		self.assertLess(keyboard, menu)

	def test_command_palette_uses_edgesuite_theme_tokens(self):
		css = COMMAND_PALETTE_CSS.read_text()
		for expected in (
			"--edge-text-muted",
			"--edge-bg",
			"--edge-border",
			"--edge-text",
			"--edge-primary",
			"--edge-surface",
		):
			self.assertIn(expected, css)

		palette_css = css[css.index(".eduedge-command-palette") :]
		for forbidden in (
			"var(--text-muted)",
			"var(--control-bg)",
			"var(--border-color)",
			"var(--text-color)",
			"rgba(0, 0, 0, .04)",
		):
			self.assertNotIn(forbidden, palette_css)


if __name__ == "__main__":
	unittest.main()