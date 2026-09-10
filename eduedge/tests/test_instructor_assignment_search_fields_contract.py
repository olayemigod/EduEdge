from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
	return (ROOT / relative).read_text(encoding="utf-8")


def test_assignment_search_fields_reuse_edgesuite_primitives():
	source = _read(
		"public/js/eduedge_instructor_assignments/InstructorAssignmentSearchFields.vue"
	)
	assert "<EdgeLinkField" in source
	assert "<EduEdgeMultiLinkField" in source
	assert "search_instructors" in source
	assert "search_assignment_offerings" in source
	assert "search_assignment_class_arms" in source
	assert "search_assignment_courses" in source


def test_assignment_instructor_search_loads_bounded_choices_on_focus():
	source = _read(
		"public/js/eduedge_instructor_assignments/InstructorAssignmentSearchFields.vue"
	)
	assert ':open-on-focus="true"' in source
	assert 'page_length: 20' in source
	assert 'placeholder="Search Instructor"' in source


def test_assignment_search_fields_preserve_contextual_scoping():
	source = _read(
		"public/js/eduedge_instructor_assignments/InstructorAssignmentSearchFields.vue"
	)
	assert ":disabled=\"!row.branch\"" in source
	assert ":disabled=\"!row.program_offering\"" in source
	assert "branch: row.branch" in source
	assert "program_offering: row.program_offering" in source
	assert 'page_length: 20' in source


def test_assignment_search_fields_keep_multi_value_semantics():
	source = _read(
		"public/js/eduedge_instructor_assignments/InstructorAssignmentSearchFields.vue"
	)
	for token in (
		'"update:class-arms"',
		'"class-arms-change"',
		'"update:courses"',
		'"courses-change"',
	):
		assert token in source
