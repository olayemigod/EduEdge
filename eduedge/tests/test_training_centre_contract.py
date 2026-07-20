import json
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent
TRAINING_ROOT = REPO_ROOT / "docs" / "training" / "eduedge"


def read(relative: str) -> str:
	return (APP_ROOT / relative).read_text(encoding="utf-8")


def test_training_manifest_covers_every_approved_audience_with_guided_steps():
	manifest = json.loads((TRAINING_ROOT / "training_modules.json").read_text(encoding="utf-8"))
	audiences = {row["audience"] for row in manifest}
	assert audiences == {
		"shared",
		"student",
		"teacher",
		"school_admin",
		"school_owner",
		"processedge_staff",
	}
	module_ids = {row["module_id"] for row in manifest}
	assert len(module_ids) == len(manifest)
	for module in manifest:
		assert module["status"] == "Published"
		assert module["steps"]
		assert module["estimated_minutes"] > 0
		assert module["content_version"] >= 1
		path = REPO_ROOT / module["markdown_path"]
		assert path.exists(), path
		assert path.resolve().is_relative_to(TRAINING_ROOT.resolve())
		for prerequisite in module.get("prerequisites", []):
			assert prerequisite in module_ids


def test_training_access_and_content_are_server_enforced():
	catalog = read("training/catalog.py")
	api = read("api/training_centre.py")
	for contract in (
		"allowed_audience_keys",
		"EduEdge Super Administrator",
		"System Manager",
		"School Administrator",
		"Teacher",
		"Student",
		"can_view_module",
		"resolve_markdown_path",
		"is_relative_to(TRAINING_ROOT.resolve())",
		"youtube-nocookie.com",
	):
		assert contract in catalog
	for contract in (
		"get_training_overview",
		"get_training_module_content",
		"save_training_progress",
		"_assert_prerequisites",
		'doc.check_permission("write")',
		"frappe.has_permission",
	):
		assert contract in api
	assert "ignore_permissions" not in api


def test_training_progress_is_private_and_role_aware():
	hooks = read("hooks.py")
	permissions = read("training/permissions.py")
	doctype = json.loads(
		(APP_ROOT / "eduedge/doctype/eduedge_training_progress/eduedge_training_progress.json").read_text(
			encoding="utf-8"
		)
	)
	assert '"EduEdge Training Progress": "eduedge.training.permissions.training_progress_query"' in hooks
	assert '"EduEdge Training Progress": "eduedge.training.permissions.has_training_progress_permission"' in hooks
	assert "doc.get(\"user\") == user" in permissions
	assert any(field["fieldname"] == "training_key" and field.get("unique") == 1 for field in doctype["fields"])
	assert {permission["role"] for permission in doctype["permissions"]} >= {
		"EduEdge Super Administrator",
		"System Manager",
		"School Administrator",
		"Teacher",
		"Student",
	}


def test_training_page_uses_edgesuite_shell_and_safe_product_bundle_loader():
	page = read("eduedge/page/eduedge_training_centre/eduedge_training_centre.js")
	bundle = read("public/js/eduedge_training_centre.bundle.js")
	component = read("public/js/eduedge_training_centre/EduEdgeTrainingCentre.vue")
	markdown = read("public/js/eduedge_training_centre/markdown.js")
	for contract in (
		'frappe.require("edgeui.bundle.js"',
		'frappe.require("eduedge_training_centre.bundle.js"',
		"createEduEdgeTrainingCentreApp",
	):
		assert contract in page
	assert "createEduEdgeApp" in bundle
	for contract in (
		"<EdgeAppShell",
		"<EdgePageLayout>",
		"<EdgePageHeader",
		"Step Checklist",
		"Watch Video",
		"Practice Exercise",
		"video_embed_url",
		"renderTrainingFlowcharts",
	):
		assert contract in component
	assert "escapeHtml" in markdown
	assert "safeHref" in markdown
	assert "language-mermaid" in markdown
	assert "javascript:" not in markdown


def test_training_centre_is_discoverable_from_navigation_and_product_menu():
	navigation = read("public/js/eduedge_ui/navigation.js")
	product_menu = read("public/js/eduedge_product_menu.bundle.js")
	home = read("public/js/eduedge_home/EduEdgeHome.vue")
	for content in (navigation, product_menu, home):
		assert "/app/eduedge-training-centre" in content
	assert "Help & Training" in navigation
	assert "EduEdge Training Centre" in product_menu
	assert "Train every EduEdge role" in home
