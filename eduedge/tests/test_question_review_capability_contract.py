from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QUESTION = (
	ROOT
	/ "eduedge"
	/ "eduedge"
	/ "doctype"
	/ "eduedge_cbt_question"
	/ "eduedge_cbt_question.py"
)


def test_question_review_capability_is_not_delete_permission():
	content = QUESTION.read_text()
	function = content.split("def can_review_questions", 1)[1].split("def _require_question_author", 1)[0]
	assert '"write"' in function
	assert '"report"' in function
	assert '"delete"' not in function


def test_draft_delete_and_final_approval_remain_separate_controls():
	content = QUESTION.read_text()
	assert "def on_trash" in content
	assert "Approved or Retired CBT questions cannot be deleted" in content
	assert "def _assert_review_authority" in content
	assert "can_review_questions(frappe.session.user)" in content
