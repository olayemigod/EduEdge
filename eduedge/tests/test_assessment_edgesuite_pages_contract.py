from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
NAVIGATION = APP / "public" / "js" / "eduedge_ui" / "navigation.js"
PRODUCT_MENU = APP / "public" / "js" / "eduedge_product_menu.bundle.js"
RESOURCE_CENTER = APP / "api" / "resource_center.py"
MARKS_ENTRY = APP / "public" / "js" / "eduedge_marks_entry" / "EduEdgeMarksEntry.vue"
MARKS_WORKBENCH = APP / "api" / "assessment_workbenches.py"
RESULT_ANALYTICS = APP / "public" / "js" / "eduedge_result_analytics" / "EduEdgeResultAnalytics.vue"


RESOURCE_PAGES = {
	"eduedge_assessment_plans": ("eduedge-assessment-plans", "assessment_plans"),
	"eduedge_assessment_results": ("eduedge-assessment-results", "assessment_results"),
	"eduedge_result_profiles": ("eduedge-result-profiles", "result_profiles"),
	"eduedge_results_audit": ("eduedge-results-audit", "result_audit"),
}


class TestAssessmentEdgeSuitePagesContract(unittest.TestCase):
	def test_four_record_pages_use_shared_edgesuite_resource_center(self):
		for directory, (page_name, resource_key) in RESOURCE_PAGES.items():
			page_dir = APP / "eduedge" / "page" / directory
			self.assertTrue((page_dir / "__init__.py").exists())
			js = (page_dir / f"{directory}.js").read_text()
			json_text = (page_dir / f"{directory}.json").read_text()
			self.assertIn("registerEduEdgeResourcePage", js)
			self.assertIn(f'pageName: "{page_name}"', js)
			self.assertIn(f'resourceKey: "{resource_key}"', js)
			self.assertIn(f'"name": "{page_name}"', json_text)

	def test_marks_entry_and_analytics_are_edgesuite_vue_pages(self):
		for component in (MARKS_ENTRY, RESULT_ANALYTICS):
			text = component.read_text()
			for required in (
				"EdgeAppShell",
				"EdgePageLayout",
				"EdgePageHeader",
				"EdgeFilterBar",
				"EdgeDashboardLayout",
				"EdgeStatCard",
			):
				self.assertIn(required, text)
			style = text.split("<style scoped>", 1)[1].split("</style>", 1)[0]
			self.assertNotRegex(style, re.compile(r"#[0-9a-fA-F]{3,8}\\b"))
			self.assertNotIn("!important", style)

	def test_assessment_resource_contracts_exist(self):
		text = RESOURCE_CENTER.read_text()
		for key in ("assessment_plans", "assessment_results", "result_profiles", "result_audit"):
			self.assertIn(f'"{key}": {{', text)
		self.assertIn('"create_route": "/app/eduedge-marks-entry"', text)
		self.assertIn('"read_only": True', text)

	def test_navigation_and_product_menu_use_only_eduedge_routes_for_six_pages(self):
		edge_routes = (
			"/app/eduedge-assessment-plans",
			"/app/eduedge-marks-entry",
			"/app/eduedge-assessment-results",
			"/app/eduedge-result-profiles",
			"/app/eduedge-result-analytics",
			"/app/eduedge-results-audit",
		)
		for path in (NAVIGATION, PRODUCT_MENU):
			text = path.read_text()
			for route in edge_routes:
				self.assertIn(route, text)

	def test_marks_entry_uses_explicit_save_not_keystroke_network_calls(self):
		text = MARKS_ENTRY.read_text()
		self.assertIn("Save Row", text)
		self.assertIn("@input=\"markDirty(row)\"", text)
		self.assertIn('@change="changeScoreState(row)"', text)
		self.assertIn("save_marks_entry", text)
		self.assertNotIn('@input="saveRow(row)"', text)
		self.assertNotIn('@change="saveRow(row)"', text)

	def test_marks_entry_supports_governed_score_states(self):
		vue = MARKS_ENTRY.read_text()
		api = MARKS_WORKBENCH.read_text()
		for token in (
			'"Scored", "Absent", "Exempt", "Not Offered"',
			'v-model="row.score_state"',
			"changeScoreState(row)",
			"row.score_state !== 'Scored'",
			'row.score_state === "Scored" ? "" : 0',
			'score_state: row.score_state',
			"saved.score_state",
			"those states store zero criterion scores",
		):
			self.assertIn(token, vue)
		for token in (
			"def _normalize_score_state",
			"state not in SCORE_STATES",
			"Absent, Exempt and Not Offered results must use zero scores.",
			"doc.eduedge_score_state = state",
			'"score_state": str(doc.get("eduedge_score_state") or "Scored")',
		):
			self.assertIn(token, api)

	def test_marks_entry_rejects_malformed_scores_before_document_save(self):
		text = MARKS_WORKBENCH.read_text()
		self.assertIn(
			"from eduedge.education.assessment_operations import normalize_assessment_result_score",
			text,
		)
		parser = text.split("def _parse_scores", 1)[1].split("@frappe.whitelist()", 1)[0]
		self.assertIn("normalize_assessment_result_score(value, str(key))", parser)
		self.assertNotIn("flt(value)", parser)

	def test_marks_entry_reuses_current_mark_capability_governance(self):
		text = MARKS_WORKBENCH.read_text()
		for token in (
			"from eduedge.api.assessment_assignment_options import assessment_result_plan_query",
			"from eduedge.api.assessment_result_tool_safe import (",
			"_authorized_plan,",
			"get_assessment_details as get_safe_assessment_details",
			"get_assessment_students as get_safe_assessment_students",
			"def _get_mark_entry_plan",
			"plan, _group = _authorized_plan(name)",
			"rows = assessment_result_plan_query(",
			"criteria = get_safe_assessment_details(plan.name)",
			"students = get_safe_assessment_students(plan.name, plan.student_group)",
		):
			self.assertIn(token, text)
		self.assertGreaterEqual(text.count("_get_mark_entry_plan(assessment_plan)"), 3)
		self.assertNotIn("from education.education.api import", text)

	def test_result_analytics_separates_score_states_from_performance(self):
		api = MARKS_WORKBENCH.read_text()
		vue = RESULT_ANALYTICS.read_text()
		for token in (
			'fields.append("eduedge_score_state")',
			'row["score_state"] = str(row.get("eduedge_score_state") or "Scored")',
			'submitted_rows = [row for row in rows if cint(row.docstatus) == 1]',
			'row for row in submitted_rows',
			'if row.score_state == "Scored"',
			'grade_counts = Counter(str(row.grade or "Ungraded") for row in performance_rows)',
			'state_counts = Counter(row.score_state for row in submitted_rows)',
			'"scored": len(performance_rows)',
			'"non_scored": len(submitted_rows) - len(performance_rows)',
			'"score_state_distribution": [',
			'if row.score_state == "Scored" and flt(row.maximum_score) > 0',
			'"average_percentage": round(sum(percentages) / len(percentages), 2) if percentages else None',
		):
			self.assertIn(token, api)
		for token in (
			"<span>Score State</span>",
			"data.options.score_states",
			'label="Scored"',
			'label="Non-scored"',
			'helper="Submitted scored results only"',
			"data.score_state_distribution",
			"<th>Score State</th>",
			"row.score_state || 'Scored'",
			"scoreLabel(row)",
			'if (value === null || value === undefined) return "—";',
			'row.score_state === \'Scored\' ? percentageLabel(row.percentage) : \'—\'',
			'row.score_state === \'Scored\' ? (row.grade || \'—\') : \'—\'',
		):
			self.assertIn(token, vue)

	def test_result_analytics_uses_submitted_rows_for_official_performance(self):
		api = MARKS_WORKBENCH.read_text()
		vue = RESULT_ANALYTICS.read_text()
		for token in (
			'if status not in {"Draft", "Submitted", "Cancelled"}:',
			'Invalid document-status filter.',
			'submitted_rows = [row for row in rows if cint(row.docstatus) == 1]',
			'row for row in submitted_rows',
			'if row.score_state == "Scored"',
			'grade_counts = Counter(str(row.grade or "Ungraded") for row in performance_rows)',
			'state_counts = Counter(row.score_state for row in submitted_rows)',
			'"cancelled": sum(1 for row in rows if cint(row.docstatus) == 2)',
			'"scored": len(performance_rows)',
			'"non_scored": len(submitted_rows) - len(performance_rows)',
		):
			self.assertIn(token, api)
		for token in (
			'label="Cancelled"',
			'helper="Voided result records"',
			'helper="Submitted numeric performance rows"',
			'helper="Submitted absent, exempt or not offered"',
			'helper="Submitted scored results only"',
			"Submitted rows only",
			"Submitted scored results only",
			"cancelled: 0",
		):
			self.assertIn(token, vue)

	def test_result_analytics_filter_options_are_permission_aware_and_paged(self):
		api = MARKS_WORKBENCH.read_text()
		options = api.split("def _analytics_option_values", 1)[1].split(
			"@frappe.whitelist()",
			1,
		)[0]
		for token in (
			"ANALYTICS_OPTION_PAGE_SIZE = 250",
			"def _analytics_option_values(branch: str, fieldname: str)",
			'frappe.get_list(',
			'distinct=True',
			'order_by=f"{fieldname} asc"',
			"limit_start=offset",
			"limit_page_length=ANALYTICS_OPTION_PAGE_SIZE",
			"offset += len(rows)",
			'_analytics_option_values(branch, "academic_year")',
			'_analytics_option_values(branch, "academic_term")',
			'_analytics_option_values(branch, "student_group")',
			'_analytics_option_values(branch, "course")',
			'_analytics_option_values(branch, "assessment_group")',
		):
			self.assertIn(token, api)
		self.assertNotIn("limit_page_length=1000", options)
		self.assertNotIn("frappe.get_all(", options)

	def test_safe_mark_entry_payload_preserves_edgesuite_metadata(self):
		text = (APP / "api" / "assessment_result_tool_safe.py").read_text()
		for token in (
			'"assessment_group"',
			'"maximum_assessment_score"',
			'student_result["comment"] = result.comment',
			'"score_state": str(result.get("eduedge_score_state") or "Scored")',
		):
			self.assertIn(token, text)


if __name__ == "__main__":
	unittest.main()
