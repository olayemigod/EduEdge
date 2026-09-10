from __future__ import annotations

import json
from pathlib import Path
import unittest


APP = Path(__file__).resolve().parents[1]
DOCTYPE = APP / "eduedge" / "doctype" / "eduedge_user_branch_access"


class TestInstitutionScopedUserAccessContract(unittest.TestCase):
	def test_access_assignment_supports_company_institution_and_branch(self):
		meta = json.loads((DOCTYPE / "eduedge_user_branch_access.json").read_text())
		fields = {field["fieldname"]: field for field in meta["fields"]}
		self.assertEqual(fields["access_scope"]["options"], "Company\nInstitution\nBranch")
		self.assertEqual(fields["institution"]["options"], "EduEdge Institution")
		self.assertTrue(fields["hq_all_branch_access"].get("hidden"))
		self.assertIn("access_scope", meta["field_order"])
		self.assertIn("institution", meta["field_order"])

	def test_controller_derives_and_validates_the_scope_hierarchy(self):
		controller = (DOCTYPE / "eduedge_user_branch_access.py").read_text()
		for token in (
			"ASSIGNMENT_SCOPE_COMPANY",
			"ASSIGNMENT_SCOPE_INSTITUTION",
			"ASSIGNMENT_SCOPE_BRANCH",
			'self.company = frappe.db.get_value("EduEdge Institution", self.institution, "company")',
			'["branch_name", "company", "institution"]',
			'"access_scope": self.access_scope',
			'filters["institution"] = self.institution',
			'filters["school_branch"] = self.school_branch',
		):
			self.assertIn(token, controller)

	def test_central_resolver_expands_institution_assignments_to_all_branches(self):
		context = (APP / "services" / "branch_context.py").read_text()
		for token in (
			"def get_allowed_institutions",
			"def get_allowed_school_branches",
			'row.access_scope == ASSIGNMENT_SCOPE_INSTITUTION',
			'or_filters.append(["institution", "in", sorted(institution_scopes)])',
			"ACTIVE_SCOPE_INSTITUTION",
			"USER_INSTITUTION_KEY",
			'"all_branch_institutions": institution_scopes',
			'"institution_name"',
		):
			self.assertIn(token, context)

	def test_institution_and_academic_permissions_use_direct_institution_resolution(self):
		institution_permissions = (APP / "education" / "institution_permissions.py").read_text()
		academic_permissions = (APP / "education" / "academic_permissions.py").read_text()
		self.assertIn("get_allowed_institutions", institution_permissions)
		self.assertIn("return doc.name in allowed", institution_permissions)
		self.assertNotIn("_has_company_structure_scope", institution_permissions)
		self.assertIn("get_allowed_institutions", academic_permissions)
		self.assertNotIn("get_allowed_school_branches", academic_permissions)

	def test_native_and_quick_editor_forms_are_cascading_and_context_aware(self):
		script = (DOCTYPE / "eduedge_user_branch_access.js").read_text()
		modal = (APP / "api" / "modal_records.py").read_text()
		education = (APP / "api" / "education.py").read_text()
		for token in (
			'frm.set_query("institution"',
			'institution: frm.doc.institution',
			'frm.toggle_reqd("institution", ["Institution", "Branch"].includes(scope))',
			'frm.toggle_reqd("school_branch", scope === "Branch")',
		):
			self.assertIn(token, script)
		for token in (
			'"access_scope"',
			'"Access Level"',
			'"Institution", "Branch"',
			"get_allowed_institutions(company=company)",
			"get_allowed_school_branches(company=company, institution=institution)",
		):
			self.assertIn(token, modal)
		self.assertIn('institution=filters.get("institution")', education)

	def test_branch_governance_reports_all_three_coverage_levels(self):
		service = (APP / "services" / "branch_governance.py").read_text()
		for token in (
			'"covered_by_company"',
			'"covered_by_institution"',
			"ASSIGNMENT_SCOPE_BRANCH",
			"ASSIGNMENT_SCOPE_INSTITUTION",
			"ASSIGNMENT_SCOPE_COMPANY",
			'"scope_label"',
			'"Institution Disabled"',
		):
			self.assertIn(token, service)

	def test_migration_is_idempotent_and_does_not_widen_existing_branch_assignments(self):
		patch = (APP / "patches" / "v0_8" / "backfill_user_access_scope.py").read_text()
		patches = (APP / "patches.txt").read_text()
		self.assertIn('if row.hq_all_branch_access:', patch)
		self.assertIn('scope = "Company"', patch)
		self.assertIn('scope = "Branch"', patch)
		self.assertIn('["company", "institution"]', patch)
		self.assertIn("update_modified=False", patch)
		self.assertIn("eduedge.patches.v0_8.backfill_user_access_scope", patches)


if __name__ == "__main__":
	unittest.main()
