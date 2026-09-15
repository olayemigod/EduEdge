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


if __name__ == "__main__":
	unittest.main()
