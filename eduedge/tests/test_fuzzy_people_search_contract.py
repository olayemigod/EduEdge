from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PEOPLE = ROOT / "api" / "people_operations.py"
FUZZY = ROOT / "api" / "fuzzy_search.py"


def test_student_workspace_search_uses_shared_fuzzy_ranker():
	text = PEOPLE.read_text()
	assert "from eduedge.api.fuzzy_search import CANDIDATE_LIMIT, rank_link_rows" in text
	assert "def _rank_student_rows" in text
	assert 'exact_fields=("value", "student_mobile_number", "student_email_id")' in text
	assert 'search_fields=("label", "description")' in text


def test_student_search_keeps_branch_scope_and_candidate_bound():
	text = PEOPLE.read_text()
	assert 'filters: dict[str, Any] = {BRANCH_FIELD: resolved}' in text
	assert "page_length=CANDIDATE_LIMIT" in text
	assert "MAX_PAGE_LENGTH = 50" in text


def test_shared_fuzzy_bridge_is_bounded_and_backward_compatible():
	text = FUZZY.read_text()
	assert "CANDIDATE_LIMIT = 100" in text
	assert "from edgesuite_ui.search_ranking import rank_search_records" in text
	assert "except (ImportError, ModuleNotFoundError):" in text
