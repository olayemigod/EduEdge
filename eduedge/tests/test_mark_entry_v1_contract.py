from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestMarkEntryV1Contract(unittest.TestCase):
	def test_batch_api_writes_native_assessment_results_only(self):
		api = (APP / "api" / "mark_entry.py").read_text()
		self.assertIn("get_assessment_result_doc", api)
		self.assertIn('"Assessment Result"', api)
		self.assertNotIn("EduEdge Mark", api)
		self.assertIn("result.save()", api)

	def test_batch_api_enforces_membership_submitted_immutability_and_score_bounds(self):
		api = (APP / "api" / "mark_entry.py").read_text()
		self.assertIn('"Student Group Student"', api)
		self.assertIn("already submitted and cannot be changed", api)
		self.assertIn("value < 0 or value > maximum", api)
		self.assertIn("ALLOWED_SCORE_STATES", api)

	def test_non_numeric_states_are_persisted_without_confusing_genuine_zero(self):
		api = (APP / "api" / "mark_entry.py").read_text()
		self.assertIn('state == "Scored"', api)
		self.assertIn('"Absent"', api)
		self.assertIn('"Exempt"', api)
		self.assertIn('"Not Offered"', api)
		self.assertIn("result.eduedge_score_state = state", api)

	def test_browser_tool_supports_autosave_spreadsheet_paste_and_status(self):
		js = (APP / "public" / "js" / "education" / "assessment_result_tool.js").read_text()
		self.assertIn("MutationObserver", js)
		self.assertIn("clipboardData", js)
		self.assertIn("save_mark_entry_batch", js)
		self.assertIn("setTimeout(() => saveRows([row]), 650)", js)
		self.assertIn("eduedge-score-state", js)
		self.assertIn("Save all drafts", js)

	def test_partial_rows_are_browser_saved_until_server_complete(self):
		js = (APP / "public" / "js" / "education" / "assessment_result_tool.js").read_text()
		self.assertIn("localStorage.setItem", js)
		self.assertIn("restoreBrowserDraft", js)
		self.assertIn("rowReadyForServer", js)
		self.assertIn("Browser draft saved · complete the row to sync", js)
		self.assertIn("navigator.onLine", js)

	def test_successful_server_sync_clears_browser_draft(self):
		js = (APP / "public" / "js" / "education" / "assessment_result_tool.js").read_text()
		self.assertIn("clearBrowserRow(saved.student)", js)
		self.assertIn("localStorage.removeItem", js)

	def test_partial_rows_wait_for_completion_instead_of_failing_autosave(self):
		js = (APP / "public" / "js" / "education" / "assessment_result_tool.js").read_text()
		self.assertIn("const rowReadyForServer", js)
		self.assertIn("Browser draft saved · complete the row to sync", js)
		self.assertIn("editable.filter(rowReadyForServer)", js)

	def test_mark_entry_does_not_auto_submit(self):
		js = (APP / "public" / "js" / "education" / "assessment_result_tool.js").read_text()
		self.assertNotIn("submit_mark_entry_batch", js)
		self.assertIn("frm.events?.submit_result", js)


if __name__ == "__main__":
	unittest.main()
