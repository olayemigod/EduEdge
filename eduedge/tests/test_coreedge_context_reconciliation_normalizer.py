from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestCoreEdgeContextReconciliationNormalizer(unittest.TestCase):
	def read_normalizer(self) -> str:
		return (APP / "services" / "coreedge_context_reconciliation.py").read_text(encoding="utf-8")

	def test_school_branch_normalizer_exposes_required_reconciliation_contract(self):
		source = self.read_normalizer()
		for contract in (
			"def get_context_reconciliation_rows(",
			'"EduEdge School Branch"',
			'"name"',
			'"branch_name"',
			'"branch_code"',
			'"company"',
			'"enabled"',
			'"platform_branch_id"',
			'"local_doctype": "EduEdge School Branch"',
			'"local_name"',
			'"local_label"',
			'"local_code"',
			'"active"',
		):
			self.assertIn(contract, source)

	def test_platform_branch_id_is_diagnostic_only_in_normalizer(self):
		source = self.read_normalizer()
		self.assertIn('"platform_branch_id": str(row.get("platform_branch_id") or "").strip()', source)
		self.assertNotIn('frappe.db.set_value(', source)
		self.assertNotIn('doc.platform_branch_id =', source)

	def test_normalizer_is_read_only_and_does_not_import_coreedge(self):
		source = self.read_normalizer()
		self.assertNotIn("import coreedge", source)
		self.assertNotIn("from coreedge", source)
		for forbidden in (
			"ignore_permissions=True",
			".insert(",
			".save(",
			".submit(",
			"frappe.db.set_value(",
			"frappe.db.commit(",
		):
			self.assertNotIn(forbidden, source)


if __name__ == "__main__":
	unittest.main()
