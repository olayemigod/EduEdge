import json
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent
TRAINING_ROOT = REPO_ROOT / "docs" / "training" / "eduedge"


def read(relative: str) -> str:
	return (APP_ROOT / relative).read_text(encoding="utf-8")


def load_manifests() -> list[dict]:
	rows = []
	for filename in ("training_modules.json", "training_modules_school_operations.json"):
		rows.extend(json.loads((TRAINING_ROOT / filename).read_text(encoding="utf-8")))
	return rows


def test_school_operations_manifest_covers_non_academic_role_families():
	extended = json.loads(
		(TRAINING_ROOT / "training_modules_school_operations.json").read_text(encoding="utf-8")
	)
	assert {row["audience"] for row in extended} == {
		"parent",
		"registrar",
		"finance",
		"people_ops",
		"procurement_assets",
		"school_operations",
		"cbt_ops",
		"student_safety",
	}
	assert len(extended) >= 14
	for module in extended:
		assert module["status"] == "Published"
		assert len(module["steps"]) >= 4
		assert module["estimated_minutes"] > 0
		path = REPO_ROOT / module["markdown_path"]
		assert path.exists(), path
		content = path.read_text(encoding="utf-8")
		assert "```mermaid" in content
		assert "## Practice Exercise" in content


def test_combined_training_manifests_have_unique_ids_and_valid_prerequisites():
	modules = load_manifests()
	module_ids = [row["module_id"] for row in modules]
	assert len(module_ids) == len(set(module_ids))
	known = set(module_ids)
	for module in modules:
		for prerequisite in module.get("prerequisites", []):
			assert prerequisite in known


def test_training_catalog_maps_school_roles_and_optional_apps_safely():
	catalog = read("training/catalog.py")
	for contract in (
		"TRAINING_MANIFESTS",
		"training_modules_school_operations.json",
		'"parent"',
		'"registrar"',
		'"finance"',
		'"people_ops"',
		'"procurement_assets"',
		'"school_operations"',
		'"cbt_ops"',
		'"student_safety"',
		'"EduEdge Parent"',
		'"Accounts User"',
		'"HR Manager"',
		'"Purchase User"',
		"module_availability",
		"frappe.get_installed_apps()",
		'frappe.db.exists("DocType", doctype)',
	):
		assert contract in catalog


def test_hrms_is_optional_and_unavailable_modules_are_blocked_server_side():
	hooks = read("hooks.py")
	catalog = read("training/catalog.py")
	api = read("api/training_centre.py")
	assert 'required_apps = ["erpnext", "education", "edgesuite_ui"]' in hooks
	assert '"required_apps"' in catalog
	assert '"required_doctypes"' in catalog
	assert "_assert_available" in api
	assert 'availability["availability_message"]' in api
	assert '_assert_available(module)' in api


def test_training_roles_and_progress_permissions_are_migration_safe():
	install = read("install.py")
	for role in (
		"EduEdge Parent",
		"Registrar",
		"Admission Officer",
		"School HR Officer",
		"Procurement Officer",
		"School Operations Manager",
		"Accounts User",
		"HR User",
		"Purchase User",
	):
		assert role in install
	assert '"EduEdge Parent": 0' in install
	assert "ensure_training_progress_permissions()" in install
	assert "ensure_training_page_roles()" in install
	assert 'role in {"EduEdge Parent", "Student"}' in install
	assert 'frappe.db.get_value("Role", role, "desk_access")' in install


def test_training_ui_explains_optional_module_requirements():
	component = read("public/js/eduedge_training_centre/EduEdgeTrainingCentre.vue")
	for contract in (
		"module.availability_message",
		"Requires setup",
		"Module not enabled on this site",
		"module.available",
		"is-unavailable",
		"Parents / Guardians",
		"registrars, finance, HR, operations",
	):
		assert contract in component
