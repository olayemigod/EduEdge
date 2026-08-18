from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
	return (ROOT / relative).read_text(encoding="utf-8")


def test_instructor_search_preserves_visibility_and_bounds():
	source = _read("api/instructor_assignment_link_search.py")
	assert "CANDIDATE_LIMIT" in source
	assert "MAX_RESULTS = 50" in source
	assert "_can_manage_assignments" in source
	assert "current_user_instructors" in source
	assert '"status": "Active"' in source
	assert 'exact_fields=("value", "eduedge_mobile", "eduedge_email")' in source
	assert "rank_link_rows(" in source


def test_assignment_offering_search_is_branch_scoped():
	source = _read("api/instructor_assignment_link_search.py")
	assert "core.assert_branch_access(branch)" in source
	assert 'filters={"school_branch": branch, "is_active": 1}' in source
	assert 'exact_fields=("value", "offering_code")' in source


def test_assignment_class_arm_search_preserves_offering_context():
	source = _read("api/instructor_assignment_link_search.py")
	for token in (
		'filters: dict = {BRANCH_FIELD: branch, "disabled": 0}',
		"filters[OFFERING_FIELD] = program_offering",
		"row.get(\"program\") != offering.program",
		"row.get(\"academic_year\") != offering.academic_year",
		"row.get(\"academic_term\") != offering.academic_term",
	):
		assert token in source
