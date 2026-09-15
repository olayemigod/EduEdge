from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResultEngineFoundationContract(unittest.TestCase):
	def test_result_profile_uses_native_assessment_groups_not_a_shadow_marks_ledger(self):
		path = APP / "eduedge" / "doctype" / "eduedge_result_profile" / "eduedge_result_profile.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in payload["fields"]}
		self.assertEqual(fields["components"]["options"], "EduEdge Result Component")
		self.assertEqual(fields["component_sources"]["options"], "EduEdge Result Component Source")
		source_path = APP / "eduedge" / "doctype" / "eduedge_result_component_source" / "eduedge_result_component_source.json"
		source = json.loads(source_path.read_text())
		source_fields = {field["fieldname"]: field for field in source["fields"]}
		self.assertEqual(source_fields["assessment_group"]["options"], "Assessment Group")
		self.assertNotIn("Assessment Result", payload["name"])

	def test_statistics_are_configurable_and_chs_cls_cas_are_not_hardcoded(self):
		path = APP / "eduedge" / "doctype" / "eduedge_result_metric" / "eduedge_result_metric.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in payload["fields"]}
		for fieldname in (
			"metric_key",
			"display_label",
			"calculation_basis",
			"display_as",
			"decimal_places",
			"show_on_terminal",
			"show_on_annual",
		):
			self.assertIn(fieldname, fields)
		raw = path.read_text()
		self.assertNotIn('"CHS"', raw)
		self.assertNotIn('"CLS"', raw)
		self.assertNotIn('"CAS"', raw)
		self.assertIn("Class Highest", fields["metric_key"]["options"])
		self.assertIn("Annual Average Percentage", fields["calculation_basis"]["options"])
		self.assertIn("Percentage", fields["display_as"]["options"])

	def test_native_grade_term_and_result_records_receive_upgrade_safe_fields(self):
		text = (APP / "education" / "result_fields.py").read_text()
		self.assertIn('"Grading Scale Interval"', text)
		self.assertIn("eduedge_report_remark", text)
		self.assertIn('"Academic Term"', text)
		self.assertIn("eduedge_report_label", text)
		self.assertIn("eduedge_annual_weight", text)
		self.assertIn('"Assessment Result"', text)
		self.assertIn("eduedge_score_state", text)
		self.assertIn("Not Offered", text)

	def test_result_engine_resolves_nested_assessment_groups_recursively(self):
		text = (APP / "education" / "result_profile.py").read_text()
		self.assertIn("resolve_assessment_group_leaves", text)
		self.assertIn('"lft": [">", group.lft]', text)
		self.assertIn('"rgt": ["<", group.rgt]', text)
		self.assertIn('"is_group": 0', text)

	def test_result_engine_keeps_zero_distinct_from_absence_and_not_offered(self):
		text = (APP / "education" / "result_engine.py").read_text()
		self.assertIn('SCORE_STATES = {"Scored", "Absent", "Exempt", "Not Offered"}', text)
		self.assertIn('"Treat as Zero"', text)
		self.assertIn('state in {"Exempt", "Not Offered"}', text)
		self.assertIn('0.0 if state == "Absent"', text)

	def test_publication_can_select_terminal_or_annual_profile_without_breaking_history(self):
		path = APP / "eduedge" / "doctype" / "eduedge_result_publication" / "eduedge_result_publication.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in payload["fields"]}
		self.assertEqual(fields["result_profile"]["options"], "EduEdge Result Profile")
		self.assertEqual(fields["result_mode"]["options"], "Terminal\nAnnual")
		service = (APP / "education" / "result_profile.py").read_text()
		self.assertIn("if not doc.get(\"result_profile\")", service)
		self.assertIn('result_mode == "Annual" and doc.academic_term', service)

	def test_result_profile_is_branch_and_institution_permission_scoped(self):
		hooks = (APP / "hooks.py").read_text()
		self.assertIn('"EduEdge Result Profile"', hooks)
		self.assertIn("result_profile_query", hooks)
		self.assertIn("has_result_profile_permission", hooks)
		permissions = (APP / "education" / "result_profile_permissions.py").read_text()
		self.assertIn("school_branch", permissions)
		self.assertIn("institution", permissions)
		self.assertIn('return "1=0"', permissions)

	def test_install_and_migrate_ensure_result_engine_custom_fields(self):
		install = (APP / "install.py").read_text()
		self.assertIn("ensure_result_engine_custom_fields", install)
		self.assertGreaterEqual(install.count("ensure_result_engine_custom_fields()"), 2)


if __name__ == "__main__":
	unittest.main()
