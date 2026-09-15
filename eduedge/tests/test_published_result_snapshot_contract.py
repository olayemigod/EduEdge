from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestPublishedResultSnapshotContract(unittest.TestCase):
	def test_snapshot_doctype_is_read_only_and_hashed(self):
		path = APP / "eduedge" / "doctype" / "eduedge_published_result_snapshot" / "eduedge_published_result_snapshot.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"] for field in payload["fields"]}
		for fieldname in (
			"result_publication",
			"publication_version",
			"student",
			"school_branch",
			"result_profile",
			"result_mode",
			"payload_hash",
			"payload_json",
		):
			self.assertIn(fieldname, fields)
		for permission in payload["permissions"]:
			self.assertFalse(permission.get("write"))
			self.assertFalse(permission.get("create"))
		model = (path.with_suffix(".py")).read_text()
		self.assertIn("Published Result Snapshots are immutable", model)
		self.assertIn("sha256", model)

	def test_publish_creates_snapshots_without_mutating_assessment_results(self):
		api = (APP / "api" / "assessment_operations.py").read_text()
		service = (APP / "education" / "result_snapshots.py").read_text()
		self.assertIn("create_publication_snapshots", api)
		self.assertIn('payload["snapshot_count"]', api)
		self.assertNotIn('set_value("Assessment Result"', service)
		self.assertNotIn('db_set("Assessment Result"', service)
		self.assertIn("source_assessment_results", service)

	def test_snapshot_supports_ytd_metrics_and_correct_opened_day_semantics(self):
		service = (APP / "education" / "result_snapshots.py").read_text()
		self.assertIn("_requires_ytd_metrics", service)
		self.assertIn("_periods_through_term", service)
		self.assertIn("cumulative_score", service)
		self.assertIn("opened_dates", service)
		self.assertIn('"school_opened": school_opened', service)
		self.assertIn("present / school_opened", service)

	def test_publication_revisions_preserve_old_published_versions(self):
		publication_path = APP / "eduedge" / "doctype" / "eduedge_result_publication" / "eduedge_result_publication.json"
		payload = json.loads(publication_path.read_text())
		fields = {field["fieldname"] for field in payload["fields"]}
		self.assertIn("publication_version", fields)
		self.assertIn("supersedes_publication", fields)
		model = publication_path.with_suffix(".py").read_text()
		self.assertIn('"publication_version": self.publication_version or 1', model)
		api = (APP / "api" / "assessment_operations.py").read_text()
		self.assertIn("create_result_publication_revision", api)
		self.assertIn('"Revision Created"', api)
		self.assertIn("for update", api)

	def test_snapshot_permissions_are_branch_scoped(self):
		hooks = (APP / "hooks.py").read_text()
		permissions = (APP / "education" / "permissions.py").read_text()
		self.assertIn('"EduEdge Published Result Snapshot"', hooks)
		self.assertIn("published_result_snapshot_query", hooks)
		self.assertIn("has_published_result_snapshot_permission", hooks)
		self.assertIn('"EduEdge Published Result Snapshot"', permissions)


if __name__ == "__main__":
	unittest.main()
