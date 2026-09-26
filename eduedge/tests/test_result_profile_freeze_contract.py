from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResultProfileFreezeContract(unittest.TestCase):
	def test_publication_stores_hidden_approved_profile_configuration(self):
		path = APP / "eduedge" / "doctype" / "eduedge_result_publication" / "eduedge_result_publication.json"
		payload = json.loads(path.read_text())
		fields = {row["fieldname"]: row for row in payload["fields"]}
		for fieldname in ("result_profile_config_hash", "result_profile_config_json"):
			self.assertIn(fieldname, fields)
			self.assertEqual(fields[fieldname].get("read_only"), 1)
			self.assertEqual(fields[fieldname].get("hidden"), 1)
			self.assertEqual(fields[fieldname].get("no_copy"), 1)

	def test_approval_freezes_current_profile_but_revision_preserves_source_profile(self):
		api = (APP / "api" / "assessment_operations.py").read_text()
		self.assertIn("freeze_publication_result_profile_config", api)
		self.assertIn("force_current=not bool(doc.supersedes_publication)", api)
		self.assertIn("source_profile_config = get_publication_result_profile_config(source)", api)
		self.assertIn("set_publication_result_profile_config(doc, source_profile_config)", api)

	def test_frozen_profile_has_integrity_hash_and_legacy_snapshot_fallback(self):
		service = (APP / "education" / "result_profile.py").read_text()
		self.assertIn("hashlib.sha256(payload.encode", service)
		self.assertIn("Result Publication profile configuration integrity check failed.", service)
		self.assertIn('"EduEdge Published Result Snapshot"', service)
		self.assertIn('{"result_publication": publication.get("name")}', service)
		self.assertIn('profile = (json.loads(snapshot_json) or {}).get("profile")', service)

	def test_frozen_profile_contains_resolved_progression_policy(self):
		service = (APP / "education" / "result_profile.py").read_text()
		self.assertIn("promotion_pass_average = resolve_profile_promotion_pass_average(doc)", service)
		self.assertIn('"progression": {', service)
		self.assertIn('"promotion_pass_average": promotion_pass_average', service)
		self.assertIn('"source": (', service)

	def test_readiness_and_snapshot_generation_use_frozen_profile(self):
		assessment = (APP / "education" / "assessment_operations.py").read_text()
		snapshots = (APP / "education" / "result_snapshots.py").read_text()
		api = (APP / "api" / "assessment_operations.py").read_text()
		self.assertIn("profile_config_override: dict | None = None", assessment)
		self.assertIn("get_publication_result_profile_config(publication_doc)", snapshots)
		self.assertIn("profile_config_override=config", snapshots)
		self.assertIn("def _readiness_profile_config", api)
		self.assertIn('publication.get("status") in {"Draft", "Rejected"}', api)
		self.assertIn('and not publication.get("supersedes_publication")', api)

	def test_revision_scope_is_backend_immutable_and_sequential(self):
		controller = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_result_publication"
			/ "eduedge_result_publication.py"
		).read_text()
		self.assertIn("A Result Publication revision must supersede a Published publication.", controller)
		self.assertIn("A Result Publication revision must use the next sequential version.", controller)
		self.assertIn("A Result Publication revision must preserve the original result scope.", controller)
		self.assertIn("A Result Publication revision scope cannot change.", controller)

	def test_frozen_profile_payload_is_not_exposed_to_assessment_operations_browser_context(self):
		api = (APP / "api" / "assessment_operations.py").read_text()
		self.assertIn('publication.pop("result_profile_config_json", None)', api)
		self.assertIn('publication.pop("result_profile_config_hash", None)', api)

	def test_published_profile_cannot_move_institution_or_branch_scope(self):
		service = (APP / "education" / "result_profile.py").read_text()
		self.assertIn("def _validate_historical_scope_identity", service)
		self.assertIn('("institution", "school_branch")', service)
		self.assertIn('{"result_profile": doc.name, "status": "Published"}', service)
		self.assertIn("Create a new Result Profile for the new scope.", service)


	def test_approval_freezes_academic_payload_until_publish(self):
		api = (APP / "api" / "assessment_operations.py").read_text()
		snapshots = (APP / "education" / "result_snapshots.py").read_text()
		schema = (APP / "eduedge" / "doctype" / "eduedge_result_publication" / "eduedge_result_publication.json").read_text()
		for token in (
			"approved_academic_payload_hash",
			"approved_academic_student_count",
		):
			self.assertIn(token, schema)
			self.assertIn(token, api)
		self.assertIn("def build_publication_approval_fingerprint", snapshots)
		self.assertIn('"academic_term_label": (payload.get("publication") or {}).get("academic_term_label")', snapshots)
		self.assertIn('"result": payload.get("result") or {}', snapshots)
		self.assertIn('presentation.get("show_attendance")', snapshots)
		self.assertIn('payload.get("attendance") or {}', snapshots)
		self.assertIn('"source_assessment_results"', snapshots)
		self.assertGreaterEqual(api.count("build_publication_approval_fingerprint("), 2)
		self.assertIn("Approved academic result data changed after approval.", api)
		self.assertIn("predates academic payload fingerprinting", api)


if __name__ == "__main__":
	unittest.main()
