from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
API_PATH = ROOT / "eduedge" / "api" / "institution_operations_settings.py"


class TestInstitutionOperationsInheritanceDisplayContract(unittest.TestCase):
	def test_inherited_institution_uses_effective_company_values_for_display(self):
		content = API_PATH.read_text(encoding="utf-8")
		for expected in (
			"def _effective_institution_values",
			'values.get("use_company_question_governance_defaults")',
			'effective_policy["source"] = COMPANY_SCOPE',
			'"question_approval_mode": effective_policy.get("question_approval_mode")',
			'"max_bulk_question_approval": cint(',
			'"allow_academic_admin_override": cint(effective_policy.get("allow_academic_admin_override"))',
			"values = _effective_institution_values(values, effective_policy)",
		):
			self.assertIn(expected, content)

	def test_explicit_institution_preference_is_not_replaced(self):
		content = API_PATH.read_text(encoding="utf-8")
		self.assertIn(
			'if not cint(values.get("use_company_question_governance_defaults")) or not effective_policy:',
			content,
		)
		self.assertIn("return values", content)


if __name__ == "__main__":
	unittest.main()
