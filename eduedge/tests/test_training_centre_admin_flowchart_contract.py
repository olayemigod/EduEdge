from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
	return (APP_ROOT / relative).read_text(encoding="utf-8")


def test_mermaid_training_blocks_render_as_diagrams_during_markdown_conversion():
	markdown = read("public/js/eduedge_training_centre/markdown.js")
	for contract in (
		"function renderFlowchartMarkup(parsed)",
		"function renderCodeBlock(language, source)",
		"renderFlowchartMarkup(parseFlowchart(source))",
		'if (diagram) return diagram',
		'role="img" aria-label="Training workflow diagram"',
		"blocks.push(renderCodeBlock(codeLanguage, codeLines.join",
	):
		assert contract in markdown
	assert "renderTrainingFlowcharts(root)" in markdown


def test_administrator_can_view_every_path_and_bypass_site_and_prerequisite_gates():
	api = read("api/training_centre.py")
	for contract in (
		'def _is_administrator(user: str | None = None) -> bool:',
		'== "Administrator"',
		"allowed = list(AUDIENCES) if administrator_override",
		'"processedge_staff" if administrator_override',
		'if _is_administrator(user):\n\t\treturn',
		'if not _is_administrator(user) and not can_view_module',
		'"administrator_override": administrator_override',
		'available = site_availability["available"] or administrator_override',
		'locked = False if administrator_override',
	):
		assert contract in api
	assert "ignore_permissions" not in api


def test_administrator_override_does_not_fake_module_completion():
	api = read("api/training_centre.py")
	for contract in (
		'if len(completed) != len(valid_steps):',
		'Complete every guided step before marking this module complete.',
		'doc.completed_step_ids = json.dumps(completed)',
		'doc.completed_on = now if resolved_status == "Completed" else None',
	):
		assert contract in api
