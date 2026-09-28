from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSnapshotTermLabelContract(unittest.TestCase):
	def test_terminal_snapshot_freezes_institution_term_display_label(self):
		text = (APP / "education" / "result_snapshots.py").read_text()
		self.assertIn('"academic_term_label": _academic_term_report_label(', text)
		self.assertIn("def _academic_term_report_label", text)
		self.assertIn('period.get("display_label")', text)


if __name__ == "__main__":
	unittest.main()
