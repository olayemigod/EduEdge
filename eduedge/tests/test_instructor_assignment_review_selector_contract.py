from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
	return (ROOT / relative).read_text(encoding="utf-8")


def test_review_selector_uses_bounded_async_instructor_search():
	selector = _read(
		"public/js/eduedge_instructor_assignments/InstructorRecordSelector.vue"
	)
	for token in (
		"<EdgeLinkField",
		'placeholder="Search Instructor"',
		':open-on-focus="true"',
		"eduedge.api.instructor_assignment_link_search.search_instructors",
		"page_length: 20",
	):
		assert token in selector
	assert "get_all" not in selector


def test_review_toolbar_upgrades_legacy_select_without_reintroducing_initial_preload():
	bridge = _read("public/js/eduedge_instructor_assignment_capabilities.bundle.js")
	for token in (
		"InstructorRecordSelector",
		'select[data-eduedge-view-instructor]',
		"select.replaceWith(host)",
		"createEduEdgeInstructorRecordSelectorApp",
		"upgradeInstructorRecordToolbar(this)",
	):
		assert token in bridge
	assert "proxy.data?.instructors" not in bridge


def test_register_wrapper_redirects_current_lightweight_runtime_only_after_instructor_selection():
	bridge = _read("public/js/eduedge_instructor_assignment_capabilities.bundle.js")
	for token in (
		'eduedge.api.instructor_assignment_runtime.get_instructor_assignments_page',
		'eduedge.api.instructor_assignment_register.get_instructor_assignment_register_page',
		"shouldLoadFilteredRegister(this)",
		"register_filters: JSON.stringify(proxy?.registerFilters || {})",
		"register_page: proxy?.registerPage || 1",
	):
		assert token in bridge


