from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
	return (ROOT / relative).read_text(encoding="utf-8")


def test_shared_fuzzy_bridge_is_bounded_and_optional():
	source = _read("api/fuzzy_search.py")
	assert "CANDIDATE_LIMIT = 100" in source
	assert "from edgesuite_ui.search_ranking import rank_search_records" in source
	assert "except (ImportError, ModuleNotFoundError)" in source
	assert "rows[start : start + page_length]" in source


def test_programme_and_institution_queries_preserve_scope_before_ranking():
	source = _read("api/academic_context.py")
	assert "assert_branch_access(branch)" in source
	assert "offering.school_branch = %(branch)s" in source
	assert "offering.is_active = 1" in source
	assert "rank_link_rows(" in source
	assert "frappe.has_permission(doctype, \"read\")" in source
	assert "query_filters[institution_fieldname] = institution" in source
	assert "page_length=CANDIDATE_LIMIT" in source


def test_teaching_instructor_query_keeps_assignment_governance():
	source = _read("api/teaching_assignment_options.py")
	assert "assert_branch_access(branch)" in source
	assert "assignment.program_offering = %(program_offering)s" in source
	assert "assignment.course = %(course)s" in source
	assert "assignment.enabled = 1" in source
	assert "instructor.status = 'Active'" in source
	assert "rank_link_rows(" in source
	assert "candidate_limit" in source
