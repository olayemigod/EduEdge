from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestModalRecordContract(unittest.TestCase):
	def test_api_is_allowlisted_permission_aware_and_uses_doc_validation(self):
		api = (APP / "api" / "modal_records.py").read_text(encoding="utf-8")
		for expected in (
			"RESOURCE_CONFIG",
			'"school_branch"',
			'"program_offering"',
			'"user_branch_access"',
			'"instructor_branch_assignment"',
			"get_modal_schema",
			"search_modal_options",
			"save_modal_record",
			'doc.check_permission("write")',
			'frappe.has_permission(doctype, "create")',
			"doc.insert()",
			"doc.save()",
			"Submitted records cannot be changed",
		):
			self.assertIn(expected, api)
		for forbidden in (
			"ignore_permissions=True",
			"ignore_permissions = True",
			"frappe.db.sql(",
			'frappe.new_doc("Sales Invoice")',
			'frappe.new_doc("Payment Entry")',
			'frappe.new_doc("Journal Entry")',
		):
			self.assertNotIn(forbidden, api)

	def test_options_are_context_filtered_and_bounded(self):
		api = (APP / "api" / "modal_records.py").read_text(encoding="utf-8")
		self.assertIn("MAX_OPTIONS = 30", api)
		self.assertIn("get_allowed_institutions(company=company)", api)
		self.assertIn("get_allowed_school_branches(company=company, institution=institution)", api)
		self.assertIn('filters={"enabled": 1, "user_type": "System User"}', api)
		self.assertIn('filters = {"academic_year": values.get("academic_year")}', api)
		self.assertIn("limit_page_length=MAX_OPTIONS", api)

	def test_client_uses_edgesuite_form_dialog_and_refreshes_after_save(self):
		client = (APP / "public/js/eduedge_ui/modal_records.js").read_text(encoding="utf-8")
		setup = (APP / "public/js/eduedge_setup_center/EduEdgeSetupCenter.vue").read_text(encoding="utf-8")
		governance = (
			APP / "public/js/eduedge_branch_governance/EduEdgeBranchGovernance.vue"
		).read_text(encoding="utf-8")
		for expected in (
			"get_modal_schema",
			"search_modal_options",
			"save_modal_record",
			"validateModal",
			"openRecordFullForm",
		):
			self.assertIn(expected, client)
		self.assertIn("<EdgeFormDialog", setup)
		self.assertIn("await this.loadReadiness()", setup)
		self.assertIn("<EdgeFormDialog", governance)
		self.assertIn("await this.loadContext()", governance)
		self.assertNotIn("new frappe.ui.Dialog", setup + governance)


if __name__ == "__main__":
	unittest.main()
