from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
	return (ROOT / relative).read_text(encoding="utf-8")


def test_assignment_page_uses_lightweight_runtime_and_search_components():
	component = _read(
		"public/js/eduedge_instructor_assignments/EduEdgeInstructorAssignments.vue"
	)
	assert "InstructorAssignmentSearchFields" in component
	assert (
		"eduedge.api.instructor_assignment_runtime.get_instructor_assignments_page"
		in component
	)
	assert "eduedge.api.instructor_assignments.get_instructor_assignments_page" not in component
	for legacy_source in (
		"data.instructors",
		"data.offerings",
		"data.groups",
		"data.courses",
		"offeringsFor(row)",
		"groupsFor(row)",
		"coursesFor(row)",
	):
		assert legacy_source not in component


def test_assignment_search_component_uses_shared_single_and_multi_link_controls():
	component = _read(
		"public/js/eduedge_instructor_assignments/InstructorAssignmentSearchFields.vue"
	)
	assert component.count("<EdgeLinkField") >= 2
	assert component.count("<EduEdgeMultiLinkField") >= 2
	for endpoint in (
		"search_instructors",
		"search_assignment_offerings",
		"search_assignment_class_arms",
		"search_assignment_courses",
	):
		assert endpoint in component


def test_assignment_offering_search_preserves_period_date_autofill_metadata():
	source = _read("api/instructor_assignment_link_search.py")
	assert 'row["period_start_date"], row["period_end_date"]' in source
	assert "assignments._period_dates(" in source
	component = _read(
		"public/js/eduedge_instructor_assignments/EduEdgeInstructorAssignments.vue"
	)
	assert "option?.period_start_date" in component
	assert "option?.period_end_date" in component
