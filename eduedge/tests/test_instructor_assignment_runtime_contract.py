from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
	return (ROOT / relative).read_text(encoding="utf-8")


def test_assignment_runtime_does_not_preload_large_link_datasets():
	source = _read("api/instructor_assignment_runtime.py")
	for forbidden in (
		'"instructors":',
		'"offerings":',
		'"groups":',
		'"courses":',
		"_all_options(",
		"_instructors(",
	):
		assert forbidden not in source
	for required in (
		'"allowed_branches": allowed',
		'"selected_instructor": selected_instructor',
		'"assignments": legacy._assignment_rows',
		'"branch_assignments":',
		'"assignment_types": list(core.ASSIGNMENT_TYPES)',
		'"assignment_scopes": list(core.BULK_SCOPES)',
	):
		assert required in source


def test_assignment_runtime_preserves_instructor_visibility_rules():
	source = _read("api/instructor_assignment_runtime.py")
	assert "current_user_instructors()" in source
	assert "core._can_manage_assignments()" in source
	assert '"status": "Active"' in source
	assert "The selected Instructor is not available to your user." in source
