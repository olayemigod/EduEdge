from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentNewestRowContract(unittest.TestCase):
	def test_new_academic_branch_and_duplicate_rows_are_promoted_to_top(self):
		bundle = (APP / "public" / "js" / "eduedge_instructor_assignments.bundle.js").read_text(encoding="utf-8")
		for token in (
			"keepNewestAssignmentRowOnTop",
			'keepNewestAssignmentRowOnTop("addAcademicRow")',
			'keepNewestAssignmentRowOnTop("addBranchAccessRow")',
			'keepNewestAssignmentRowOnTop("duplicateRow")',
			"this.rows.unshift(newest)",
			"scrollIntoView",
		):
			self.assertIn(token, bundle)


if __name__ == "__main__":
	unittest.main()
