import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ACCESS_PATH = ROOT / "eduedge" / "access_control.py"
MENU_PATH = ROOT / "eduedge" / "public" / "js" / "eduedge_product_menu.bundle.js"


class TestOperationalRouteVisibilityContract(unittest.TestCase):
	def _route_requirements(self):
		tree = ast.parse(ACCESS_PATH.read_text())
		for node in tree.body:
			if not isinstance(node, ast.Assign):
				continue
			if any(isinstance(target, ast.Name) and target.id == "ROUTE_REQUIREMENTS" for target in node.targets):
				return ast.literal_eval(node.value)
		self.fail("ROUTE_REQUIREMENTS was not found")

	def test_academic_operations_requires_attendance_operation_right(self):
		requirements = self._route_requirements()["/app/eduedge-academic-operations"]
		self.assertEqual(
			set(requirements),
			{
				("student_attendance", "create"),
				("student_attendance", "write"),
			},
		)
		self.assertNotIn(("student_group", "read"), requirements)
		self.assertNotIn(("room", "read"), requirements)

	def test_assessment_operations_requires_create_or_write(self):
		requirements = self._route_requirements()["/app/eduedge-assessment-operations"]
		self.assertEqual(
			set(requirements),
			{
				("assessment_plan", "create"),
				("assessment_plan", "write"),
				("assessment_result", "create"),
				("assessment_result", "write"),
			},
		)
		self.assertNotIn(("assessment_plan", "read"), requirements)
		self.assertNotIn(("assessment_result", "read"), requirements)

	def test_setup_center_matches_settings_read_api(self):
		requirements = self._route_requirements()["/app/eduedge-setup-center"]
		self.assertEqual(requirements, (("eduedge_settings", "read"),))

	def test_product_menu_filters_all_three_routes_through_manifest(self):
		menu = MENU_PATH.read_text()
		self.assertIn('"/app/eduedge-academic-operations"', menu)
		self.assertIn('"/app/eduedge-assessment-operations"', menu)
		self.assertIn('"/app/eduedge-setup-center"', menu)
		self.assertIn("manifest.routes", menu)
		self.assertIn("itemAllowed", menu)


if __name__ == "__main__":
	unittest.main()
