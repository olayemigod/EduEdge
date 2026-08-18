from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
	return (ROOT / relative).read_text(encoding="utf-8")


def test_multi_link_field_composes_existing_edgesuite_link_field():
	source = _read("public/js/eduedge_ui/components/EduEdgeMultiLinkField.vue")
	assert "<EdgeLinkField" in source
	assert 'emits: ["update:modelValue", "change"]' in source
	assert "selectedOptions" in source
	assert "searchAvailable" in source
	assert "!selected.has(row.value)" in source


def test_multi_link_field_preserves_multi_value_semantics():
	source = _read("public/js/eduedge_ui/components/EduEdgeMultiLinkField.vue")
	assert "const next = [...(this.modelValue || []), value]" in source
	assert "filter((item) => item !== value)" in source
	assert 'this.$emit("update:modelValue", next)' in source
