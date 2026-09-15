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

	def test_profile_or_assessment_group_is_required_for_creation(self):
		api = (APP / "api" / "assessment_operations.py").read_text()
		self.assertIn("if not assessment_group and not result_profile", api)
		self.assertIn("Select a Result Profile or Assessment Group", api)


if __name__ == "__main__":
	unittest.main()
