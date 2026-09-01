from __future__ import annotations

import ast
import json
import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
APP_ROOT = REPO_ROOT / "eduedge"


class TestRepositoryContract(unittest.TestCase):
	def test_hooks_require_product_dependencies_not_coreedge(self):
		hooks = (APP_ROOT / "hooks.py").read_text()
		self.assertIn('"erpnext"', hooks)
		self.assertIn('"education"', hooks)
		self.assertIn('"edgesuite_ui"', hooks)
		self.assertNotIn('"coreedge"', hooks)

	def test_no_python_coreedge_imports(self):
		violations = []
		for path in APP_ROOT.rglob("*.py"):
			tree = ast.parse(path.read_text(), filename=str(path))
			for node in ast.walk(tree):
				if isinstance(node, ast.Import):
					for alias in node.names:
						if alias.name == "coreedge" or alias.name.startswith("coreedge."):
							violations.append(str(path))
				elif isinstance(node, ast.ImportFrom):
					if node.module == "coreedge" or str(node.module).startswith("coreedge."):
						violations.append(str(path))
		self.assertEqual(violations, [])

	def test_all_json_files_are_valid(self):
		for path in APP_ROOT.rglob("*.json"):
			with self.subTest(path=path):
				json.loads(path.read_text())

	def test_doctype_packages_have_controller_and_init(self):
		doctype_root = APP_ROOT / "eduedge" / "doctype"
		for json_path in sorted(doctype_root.glob("*/*.json")):
			with self.subTest(path=json_path):
				self.assertEqual(json_path.parent.name, json_path.stem)
				self.assertTrue((json_path.parent / "__init__.py").exists())
				controller = json_path.with_suffix(".py")
				self.assertTrue(controller.exists())
				compile(controller.read_text(), str(controller), "exec")

	def test_setup_loader_loads_edgesuite_first(self):
		path = (
			APP_ROOT
			/ "eduedge"
			/ "page"
			/ "eduedge_setup_center"
			/ "eduedge_setup_center.js"
		)
		source = path.read_text()
		self.assertLess(source.index("edgeui.bundle.js"), source.index("eduedge_setup_center.bundle.js"))
		self.assertIn("window.EdgeSuiteUI", source)


if __name__ == "__main__":
	unittest.main()
