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

	def test_installed_role_audit_classifies_and_flags_sensitive_access(self):
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
			"missing_doctypes",
			"sensitive_permission_warnings",
			"portal_roles_with_desk_access",
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

	def test_school_managers_and_hr_receive_report_based_training_oversight(self):
		baseline = (EDUEDGE / "permissions_baseline.py").read_text()
		self.assertIn('SCHOOL_MANAGERS = (', baseline)
		self.assertIn('SELF_PROGRESS = ("read", "create", "write")', baseline)
		self.assertIn('TRAINING_OVERSIGHT = SELF_PROGRESS + ("report", "export", "print")', baseline)
		self.assertIn('managers + ("School HR Officer",)', baseline)
		self.assertNotIn('"EduEdge Training Course"', baseline)
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
		question_review = question.split("def can_review_questions", 1)[1].split("def _require_question_author", 1)[0]
		self.assertIn('"EduEdge CBT Question", "write", resolved_user', question_review)
		self.assertIn('"EduEdge CBT Question", "report", resolved_user', question_review)
		self.assertNotIn('"delete"', question_review)
		self.assertIn('user_has_role_permission("EduEdge CBT Exam Template", "delete", user)', template)
		self.assertNotIn("REVIEW_ROLES", question)
		self.assertNotIn("REVIEW_ROLES", template)
		self.assertIn('TRAINING_OVERSIGHT_PERMISSION = "report"', training)
		self.assertIn("user_has_role_permission(TRAINING_PROGRESS_DOCTYPE, TRAINING_OVERSIGHT_PERMISSION, user)", training)
		self.assertNotIn("frappe.has_permission", training)

	def test_training_progress_controller_internal_imports_and_audit_safety(self):
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
		self.assertIn('TRAINING_OVERSIGHT_PERMISSION = "report"', controller_text)
		self.assertIn("def on_trash", controller_text)
		self.assertIn("Training progress records cannot be deleted", controller_text)

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
		for role in ("Student", "Guardian", "EduEdge Parent", "HR User", "Purchase User", "Stock User"):
			self.assertNotIn(role, permissions)
		for role in (
			"System Manager",
			"School Administrator",
			"Academic Administrator",
			"Education Manager",
			"School HR Officer",
		):
			self.assertEqual(permissions[role].get("report"), 1)
			self.assertFalse(permissions[role].get("delete", 0))
		self.assertFalse(permissions["Teacher"].get("report", 0))
		self.assertFalse(permissions["Teacher"].get("delete", 0))

	def test_training_permission_patch_normalises_only_known_roles(self):
		patches = (EDUEDGE / "patches.txt").read_text()
		patch = (
			EDUEDGE
			/ "patches"
			/ "v0_8"
			/ "normalize_training_progress_permissions.py"
		).read_text()
		self.assertIn("normalize_training_progress_permissions", patches)
		self.assertIn("get_default_permission_matrix", patch)
		self.assertIn("LEGACY_NO_DEFAULT_RIGHTS", patch)
		self.assertIn("Custom roles are deliberately untouched", patch)
		self.assertIn("_set_exact_permission_row", patch)
		self.assertIn("_remove_known_legacy_row", patch)

	def test_access_manifest_uses_frappe_16_permission_signature(self):
		access = (EDUEDGE / "access_control.py").read_text()
		self.assertIn("frappe.has_permission(doctype, permission_type, user=user)", access)
		self.assertNotIn("print_logs=", access)
		ast.parse(access)


if __name__ == "__main__":
	unittest.main()
