from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestPlatformAccessGuardContract(unittest.TestCase):
	def test_guard_preserves_wrapped_signature_and_drops_frappe_cmd(self):
		access = (APP / "platform" / "access.py").read_text(encoding="utf-8")
		branch_api = (APP / "api" / "branch_context.py").read_text(encoding="utf-8")

		for expected in (
			"from functools import wraps",
			"@wraps(function)",
			'kwargs.pop("cmd", None)',
			"return function(*args, **kwargs)",
			'@guard_eduedge_action("school_branch", action="switch_school_branch")',
		):
			self.assertIn(expected, access + branch_api)

		self.assertNotIn("return function(*args, cmd=", access)

	def test_coreedge_cache_key_contains_record_identity(self):
		access = (APP / "platform" / "access.py").read_text(encoding="utf-8")
		for expected in (
			"reference_doctype: str | None = None",
			"reference_name: str | None = None",
			'"reference_doctype": reference_doctype or ""',
			'"reference_name": reference_name or ""',
			"reference_doctype=reference_doctype",
			"reference_name=reference_name",
		):
			self.assertIn(expected, access)
		self.assertGreaterEqual(access.count("reference_doctype=reference_doctype"), 4)
		self.assertGreaterEqual(access.count("reference_name=reference_name"), 4)


if __name__ == "__main__":
	unittest.main()
