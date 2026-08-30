from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestPreQAReleaseHardeningContract(unittest.TestCase):
	def test_school_event_is_wired_to_branch_query_and_record_permissions(self):
		hooks = (APP / "hooks.py").read_text(encoding="utf-8")
		self.assertIn(
			'"EduEdge School Event": "eduedge.education.school_event_permissions.school_event_query"',
			hooks,
		)
		self.assertIn(
			'"EduEdge School Event": "eduedge.education.school_event_permissions.has_school_event_permission"',
			hooks,
		)

	def test_school_event_branch_permission_service_fails_closed_by_contract(self):
		source = (APP / "education" / "school_event_permissions.py").read_text(encoding="utf-8")
		for expected in (
			"def school_event_query",
			"def has_school_event_permission",
			"get_allowed_school_branches(user=user)",
			'if not allowed:\n\t\treturn "1=0"',
			'`tabEduEdge School Event`.`school_branch` in',
			'branch in allowed',
			'"System Manager"',
			'"EduEdge Super Administrator"',
			'"EduEdge Administrator"',
		):
			self.assertIn(expected, source)
		self.assertNotIn("return None", source)

	def test_school_event_controller_enforces_institution_calendar_and_audience_cascade(self):
		source = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_school_event"
			/ "eduedge_school_event.py"
		).read_text(encoding="utf-8")
		for expected in (
			'"EduEdge Institution Academic Calendar"',
			'"EduEdge Academic Calendar Period"',
			'"EduEdge Program Offering"',
			'"school_branch": self.school_branch',
			'"academic_year": self.academic_year',
			'"program": self.program',
			"PROGRAMME_AUDIENCE_SCOPES",
			"self.program = None",
			"self.student_group = None",
			"The selected Class / Programme is not offered by this Branch in the selected Academic Session.",
		):
			self.assertIn(expected, source)

	def test_school_event_lifecycle_history_and_publication_window_are_governed(self):
		source = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_school_event"
			/ "eduedge_school_event.py"
		).read_text(encoding="utf-8")
		for expected in (
			"def on_trash(self):",
			'if (self.status or "Draft") != "Draft":',
			"Only Draft School Events can be deleted.",
			"def _validate_publication_window(self):",
			"Publish Until cannot be earlier than Publish From.",
		):
			self.assertIn(expected, source)

	def test_school_calendar_context_uses_institution_owned_sessions_and_terms(self):
		hooks = (APP / "hooks.py").read_text(encoding="utf-8")
		self.assertIn(
			'"eduedge.api.school_calendar.get_school_calendar_context": "eduedge.api.school_calendar_hardened.get_school_calendar_context"',
			hooks,
		)
		self.assertIn(
			'"eduedge.api.school_calendar.get_event_form_options": "eduedge.api.school_calendar_hardened.get_event_form_options"',
			hooks,
		)
		source = (APP / "api" / "school_calendar_hardened.py").read_text(encoding="utf-8")
		for expected in (
			"def _institution_session_options",
			"def _institution_terms",
			'filters={"institution": institution, "enabled": 1}',
			'"parenttype": "EduEdge Institution Academic Calendar"',
			"Select an Academic Session configured for this Institution.",
			"Select a Term configured in this Institution Academic Calendar.",
			"program not in programs",
		):
			self.assertIn(expected, source)

	def test_shared_resource_pages_use_the_canonical_edgesuite_runtime(self):
		source = (APP / "public" / "js" / "eduedge_resource_page_loader.bundle.js").read_text(encoding="utf-8")
		self.assertIn('frappe.require("edgesuite_ui.bundle.js"', source)
		self.assertNotIn('frappe.require("edgeui.bundle.js"', source)
		self.assertIn("[window.EdgeSuiteUI, window.EdgeUI].find", source)
		self.assertIn('Boolean(candidate?.components?.EdgeAppShell)', source)
		self.assertNotIn("candidate?.components?.EdgeFormDialog", source)

	def test_school_calendar_is_reconciled_into_permission_filtered_product_menu(self):
		hooks = (APP / "hooks.py").read_text(encoding="utf-8")
		self.assertIn('"eduedge_product_menu_hardening.bundle.js"', hooks)
		source = (APP / "public" / "js" / "eduedge_product_menu_hardening.bundle.js").read_text(encoding="utf-8")
		for expected in (
			'const SCHOOL_CALENDAR_ROUTE = "/app/eduedge-school-calendar"',
			"calendarRouteAllowed",
			"eduedge_access_manifest",
			"getProductMenuConfig",
			"registerProductMenu",
			'item.route === "/app/eduedge-teaching-schedule"',
			'label: "School Calendar & Events"',
		):
			self.assertIn(expected, source)

	def test_existing_cbt_scoring_key_permission_hook_is_preserved(self):
		hooks = (APP / "hooks.py").read_text(encoding="utf-8")
		self.assertIn(
			'"EduEdge CBT Attempt Scoring Key": "eduedge.cbt.permissions.cbt_attempt_scoring_key_query"',
			hooks,
		)
		self.assertIn(
			'"EduEdge CBT Attempt Scoring Key": "eduedge.cbt.permissions.has_attempt_reference_permission"',
			hooks,
		)


if __name__ == "__main__":
	unittest.main()
