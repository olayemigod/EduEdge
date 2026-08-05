from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentAssetLoadingContract(unittest.TestCase):
	def test_cache_safe_bundle_exports_instructor_and_legacy_globals(self):
		bundle = (APP / "public" / "js" / "eduedge_teacher_assignments.bundle.js").read_text(encoding="utf-8")
		for token in (
			"createEduEdgeInstructorAssignmentsApp",
			"window.EduEdgeInstructorAssignments",
			"window.createEduEdgeInstructorAssignmentsApp",
			"window.EduEdgeTeacherAssignments",
			"window.createEduEdgeTeacherAssignmentsApp",
		):
			self.assertIn(token, bundle)

	def test_page_loader_prefers_cache_safe_bundle_and_falls_back_to_legacy_asset(self):
		loader = (
			APP
			/ "eduedge"
			/ "page"
			/ "eduedge_instructor_assignments"
			/ "eduedge_instructor_assignments.js"
		).read_text(encoding="utf-8")
		self.assertLess(
			loader.index("eduedge_teacher_assignments.bundle.js"),
			loader.index("eduedge_instructor_assignments.bundle.js"),
		)
		self.assertIn("instructor_assignment_factory", loader)
		self.assertIn("instructor_assignment_component", loader)
		self.assertIn("load_instructor_assignments_bundle", loader)
		self.assertIn("Rebuild EduEdge assets and hard-refresh the browser", loader)


if __name__ == "__main__":
	unittest.main()
