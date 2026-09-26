from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResultProfilePublicationUIContract(unittest.TestCase):
	def test_profile_publication_does_not_require_legacy_assessment_group(self):
		path = APP / "eduedge" / "doctype" / "eduedge_result_publication" / "eduedge_result_publication.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in payload["fields"]}
		self.assertFalse(fields["assessment_group"].get("reqd"))
		service = (APP / "education" / "assessment_operations.py").read_text()
		self.assertIn("Select either a Result Profile or an Assessment Group", service)
		self.assertIn('assessment_group: str | None = None', service)

	def test_assessment_context_exposes_branch_safe_result_profiles(self):
		api = (APP / "api" / "assessment_operations.py").read_text()
		self.assertIn('result_profile: str | None = None', api)
		self.assertIn('result_mode: str | None = None', api)
		self.assertIn('"EduEdge Result Profile"', api)
		self.assertIn('"result_profiles": result_profiles', api)
		self.assertIn("profile_groups", api)
		self.assertIn('result_mode == "Annual"', api)
		self.assertIn('group_filters["academic_term"] = ["is", "not set"]', api)

	def test_new_governed_publications_require_result_profile(self):
		service = (APP / "education" / "assessment_operations.py").read_text()
		api = (APP / "api" / "assessment_operations.py").read_text()
		vue = (APP / "public" / "js" / "eduedge_assessment_operations" / "EduEdgeAssessmentOperations.vue").read_text()
		self.assertIn("PROFILE_BACKED_PUBLICATION_REQUIRED", service)
		self.assertIn("def assert_profile_backed_publication", service)
		self.assertIn("if doc.is_new():", service)
		self.assertIn("assert_profile_backed_publication(doc)", service)
		self.assertGreaterEqual(api.count("assert_profile_backed_publication("), 4)
		self.assertIn("!context.publication && filters.result_profile", vue)
		self.assertIn("Existing legacy Assessment Group publications remain available for read and history only.", vue)
		self.assertIn("Legacy Assessment Group publication — read/history only.", vue)

	def test_legacy_publication_cannot_advance_or_spawn_revision(self):
		api = (APP / "api" / "assessment_operations.py").read_text()
		for function_name in (
			"request_result_approval",
			"approve_results",
			"publish_results",
			"create_result_publication_revision",
		):
			block = api.split(f"def {function_name}", 1)[1].split("\n\n", 1)[0]
			self.assertIn("assert_profile_backed_publication(", block)


if __name__ == "__main__":
	unittest.main()
