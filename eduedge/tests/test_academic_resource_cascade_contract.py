from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


def test_program_editor_uses_native_institution_department_cascade():
	contract = (APP / "api" / "academic_resource_contract.py").read_text()
	for expected in (
		'INSTITUTION_FIELD = "eduedge_institution"',
		'"clear_fields": ["department"]',
		'"refresh_fields": ["department"]',
		'"fieldname": "department"',
		'filters={INSTITUTION_FIELD: institution}',
		'if not institution:\n\t\t\t\treturn []',
	):
		assert expected in contract
	program_editor = contract.split('config["editor_fields"] = [', 1)[1].split(
		'config["advanced_note"]', 1
	)[0]
	assert LEGACY_EDITOR_FIELD not in program_editor


def test_programme_offering_cascade_clears_all_invalid_context():
	contract = (APP / "api" / "academic_resource_contract.py").read_text()
	for expected in (
		'"academic_year",\n\t\t\t\t"academic_term",',
		'"clear_fields": ["academic_level"]',
		'"refresh_fields": ["academic_level"]',
		'"clear_fields": ["academic_term"]',
		'"refresh_fields": ["academic_term"]',
		"def _calendar_year_options",
		"def _calendar_term_options",
		'"EduEdge Institution Academic Calendar"',
		'"EduEdge Academic Calendar Period"',
	):
		assert expected in contract


def test_parentless_academic_option_queries_fail_closed_and_are_bounded():
	contract = (APP / "api" / "academic_resource_contract.py").read_text()
	for expected in (
		'if not institution:\n\t\t\treturn []',
		'if not institution or not program:\n\t\t\treturn []',
		'if not institution or not academic_year:\n\t\treturn []',
		"limit_page_length=30",
		"frappe.has_permission(doctype, \"read\")",
		"frappe.get_list(",
	):
		assert expected in contract


LEGACY_EDITOR_FIELD = '"fieldname": "eduedge_academic_section"'
