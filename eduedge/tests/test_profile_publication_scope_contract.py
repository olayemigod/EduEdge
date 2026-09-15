from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestProfilePublicationScopeContract(unittest.TestCase):
	def test_assessment_group_is_optional_for_profile_publications(self):
		path = APP / "eduedge" / "doctype" / "eduedge_result_publication" / "eduedge_result_publication.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in payload["fields"]}
		self.assertFalse(fields["assessment_group"].get("reqd"))
		service = (APP / "education" / "result_profile.py").read_text()
		self.assertIn("Select either a Result Profile or an Assessment Group, not both.", service)
		self.assertIn("Select a Result Profile or Assessment Group.", service)

	def test_profile_scope_lookup_does_not_collapse_into_blank_assessment_group(self):
		api = (APP / "api" / "assessment_operations.py").read_text()
		self.assertIn("def _publication_scope_filters(", api)
		self.assertIn('filters["result_profile"] = result_profile', api)
		self.assertIn('filters["assessment_group"] = ["is", "not set"]', api)
		self.assertIn('filters["result_profile"] = ["is", "not set"]', api)

	def test_revision_lock_includes_profile_and_mode(self):
		api = (APP / "api" / "assessment_operations.py").read_text()
		self.assertIn("coalesce(result_profile, '')=%(result_profile)s", api)
		self.assertIn("result_mode=%(result_mode)s for update", api)
		model = (APP / "eduedge" / "doctype" / "eduedge_result_publication" / "eduedge_result_publication.py").read_text()
		self.assertIn('"result_profile": self.result_profile if self.result_profile else ["is", "not set"]', model)
		self.assertIn('"result_mode": self.result_mode or "Terminal"', model)


if __name__ == "__main__":
	unittest.main()
