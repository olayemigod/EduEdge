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

	def test_searchable_links_use_shared_width_bound_flyout(self):
		form = (
			APP
			/ "public"
			/ "js"
			/ "eduedge_ui"
			/ "components"
			/ "EdgeFormDialogFallback.vue"
		).read_text(encoding="utf-8")

		for expected in (
			"<EdgeLinkField",
			':options="normalizedOptions(field.options)"',
			'@query-change="requestOptions(field, $event)"',
			'@update:model-value="setValue(field, $event)"',
			"eduedge-quick-link-control",
			"eduedge-quick-link-field { min-width: 0; width: 100%; }",
		):
			self.assertIn(expected, form)

		self.assertNotIn("<datalist", form)
		self.assertNotIn(":list=", form)

	def test_searchable_flyout_has_capture_phase_outside_click_dismissal(self):
		form = (
			APP
			/ "public"
			/ "js"
			/ "eduedge_ui"
			/ "components"
			/ "EdgeFormDialogFallback.vue"
		).read_text(encoding="utf-8")

		for expected in (
			'ref="formRoot"',
			'document.addEventListener("pointerdown", this.dismissOpenLinkOnOutsidePointer, true)',
			'document.removeEventListener("pointerdown", this.dismissOpenLinkOnOutsidePointer, true)',
			'active?.classList?.contains("edge-link-field__input")',
			'this.$refs.formRoot?.contains(active)',
			'active.closest?.(".edge-link-field")',
			"active.blur()",
		):
			self.assertIn(expected, form)


if __name__ == "__main__":
	unittest.main()
