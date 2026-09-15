from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResultBroadsheetContract(unittest.TestCase):
	def test_broadsheet_uses_published_immutable_snapshots_only(self):
		api = (APP / "api" / "result_broadsheet.py").read_text()
		self.assertIn('"EduEdge Published Result Snapshot"', api)
		self.assertIn('"EduEdge Result Publication"', api)
		self.assertIn('"status": "Published"', api)
		self.assertNotIn('"Assessment Result"', api)

	def test_terminal_requires_term_and_annual_uses_blank_term(self):
		api = (APP / "api" / "result_broadsheet.py").read_text()
		self.assertIn('result_mode == "Annual"', api)
		self.assertIn('filters["academic_term"] = ["is", "not set"]', api)
		self.assertIn("Select an Academic Term for a Terminal broadsheet.", api)

	def test_ambiguous_profile_scope_requires_exact_publication(self):
		api = (APP / "api" / "result_broadsheet.py").read_text()
		vue = (APP / "public" / "js" / "eduedge_result_broadsheet" / "EduEdgeResultBroadsheet.vue").read_text()
		self.assertIn("publication_choices", api)
		self.assertIn("More than one published Result Profile exists", api)
		self.assertIn("Selected Result Publication is outside this broadsheet scope.", api)
		self.assertIn("Published Result", vue)
		self.assertIn("publicationLabel", vue)

	def test_rank_is_not_inferred_without_policy(self):
		api = (APP / "api" / "result_broadsheet.py").read_text()
		self.assertIn("Position/rank is not inferred", api)
		self.assertNotIn('"position"', api)

	def test_csv_export_uses_same_snapshot_payload(self):
		api = (APP / "api" / "result_broadsheet.py").read_text()
		self.assertIn("def download_broadsheet_csv", api)
		self.assertIn("data = _build_broadsheet", api)
		self.assertIn("csv.writer", api)

	def test_page_has_sticky_identity_columns_and_dynamic_subject_columns(self):
		vue = (APP / "public" / "js" / "eduedge_result_broadsheet" / "EduEdgeResultBroadsheet.vue").read_text()
		self.assertIn("sticky-col", vue)
		self.assertIn('v-for="subject in report.subjects"', vue)
		self.assertIn("Export CSV", vue)


if __name__ == "__main__":
	unittest.main()
