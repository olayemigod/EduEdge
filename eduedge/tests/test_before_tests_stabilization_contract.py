from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestBeforeTestsStabilizationContract(unittest.TestCase):
	def test_test_root_stabilizer_is_not_registered_as_a_product_hook(self):
		hooks = (APP / "hooks.py").read_text()
		self.assertNotIn("ensure_erpnext_test_roots", hooks)

	def test_test_package_rechecks_root_inside_the_frappe_test_process(self):
		init = (APP / "tests" / "__init__.py").read_text()
		self.assertIn("ensure_erpnext_test_roots,", init)
		self.assertIn("ensure_erpnext_test_roots()", init)
		self.assertIn('getattr(frappe.local, "site", None)', init)

	def test_optional_doctype_guard_is_test_only(self):
		ci = (APP / "ci.py").read_text()
		init = (APP / "tests" / "__init__.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn("def install_frappe_v16_test_dependency_compat()", ci)
		self.assertIn('if not frappe.db.exists("DocType", doctype):', ci)
		self.assertIn("install_frappe_v16_test_dependency_compat()", init)
		self.assertNotIn("install_frappe_v16_test_dependency_compat", hooks)

	def test_upstream_fixture_relaxation_is_scoped_to_generator_insert(self):
		ci = (APP / "ci.py").read_text()
		self.assertIn("original_try_create = generators._try_create", ci)
		self.assertIn("def guarded_try_create(record, reset=False, commit=False):", ci)
		self.assertIn("academic_validation.validate_master_institution = fixture_validate_master_institution", ci)
		self.assertIn("finally:", ci)
		self.assertIn("academic_validation.validate_master_institution = original_validate", ci)
		self.assertIn("generators._try_create = guarded_try_create", ci)
		self.assertNotIn("required=False\n\treturn", (APP / "education" / "academic_validation.py").read_text())

	def test_explicit_workflow_stabilization_remains_before_run_tests(self):
		for filename in ("integration.yml", "edgesuite-ui-candidate-compat.yml"):
			workflow = (ROOT / ".github" / "workflows" / filename).read_text()
			self.assertIn("eduedge.ci.ensure_erpnext_test_roots", workflow)
			self.assertLess(
				workflow.index("eduedge.ci.ensure_erpnext_test_roots"),
				workflow.index("run-tests"),
			)


if __name__ == "__main__":
	unittest.main()
