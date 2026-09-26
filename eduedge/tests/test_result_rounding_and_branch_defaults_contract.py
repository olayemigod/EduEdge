from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResultRoundingAndBranchDefaultsContract(unittest.TestCase):
	def test_academic_result_rounding_is_decimal_half_up(self):
		engine = (APP / "education" / "result_engine.py").read_text()
		self.assertIn("ROUND_HALF_UP", engine)
		self.assertIn("def round_result_value", engine)
		self.assertIn("Decimal(str(flt(value)))", engine)
		self.assertIn("rounded = round_result_value(value, precision)", engine)

	def test_stale_default_warehouse_is_only_cleared_for_new_cross_company_default(self):
		branch = (APP / "eduedge" / "doctype" / "eduedge_school_branch" / "eduedge_school_branch.py").read_text()
		self.assertIn("def _clear_stale_default_warehouse", branch)
		self.assertIn('frappe.defaults.get_user_default("default_warehouse")', branch)
		self.assertIn("warehouse_company == self.company", branch)
		self.assertIn("if not self.is_new()", branch)
		self.assertIn("self.default_warehouse = None", branch)
		self.assertIn("Default Warehouse must belong to Company", branch)


if __name__ == "__main__":
	unittest.main()
