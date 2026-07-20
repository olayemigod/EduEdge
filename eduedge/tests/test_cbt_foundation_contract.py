from __future__ import annotations

import json
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent
DOCTYPE_ROOT = APP_ROOT / "eduedge" / "doctype"


def read(relative: str) -> str:
	return (APP_ROOT / relative).read_text(encoding="utf-8")


def doctype_json(slug: str) -> dict:
	return json.loads((DOCTYPE_ROOT / slug / f"{slug}.json").read_text(encoding="utf-8"))


def test_cbt_foundation_defines_required_doctypes():
	expected = {
		"eduedge_cbt_question_option": "EduEdge CBT Question Option",
		"eduedge_cbt_question": "EduEdge CBT Question",
		"eduedge_cbt_exam_question": "EduEdge CBT Exam Question",
		"eduedge_cbt_exam": "EduEdge CBT Exam",
		"eduedge_cbt_attempt_question": "EduEdge CBT Attempt Question",
		"eduedge_cbt_attempt": "EduEdge CBT Attempt",
		"eduedge_cbt_attempt_answer": "EduEdge CBT Attempt Answer",
		"eduedge_cbt_sync_log": "EduEdge CBT Sync Log",
	}
	for slug, name in expected.items():
		payload = doctype_json(slug)
		assert payload["name"] == name
		assert payload["module"] == "EduEdge"


def test_attempt_snapshot_hides_answer_keys_from_students():
	snapshot = doctype_json("eduedge_cbt_attempt_question")
	fields = {row["fieldname"]: row for row in snapshot["fields"]}
	assert fields["answer_key_json"]["permlevel"] == 1
	assert fields["answer_key_json"]["hidden"] == 1
	assert fields["source_content_hash"]["permlevel"] == 1

	attempt = doctype_json("eduedge_cbt_attempt")
	student_permissions = [
		row for row in attempt["permissions"] if row["role"] == "Student"
	]
	assert student_permissions == [{"role": "Student", "read": 1, "write": 1, "create": 1}]
	assert not any(row.get("permlevel") == 1 and row["role"] == "Student" for row in attempt["permissions"])


def test_exam_and_attempt_lifecycle_are_server_owned():
	exam_controller = read("eduedge/doctype/eduedge_cbt_exam/eduedge_cbt_exam.py")
	attempt_controller = read("eduedge/doctype/eduedge_cbt_attempt/eduedge_cbt_attempt.py")
	answer_controller = read("eduedge/doctype/eduedge_cbt_attempt_answer/eduedge_cbt_attempt_answer.py")
	for contract in (
		"ALLOWED_STATUS_TRANSITIONS",
		"allow_cbt_transition",
		"cannot change after the CBT Exam is scheduled",
		"A CBT Exam with attempts cannot be deleted",
	):
		assert contract in exam_controller
	for contract in (
		"from_cbt_service",
		"Students can only access their own CBT Attempt",
		"active member of the selected class",
		"complete immutable question snapshot",
	):
		assert contract in attempt_controller
	assert "offline-resilient sync service" in answer_controller
	assert "answer history is immutable" in answer_controller


def test_cbt_service_enforces_timing_idempotency_and_pending_sync():
	service = read("cbt/service.py")
	for contract in (
		"for update",
		"compute_server_deadline",
		"classify_sync_update",
		"client_batch_id",
		"Pending Sync",
		"sync_grace_ends_on",
		"Students can only start their own CBT Attempt",
		"Maximum CBT attempts have been used",
		"Resolve all pending answer sync before result approval",
		"EduEdge CBT Sync Log",
		"submission_hash",
	):
		assert contract in service
	assert "ignore_permissions" not in service


def test_cbt_api_guards_every_mutation_with_platform_access():
	api = read("api/cbt.py")
	for action in (
		"schedule_exam",
		"activate_exam",
		"close_exam",
		"start_attempt",
		"resume_attempt",
		"sync_answers",
		"submit_attempt",
		"record_integrity_event",
		"approve_attempt_result",
	):
		assert f'@guard_eduedge_action("cbt", action="{action}")' in api
	assert "get_invigilator_monitor" in api
	assert "get_exam_access" in api


def test_cbt_permissions_and_timeout_scheduler_are_registered():
	hooks = read("hooks.py")
	for doctype in (
		"EduEdge CBT Question",
		"EduEdge CBT Exam",
		"EduEdge CBT Attempt",
		"EduEdge CBT Attempt Answer",
		"EduEdge CBT Sync Log",
	):
		assert f'"{doctype}"' in hooks
	assert "eduedge.cbt.tasks.refresh_attempt_timeouts" in hooks
	permissions = read("cbt/permissions.py")
	assert "attempt.user" in permissions
	assert "get_allowed_school_branches" in permissions
	assert "1=0" in permissions


def test_cbt_sync_log_is_append_only_and_counts_are_balanced():
	controller = read("eduedge/doctype/eduedge_cbt_sync_log/eduedge_cbt_sync_log.py")
	assert "before_save" in controller
	assert "append-only" in controller
	assert "cannot be deleted" in controller
	assert "sum(counts) != cint(self.received_count)" in controller


def test_cbt_foundation_documents_scope_and_next_phase():
	doc = (REPO_ROOT / "docs" / "eduedge_offline_resilient_cbt_v0_8.md").read_text(encoding="utf-8")
	for contract in (
		"Offline-Resilient CBT Foundation",
		"server authoritative",
		"Pending Sync attempts cannot be approved",
		"full LAN/offline server mode",
		"IndexedDB answer queue",
		"Assessment Result",
	):
		assert contract in doc
