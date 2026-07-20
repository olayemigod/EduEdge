from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
	return (APP_ROOT / relative).read_text(encoding="utf-8")


def test_admission_quick_editor_populates_upstream_program_rows():
	adapter = read("api/admission_resource.py")
	for contract in (
		'PROGRAMS_FIELD = "admission_programs"',
		'"type": "MultiSelect"',
		'doc.set("program_details", [])',
		'doc.append("program_details", {"program": program})',
		"validate_program_offering(",
		'"admission_enabled": 1',
		'"is_active": 1',
	):
		assert contract in adapter
	assert "ignore_permissions" not in adapter


def test_admission_editor_is_branch_safe_and_supports_repeated_campus_records():
	adapter = read("api/admission_resource.py")
	for contract in (
		"get_allowed_school_branches",
		"_assert_branch_access(branch)",
		"Each admission belongs to one branch/campus",
		"create separate admission records for each permitted campus",
		"Use a branch-specific title",
	):
		assert contract in adapter


def test_admission_program_options_require_doctype_permissions():
	adapter = read("api/admission_resource.py")
	for contract in (
		"_assert_program_option_permission()",
		'frappe.has_permission("Student Admission", permission_type)',
		'frappe.has_permission("EduEdge Program Offering", "read")',
		'frappe.get_list(',
		"You are not permitted to view admission programme options.",
	):
		assert contract in adapter
	assert 'frappe.get_all(\n\t\t"EduEdge Program Offering"' not in adapter


def test_admission_option_refresh_is_cascading_and_server_routed():
	safe = read("api/resource_center_safe.py")
	hooks = read("hooks.py")
	frontend = read("public/js/eduedge_ui/resource_modal.js")

	assert "admission_resource.enrich_editor" in safe
	assert "admission_resource.search_program_options" in safe
	assert "admission_resource.save_admission" in safe
	assert "search_resource_options" in hooks
	assert "field?.refresh_fields" in frontend
	assert "await searchResourceOptions" in frontend
	assert "Array.isArray(value)" in frontend


def test_school_administrators_receive_normal_frappe_admission_permissions():
	install = read("install.py")
	for role in (
		"EduEdge Administrator",
		"School Administrator",
		"Academic Administrator",
	):
		assert role in install
	for permission_type in (
		"read",
		"write",
		"create",
		"delete",
		"report",
	):
		assert f'"{permission_type}"' in install
	assert "ensure_admission_manager_permissions()" in install
	assert "update_permission_property(" in install
