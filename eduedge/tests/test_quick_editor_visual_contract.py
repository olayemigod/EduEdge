from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestQuickEditorVisualContract(unittest.TestCase):
	def test_compatible_modal_uses_the_shared_edgesuite_structure(self):
		modal = (
			APP
			/ "public"
			/ "js"
			/ "eduedge_ui"
			/ "components"
			/ "EdgeModalFallback.vue"
		).read_text(encoding="utf-8")

		for expected in (
			'class="edge-modal-backdrop eduedge-modal-backdrop"',
			'class="edge-modal eduedge-compatible-modal"',
			"edge-modal__header",
			"edge-modal__heading",
			"edge-modal__close",
			"edge-modal__body",
			"edge-modal__footer",
			"align-items: center",
			"justify-content: center",
			"position: fixed",
			"margin: auto",
		):
			self.assertIn(expected, modal)

		self.assertNotIn('class="edge-modal edge-modal-fallback"', modal)
		self.assertNotIn("edge-modal-fallback__body", modal)

	def test_compatible_form_uses_shared_edgesuite_form_controls(self):
		form = (
			APP
			/ "public"
			/ "js"
			/ "eduedge_ui"
			/ "components"
			/ "EdgeFormDialogFallback.vue"
		).read_text(encoding="utf-8")

		for expected in (
			'class="edge-form-dialog"',
			'class="edge-form-grid"',
			'class="edge-form-field"',
			"edge-form-field__label",
			"edge-form-control",
			"edge-form-global-error",
			"edge-form-error",
			"edge-checkbox",
			"edge-modal__footer-spacer",
			"edge-modal__full-form",
		):
			self.assertIn(expected, form)

		self.assertNotIn("edge-form-dialog-fallback__grid", form)
		self.assertNotIn('class="form-control"', form)


if __name__ == "__main__":
	unittest.main()
