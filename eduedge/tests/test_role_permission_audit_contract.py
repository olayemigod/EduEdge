import ast
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EDUEDGE = ROOT / "eduedge"
PAGE_ROOT = EDUEDGE / "eduedge" / "page"


class TestRolePermissionAuditContract(unittest.TestCase):
	def test_every_eduedge_page_shell_is_permission_neutral(self):
		baseline = (EDUEDGE / "permissions_baseline.py").read_text()
		page_names = (
			"eduedge_home",
			"eduedge_academic_operations",
			"eduedge_admissions",
			"eduedge_applicants",
			"eduedge_students",
			"eduedge_programs",
			"eduedge_program_offerings",
			"eduedge_cbt_operations",
			"eduedge_question_builder",
			"eduedge_question_batch",
			"eduedge_assessment_operations",
			"eduedge_report_cards",
			"eduedge_school_branches",
			"eduedge_branch_governance",
			"eduedge_setup_center",
			"eduedge_settings_center",
			"eduedge_training_centre",
		)
		for folder in page_names:
			payload = json.loads((PAGE_ROOT / folder / f"{folder}.json").read_text())
			self.assertEqual(payload["roles"], [], folder)
			self.assertIn(payload["name"], baseline)
		self.assertIn('frappe.db.delete(\n\t\t\t"Has Role"', baseline)

	def test_boot_menu_and_navigation_share_permission_manifest(self):
		access = (EDUEDGE / "access_control.py").read_text()
		boot = (EDUEDGE / "boot.py").read_text()
		menu = (EDUEDGE / "public" / "js" / "eduedge_product_menu.bundle.js").read_text()
		navigation = (EDUEDGE / "public" / "js" / "eduedge_ui" / "navigation.js").read_text()
		self.assertIn("RESOURCE_DOCTYPES", access)
		self.assertIn("ROUTE_REQUIREMENTS", access)
		self.assertIn("user_has_role_permission", access)
		self.assertIn("get_valid_perms", access)
		self.assertIn('bootinfo["eduedge_access_manifest"] = build_access_manifest', boot)
		self.assertIn("eduedge_access_manifest", menu)
		self.assertIn("itemAllowed", menu)
		self.assertIn("eduedge_access_manifest", navigation)
		self.assertIn("hasEduEdgeRouteAccess", navigation)
		self.assertIn("Your current role permissions do not provide access", navigation)

	def test_permission_baseline_is_one_time_and_preserves_standard_rows(self):
		baseline = (EDUEDGE / "permissions_baseline.py").read_text()
		install = (EDUEDGE / "install.py").read_text()
		patches = (EDUEDGE / "patches.txt").read_text()
		patch = (EDUEDGE / "patches" / "v0_8" / "apply_role_permission_baseline.py").read_text()
		self.assertIn("setup_custom_perms(doctype)", baseline)
		self.assertIn("add_permission", baseline)
		self.assertIn("update_permission_property", baseline)
		self.assertIn("apply_role_permission_baseline", patches)
		self.assertIn("apply_default_permission_baseline", patch)
		self.assertIn("ensure_eduedge_page_role_baseline", patch)
		after_migrate = install.split("def after_migrate", 1)[1].split("def ensure_roles", 1)[0]
		self.assertNotIn("apply_default_permission_baseline", after_migrate)
		self.assertIn("ensure_eduedge_page_role_baseline", after_migrate)

	def test_installed_role_audit_classifies_custom_and_native_roles(self):
		baseline = (EDUEDGE / "permissions_baseline.py").read_text()
		for marker in (
			"def get_role_permission_audit",
			'frappe.get_all(\n\t\t"Role"',
			"custom_or_unclassified",
			"native_erpnext_no_eduedge_default",
			"eduedge_managed_default",
			"portal_only",
			"unclassified_desk_roles",
			"remaining_page_role_gates",
			"audited_permissions",
		):
			self.assertIn(marker, baseline)
		for role in (
			"HR User",
			"Stock Manager",
			"Purchase User",
			"Sales Manager",
			"Student",
			"Guardian",
			"EduEdge Parent",
		):
			self.assertIn(f'"{role}"', baseline)

	def test_school_managers_receive_safe_defaults_without_global_security_grants(self):
		baseline = (EDUEDGE / "permissions_baseline.py").read_text()
		self.assertIn('SCHOOL_MANAGERS = (', baseline)
		self.assertIn('_grant(matrix, "EduEdge Training Course", managers, MANAGE)', baseline)
		self.assertIn('_grant(matrix, "EduEdge Training Progress", managers, MANAGE)', baseline)
		self.assertNotIn('"Role Permission Manager"', baseline)
		self.assertNotIn('"Custom DocPerm", managers', baseline)

	def test_branch_hooks_scope_any_effectively_authorised_custom_role(self):
		education_permissions = (EDUEDGE / "education" / "permissions.py").read_text()
		cbt_permissions = (EDUEDGE / "cbt" / "permissions.py").read_text()
		self.assertIn("user_has_role_permission", education_permissions)
		self.assertIn("return True", education_permissions)
		self.assertNotIn("OPERATIONAL_ROLES", education_permissions)
		self.assertIn("user_has_role_permission", cbt_permissions)
		self.assertIn("return True", cbt_permissions)
		self.assertNotIn("CBT_OPERATIONAL_ROLES", cbt_permissions)
		self.assertIn("school_branch` is not null", cbt_permissions)

	def test_review_and_training_oversight_are_configurable_without_recursion(self):
		question = (
			EDUEDGE
			/ "eduedge"
			/ "doctype"
			/ "eduedge_cbt_question"
			/ "eduedge_cbt_question.py"
		).read_text()
		template = (
			EDUEDGE
			/ "eduedge"
			/ "doctype"
			/ "eduedge_cbt_exam_template"
			/ "eduedge_cbt_exam_template.py"
		).read_text()
		training = (EDUEDGE / "training" / "permissions.py").read_text()
		self.assertIn('user_has_role_permission("EduEdge CBT Question", "delete", user)', question)
		self.assertIn('user_has_role_permission("EduEdge CBT Exam Template", "delete", user)', template)
		self.assertNotIn("REVIEW_ROLES", question)
		self.assertNotIn("REVIEW_ROLES", template)
		self.assertIn('user_has_role_permission(TRAINING_PROGRESS_DOCTYPE, "delete", user)', training)
		self.assertNotIn("frappe.has_permission", training)

	def test_training_progress_controller_internal_imports_exist_and_portal_roles_are_excluded(self):
		controller_path = (
			EDUEDGE
			/ "eduedge"
			/ "doctype"
			/ "eduedge_training_progress"
			/ "eduedge_training_progress.py"
		)
		controller_text = controller_path.read_text()
		controller_tree = ast.parse(controller_text)
		self.assertNotIn("TRAINING_OVERSIGHT_ROLES", controller_text)
		self.assertIn("user_has_role_permission", controller_text)

		for node in ast.walk(controller_tree):
			if not isinstance(node, ast.ImportFrom) or not (node.module or "").startswith("eduedge."):
				continue
			module_path = ROOT.joinpath(*(node.module or "").split(".")).with_suffix(".py")
			self.assertTrue(module_path.exists(), f"Missing internal module {node.module}")
			module_tree = ast.parse(module_path.read_text())
			defined_names = set()
			for statement in module_tree.body:
				if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
					defined_names.add(statement.name)
				elif isinstance(statement, (ast.Assign, ast.AnnAssign)):
					targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
					defined_names.update(target.id for target in targets if isinstance(target, ast.Name))
			for alias in node.names:
				self.assertIn(alias.name, defined_names, f"{node.module}.{alias.name} is not defined")

		metadata = json.loads(controller_path.with_suffix(".json").read_text())
		permissions = {row["role"]: row for row in metadata["permissions"]}
		for role in ("Student", "Guardian", "EduEdge Parent"):
			self.assertNotIn(role, permissions)
		for role in ("School Administrator", "Academic Administrator", "Education Manager"):
			self.assertEqual(permissions[role].get("delete"), 1)
		self.assertFalse(permissions["Teacher"].get("delete", 0))


if __name__ == "__main__":
	unittest.main()
