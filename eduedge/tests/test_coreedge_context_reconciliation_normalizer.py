from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from eduedge.services import coreedge_context_reconciliation

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestCoreEdgeContextReconciliationNormalizer(unittest.TestCase):
	def test_school_branch_normalizes_without_changing_local_authority(self):
		with patch.object(
			coreedge_context_reconciliation.frappe,
			"get_all",
			return_value=[
				{
					"name": "IKEJA",
					"branch_name": "Ikeja Campus",
					"branch_code": "IKEJA",
					"company": "Demo School",
					"enabled": 1,
					"platform_branch_id": "",
				}
			],
		):
			rows = coreedge_context_reconciliation.get_context_reconciliation_rows()

		self.assertEqual(
			rows,
			[
				{
					"local_doctype": "EduEdge School Branch",
					"local_name": "IKEJA",
					"local_label": "Ikeja Campus",
					"local_code": "IKEJA",
					"company": "Demo School",
					"active": True,
					"platform_branch_id": "",
				}
			],
		)

	def test_normalizer_is_read_only_and_does_not_import_coreedge(self):
		source = (APP / "services" / "coreedge_context_reconciliation.py").read_text(encoding="utf-8")
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
