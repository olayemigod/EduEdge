from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
	return (ROOT / relative).read_text(encoding="utf-8")


def test_assignment_course_search_is_branch_and_offering_scoped():
	source = _read("api/instructor_assignment_course_search.py")
	for token in (
		"core.assert_branch_access(branch)",
		"offering.school_branch != branch",
		"branch_row.get(\"institution\") != offering.institution",
		'filters={"parent": offering.program, "parenttype": "Program"}',
		"page_length=CANDIDATE_LIMIT",
		"rank_link_rows(",
	):
		assert token in source


def test_assignment_course_search_marks_curriculum_membership_and_is_bounded():
	source = _read("api/instructor_assignment_course_search.py")
	assert '"In curriculum" if row.get("name") in configured else "Institution course"' in source
	assert 'row["configured"] = row.get("name") in configured' in source
	assert "MAX_RESULTS = 50" in source
	assert "min(max(cint(value) or 20, 1), MAX_RESULTS)" in source
