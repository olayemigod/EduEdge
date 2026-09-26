from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResultProfileIdentityContract(unittest.TestCase):
	def test_profile_name_is_not_globally_unique_across_institutions(self):
		path = APP / "eduedge" / "doctype" / "eduedge_result_profile" / "eduedge_result_profile.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in payload["fields"]}
		self.assertFalse(fields["profile_name"].get("unique"))
		self.assertEqual(payload["autoname"], "EDU-RPF-.YYYY.-.#####")
		service = (APP / "education" / "result_profile.py").read_text()
		self.assertIn("_validate_profile_name_scope", service)
		self.assertIn('"institution": doc.institution', service)
		self.assertIn('"school_branch": doc.school_branch if doc.school_branch else ["is", "not set"]', service)


if __name__ == "__main__":
	unittest.main()
