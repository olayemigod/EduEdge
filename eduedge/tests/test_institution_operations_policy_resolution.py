from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "eduedge" / "education" / "operations_policy.py"


class _Row(dict):
	def __getattr__(self, key):
		return self.get(key)


class _FakeMeta:
	def __init__(self, fields):
		self.fields = set(fields)

	def has_field(self, fieldname):
		return fieldname in self.fields


class _FakeDB:
	def __init__(self):
		self.companies = {}
		self.institutions = {}
		self.company_settings = {}

	def exists(self, doctype, filters=None):
		if doctype == "Company":
			return filters in self.companies
		if doctype == "DocType":
			return filters == "EduEdge Company Operations Settings"
		if doctype == "EduEdge Institution":
			return filters in self.institutions
		return False

	def get_value(self, doctype, filters, fields=None, as_dict=False):
		if doctype == "Company":
			row = self.companies.get(filters, {})
			return row.get(fields)
		if doctype == "EduEdge Institution":
			row = self.institutions.get(filters)
			return self._project(row, fields, as_dict)
		if doctype == "EduEdge Company Operations Settings":
			if isinstance(filters, dict):
				company = filters.get("company")
				return company if company in self.company_settings else None
			row = self.company_settings.get(filters)
			return self._project(row, fields, as_dict)
		return None

	@staticmethod
	def _project(row, fields, as_dict):
		if not row:
			return None
		if isinstance(fields, (list, tuple)):
			values = _Row({field: row.get(field) for field in fields})
			return values if as_dict else tuple(values[field] for field in fields)
		return row.get(fields)


class TestInstitutionOperationsPolicyResolution(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.original_modules = {
			name: sys.modules.get(name)
			for name in (
				"frappe",
				"frappe.utils",
				"eduedge.education.institution_types",
			)
		}
		cls.db = _FakeDB()
		frappe = types.ModuleType("frappe")
		frappe.db = cls.db
		frappe._ = lambda value: value
		frappe.ValidationError = ValueError
		frappe.throw = lambda message, exc=ValueError: (_ for _ in ()).throw(exc(message))
		frappe.get_meta = lambda doctype: _FakeMeta({"eduedge_institution_type"})

		utils = types.ModuleType("frappe.utils")
		utils.cint = lambda value: int(value or 0)
		frappe.utils = utils

		institution_types = types.ModuleType("eduedge.education.institution_types")
		institution_types.DEFAULT_INSTITUTION_TYPE = "SECONDARY"
		institution_types.normalize_institution_type_code = (
			lambda value: str(value or "").strip().upper().replace(" ", "_")
		)

		sys.modules["frappe"] = frappe
		sys.modules["frappe.utils"] = utils
		sys.modules["eduedge.education.institution_types"] = institution_types
		spec = importlib.util.spec_from_file_location("eduedge_test_operations_policy", POLICY_PATH)
		cls.policy = importlib.util.module_from_spec(spec)
		assert spec and spec.loader
		spec.loader.exec_module(cls.policy)

	@classmethod
	def tearDownClass(cls):
		for name, module in cls.original_modules.items():
			if module is None:
				sys.modules.pop(name, None)
			else:
				sys.modules[name] = module

	def setUp(self):
		self.db.companies.clear()
		self.db.institutions.clear()
		self.db.company_settings.clear()

	def test_recommended_modes_follow_all_four_institution_types(self):
		expected = {
			"PRIMARY": "Simple",
			"SECONDARY": "Standard",
			"TERTIARY": "Standard",
			"TRAINING_CENTRE": "Simple",
		}
		for institution_type, mode in expected.items():
			with self.subTest(institution_type=institution_type):
				resolved = self.policy.recommended_question_governance(institution_type)
				self.assertEqual(resolved["question_approval_mode"], mode)
				self.assertEqual(resolved["max_bulk_question_approval"], 100)

	def test_company_without_saved_settings_uses_recommended_default(self):
		self.db.companies["Primary Company"] = {"eduedge_institution_type": "PRIMARY"}
		resolved = self.policy.resolve_company_question_governance("Primary Company")
		self.assertEqual(resolved["source"], "Recommended Default")
		self.assertEqual(resolved["question_approval_mode"], "Simple")
		self.assertEqual(resolved["approval_steps"], 1)

	def test_inherited_company_recommended_mode_uses_each_institution_type(self):
		self.db.companies["Mixed School"] = {"eduedge_institution_type": "SECONDARY"}
		self.db.company_settings["Mixed School"] = {
			"question_approval_mode": "Recommended",
			"allow_bulk_question_approval": 1,
			"max_bulk_question_approval": 40,
			"require_separate_question_approver": 1,
			"allow_academic_admin_override": 0,
		}
		self.db.institutions["PRIMARY-A"] = {
			"name": "PRIMARY-A",
			"company": "Mixed School",
			"institution_type": "PRIMARY",
			"use_company_question_governance_defaults": 1,
		}
		resolved = self.policy.resolve_question_governance("PRIMARY-A")
		self.assertEqual(resolved["source"], "Company Default")
		self.assertTrue(resolved["inherits_company"])
		self.assertEqual(resolved["question_approval_mode"], "Simple")
		self.assertEqual(resolved["max_bulk_question_approval"], 40)
		self.assertFalse(resolved["allow_academic_admin_override"])

	def test_institution_preference_overrides_company_values(self):
		self.db.companies["EduEdge Schools"] = {"eduedge_institution_type": "SECONDARY"}
		self.db.company_settings["EduEdge Schools"] = {
			"question_approval_mode": "Standard",
			"allow_bulk_question_approval": 1,
			"max_bulk_question_approval": 75,
			"require_separate_question_approver": 1,
			"allow_academic_admin_override": 1,
		}
		self.db.institutions["SECONDARY-B"] = {
			"name": "SECONDARY-B",
			"company": "EduEdge Schools",
			"institution_type": "SECONDARY",
			"use_company_question_governance_defaults": 0,
			"question_approval_mode": "Simple",
			"allow_bulk_question_approval": 0,
			"max_bulk_question_approval": 12,
			"require_separate_question_approver": 0,
			"allow_academic_admin_override": 0,
		}
		resolved = self.policy.resolve_question_governance("SECONDARY-B")
		self.assertEqual(resolved["source"], "Institution Preference")
		self.assertFalse(resolved["inherits_company"])
		self.assertEqual(resolved["question_approval_mode"], "Simple")
		self.assertEqual(resolved["approval_steps"], 1)
		self.assertFalse(resolved["allow_bulk_question_approval"])
		self.assertEqual(resolved["max_bulk_question_approval"], 12)
		self.assertFalse(resolved["require_separate_question_approver"])

	def test_resolver_clamps_bulk_limit_to_supported_range(self):
		self.db.companies["Training Company"] = {"eduedge_institution_type": "TRAINING_CENTRE"}
		self.db.company_settings["Training Company"] = {
			"question_approval_mode": "Simple",
			"allow_bulk_question_approval": 1,
			"max_bulk_question_approval": 999,
			"require_separate_question_approver": 1,
			"allow_academic_admin_override": 1,
		}
		resolved = self.policy.resolve_company_question_governance("Training Company")
		self.assertEqual(resolved["max_bulk_question_approval"], 100)


if __name__ == "__main__":
	unittest.main()
