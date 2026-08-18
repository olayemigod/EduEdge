from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
	return (ROOT / relative).read_text(encoding="utf-8")


def test_enrollment_student_search_is_bounded_and_institution_scoped():
	source = _read("api/enrollment_link_search.py")
	assert "page_length=CANDIDATE_LIMIT" in source
	assert "_same_institution_allowed_branches" in source
	assert '"enabled": 1' in source
	assert 'exact_fields=("value", "student_mobile_number", "student_email_id")' in source
	assert "rank_link_rows(" in source


def test_enrollment_offering_search_preserves_branch_and_enrollment_rules():
	source = _read("api/enrollment_link_search.py")
	for token in (
		'"school_branch": resolved',
		'"institution": institution',
		'"is_active": 1',
		'"enrollment_enabled": 1',
		"_student_institution(student_row) != institution",
		"You do not have access to the Student's home Branch.",
		'exact_fields=("value", "offering_code")',
	):
		assert token in source


def test_enrollment_search_result_limit_is_hard_bounded():
	source = _read("api/enrollment_link_search.py")
	assert "MAX_RESULTS = 50" in source
	assert "min(max(cint(value) or 20, 1), MAX_RESULTS)" in source
