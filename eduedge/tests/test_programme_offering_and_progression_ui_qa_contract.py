from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_class_intake_page_uses_single_edgesuite_workflow_surface():
	page = (ROOT / "eduedge/eduedge/page/eduedge_program_offerings/eduedge_program_offerings.js").read_text()
	assert "add_visible_curriculum_bridge" not in page
	assert "add_offering_operation_buttons" not in page
	assert '__("Class Operations")' not in page
	assert "programme_offering_session_options.get_programme_offering_session_options" in page
	assert "clear_inner_toolbar" in page


def test_class_intake_session_options_expose_calendar_readiness_separately():
	api = (ROOT / "eduedge/api/programme_offering_session_options.py").read_text()
	assert 'frappe.get_list(\n\t\t"Academic Year"' in api
	assert '"calendar_ready": bool(calendar.get("name"))' in api
	assert "selected_session_calendar_ready" in api
	assert "Programme Offering is sessional" in api


def test_student_progression_rows_cannot_overflow_their_panel():
	css = (ROOT / "eduedge/public/css/eduedge_student_progression_runtime_fix.css").read_text()
	assert ".progression-row > *" in css
	assert "min-width: 0" in css
	assert "overflow-wrap: anywhere" in css
	assert "grid-column: 2 / -1" in css
	assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in css
