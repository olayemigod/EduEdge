from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResultProfileSmartFormContract(unittest.TestCase):
	def test_source_component_key_is_guided_by_parent_components(self):
		path = APP / "eduedge" / "doctype" / "eduedge_result_component_source" / "eduedge_result_component_source.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in payload["fields"]}
		self.assertEqual(fields["component_key"]["fieldtype"], "Select")
		js = (APP / "eduedge" / "doctype" / "eduedge_result_profile" / "eduedge_result_profile.js").read_text()
		self.assertIn("refreshComponentKeyOptions", js)
		self.assertIn("EduEdge Result Component Source", js)

	def test_profile_requires_one_official_grading_scale(self):
		path = APP / "eduedge" / "doctype" / "eduedge_result_profile" / "eduedge_result_profile.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in payload["fields"]}
		self.assertTrue(fields["grading_scale"].get("reqd"))
		service = (APP / "education" / "result_profile.py").read_text()
		self.assertIn("Select the official Grading Scale for this Result Profile", service)

	def test_profile_links_are_cascade_filtered_by_institution(self):
		js = (APP / "eduedge" / "doctype" / "eduedge_result_profile" / "eduedge_result_profile.js").read_text()
		self.assertIn('frm.set_query("school_branch"', js)
		self.assertIn('frm.set_query("grading_scale"', js)
		self.assertIn('frm.set_query("assessment_group", "component_sources"', js)
		self.assertIn("eduedge_institution", js)
		service = (APP / "education" / "result_profile.py").read_text()
		self.assertIn("Grading Scale must belong to the selected Institution", service)
		self.assertIn("Assessment Group {0} must belong to the selected Institution", service)

	def test_institution_wide_write_requires_all_branch_scope(self):
		permissions = (APP / "education" / "result_profile_permissions.py").read_text()
		self.assertIn('permission_type in {"create", "write", "delete", "share"}', permissions)
		self.assertIn("institution_branches.issubset(branches)", permissions)

	def test_metric_form_prevents_incompatible_terminal_and_annual_bases(self):
		js = (APP / "eduedge" / "doctype" / "eduedge_result_profile" / "eduedge_result_profile.js").read_text()
		service = (APP / "education" / "result_profile.py").read_text()
		for token in (
			"TERMINAL_METRIC_BASES",
			"ANNUAL_METRIC_BASES",
			"reconcileMetricSurfaces",
			'show_on_terminal", 0',
			'show_on_annual", 0',
			'frappe.ui.form.on("EduEdge Result Metric"',
		):
			self.assertIn(token, js)
		for token in (
			"TERMINAL_METRIC_BASES",
			"ANNUAL_METRIC_BASES",
			"cannot use {1} on Terminal reports",
			"cannot use {1} on Annual reports",
		):
			self.assertIn(token, service)

	def test_zero_score_precision_is_not_treated_as_missing(self):
		engine = (APP / "education" / "result_engine.py").read_text()
		self.assertIn("def result_score_precision", engine)
		self.assertIn('if value in (None, "")', engine)
		self.assertNotIn('config.get("score_precision") or 2', engine)

	def test_profile_is_locked_during_approval_window(self):
		service = (APP / "education" / "result_profile.py").read_text()
		self.assertIn("assert_result_profile_mutable", service)
		self.assertIn('"Pending Approval"', service)
		self.assertIn('"Approved"', service)


if __name__ == "__main__":
	unittest.main()
