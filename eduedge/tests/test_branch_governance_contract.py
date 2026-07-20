from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestBranchGovernanceContract(unittest.TestCase):
	def test_user_branch_access_has_required_scope_and_controls(self):
		path = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_user_branch_access"
			/ "eduedge_user_branch_access.json"
		)
		payload = json.loads(path.read_text())
		fields = {field["fieldname"] for field in payload["fields"]}
		for fieldname in (
			"user",
			"company",
			"school_branch",
			"branch_role",
			"is_default_branch",
			"can_switch_branch",
			"hq_all_branch_access",
			"valid_from",
			"valid_to",
			"enabled",
		):
			self.assertIn(fieldname, fields)
		roles = {row["role"] for row in payload["permissions"]}
		self.assertEqual(roles, {"System Manager", "EduEdge Administrator"})

	def test_enforcement_is_settings_gated_for_safe_rollout(self):
		settings = json.loads(
			(
				APP
				/ "eduedge"
				/ "doctype"
				/ "eduedge_settings"
				/ "eduedge_settings.json"
			).read_text()
		)
		fields = {field["fieldname"]: field for field in settings["fields"]}
		self.assertEqual(fields["enable_user_branch_access_enforcement"]["default"], "0")
		self.assertIn("allow_hq_all_branch_view", fields)

	def test_active_context_supports_company_scoped_all_branches(self):
		text = (APP / "services" / "branch_context.py").read_text()
		self.assertIn('ALL_BRANCHES_KEY = "__all__"', text)
		self.assertIn("hq_all_branch_access", text)
		self.assertIn("all_branch_companies", text)
		self.assertIn("active_company", text)
		self.assertIn("can_view_all_branches", text)
		self.assertIn("invalidate_user_branch_context", text)

	def test_operational_permissions_consume_authorised_branch_service(self):
		permissions = (APP / "education" / "permissions.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn("get_allowed_school_branches", permissions)
		self.assertIn("school_branch_query", permissions)
		self.assertIn('"EduEdge School Branch"', hooks)
		self.assertIn("has_school_branch_record_permission", hooks)

	def test_school_branch_contains_approved_accounting_defaults(self):
		path = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_school_branch"
			/ "eduedge_school_branch.json"
		)
		payload = json.loads(path.read_text())
		fields = {field["fieldname"] for field in payload["fields"]}
		for fieldname in (
			"contact_person",
			"academic_levels_offered",
			"default_income_cost_center",
			"default_expense_cost_center",
			"school_fees_income_account",
			"cbt_exam_fees_income_account",
			"admission_registration_income_account",
			"transport_fees_income_account",
			"default_receivable_account",
			"default_cash_account",
			"default_bank_account",
			"default_payment_gateway_account",
			"default_discount_account",
			"default_scholarship_bursary_account",
			"default_write_off_account",
			"default_inventory_account",
			"default_cost_of_goods_sold_account",
			"default_stock_adjustment_account",
		):
			self.assertIn(fieldname, fields)

	def test_accounting_resolver_does_not_create_or_mutate_documents(self):
		paths = [
			APP / "services" / "branch_accounting.py",
			APP / "api" / "branch_accounting.py",
		]
		text = "\n".join(path.read_text() for path in paths)
		for forbidden in (
			'frappe.new_doc("Sales Invoice")',
			'frappe.get_doc({"doctype": "Sales Invoice"',
			'frappe.new_doc("Payment Entry")',
			'frappe.new_doc("Journal Entry")',
			".submit()",
			".cancel()",
			"ignore_permissions=True",
		):
			self.assertNotIn(forbidden, text)
		self.assertIn("resolve_transaction_defaults", text)

	def test_coreedge_remains_remote_service_boundary(self):
		for path in APP.rglob("*.py"):
			if "tests" in path.parts:
				continue
			text = path.read_text()
			self.assertNotIn("import coreedge", text, path.as_posix())
			self.assertNotIn("from coreedge", text, path.as_posix())


if __name__ == "__main__":
	unittest.main()
