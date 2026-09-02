from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
	return (ROOT / relative).read_text(encoding="utf-8")


def test_shared_fuzzy_bridge_is_bounded_and_optional():
	source = _read("api/fuzzy_search.py")
	assert "CANDIDATE_LIMIT = 100" in source
	assert "MAX_ANCHORS = 4" in source
	assert "query_anchors" in source
	assert "get_bounded_candidates" in source
	assert "from edgesuite_ui.search_ranking import rank_search_records" in source
	assert "except (ImportError, ModuleNotFoundError)" in source
	assert "rows[start : start + page_length]" in source


def test_programme_and_institution_queries_preserve_scope_before_ranking():
	source = _read("api/academic_context.py")
	assert "assert_branch_access(branch)" in source
	assert "offering.school_branch = %(branch)s" in source
	assert "offering.is_active = 1" in source
	assert "_program_offering_rows" in source
	assert "query_anchors(search_text)" in source
	assert "remaining = CANDIDATE_LIMIT - len(rows)" in source
	assert "rank_link_rows(" in source
	assert "frappe.has_permission(doctype, \"read\")" in source
	assert "query_filters[institution_fieldname] = institution" in source
	assert "get_bounded_candidates(" in source


def test_teaching_instructor_query_keeps_assignment_governance():
	source = _read("api/teaching_assignment_options.py")
	assert "assert_branch_access(branch)" in source
	assert "assignment.program_offering = %(program_offering)s" in source
	assert "assignment.course = %(course)s" in source
	assert "assignment.enabled = 1" in source
	assert "instructor.status = 'Active'" in source
	assert "_eligible_instructor_rows" in source
	assert "query_anchors(search_text)" in source
	assert "remaining = CANDIDATE_LIMIT - len(rows)" in source
	assert "rank_link_rows(" in source
	assert "candidate_limit" in source


def test_class_arm_fuzzy_provider_preserves_branch_scope_and_ranked_paging():
	source = _read("api/class_arm_fuzzy.py")
	assert "core._require_read()" in source
	assert "core._resolve_branch(branch)" in source
	assert "filters = {BRANCH_FIELD: branch}" in source
	assert "get_bounded_candidates(" in source
	assert "search_fields=search_fields" in source
	assert "rank_link_candidates(" in source
	assert "ranked[start : start + page_length]" in source
	assert "core._attach_group_summary(result_rows)" in source


def test_class_arm_page_uses_fuzzy_provider_for_search_and_browsing():
	source = _read("eduedge/page/eduedge_class_arms/eduedge_class_arms.js")
	assert "configure_class_arm_fuzzy_search" in source
	assert "eduedge.api.class_arm_fuzzy.get_class_arms_page" in source
	assert "configure_class_arm_fuzzy_search();" in source
