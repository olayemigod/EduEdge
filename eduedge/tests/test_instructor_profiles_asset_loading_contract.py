from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorProfilesAssetLoadingContract(unittest.TestCase):
	def test_cache_safe_bundle_exports_new_and_legacy_globals(self):
		bundle = (APP / "public" / "js" / "eduedge_instructor_profiles.bundle.js").read_text(encoding="utf-8")
		for token in (
			"createEduEdgeInstructorProfilesApp",
			"window.EduEdgeInstructorProfiles",
			"window.createEduEdgeInstructorProfilesApp",
			"window.EduEdgeInstructors",
			"window.createEduEdgeInstructorsApp",
		):
			self.assertIn(token, bundle)

	def test_page_loader_prefers_cache_safe_bundle_and_falls_back_to_legacy_asset(self):
		loader = (
			APP
			/ "eduedge"
			/ "page"
			/ "eduedge_instructors"
			/ "eduedge_instructors.js"
		).read_text(encoding="utf-8")
		self.assertLess(
			loader.index("eduedge_instructor_profiles.bundle.js"),
			loader.index("eduedge_instructors.bundle.js"),
		)
		self.assertIn("instructor_profiles_factory", loader)
		self.assertIn("instructor_profiles_component", loader)
		self.assertIn("load_instructor_profiles_bundle", loader)
		self.assertIn("Rebuild EduEdge assets and hard-refresh the browser", loader)


if __name__ == "__main__":
	unittest.main()
