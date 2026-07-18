from __future__ import annotations

import unittest

from eduedge.platform.config import PlatformConfig, normalize_mode, parse_bool


class TestPlatformConfig(unittest.TestCase):
	def test_default_is_standalone(self):
		config = PlatformConfig.from_mapping({})
		self.assertEqual(config.mode, "standalone")
		self.assertFalse(config.remote_enabled)

	def test_legacy_modes_are_remote(self):
		self.assertEqual(normalize_mode("shared_hosted"), "remote")
		self.assertEqual(normalize_mode("white_label"), "remote")

	def test_boolean_parser(self):
		self.assertTrue(parse_bool("yes"))
		self.assertTrue(parse_bool(1))
		self.assertFalse(parse_bool("off", default=True))

	def test_sanitized_config_does_not_expose_secret(self):
		config = PlatformConfig.from_mapping(
			{
				"edge_platform_mode": "remote",
				"coreedge_client_secret": "do-not-expose",
			}
		)
		payload = config.sanitized()
		self.assertNotIn("client_secret", payload)
		self.assertNotIn("do-not-expose", str(payload))

	def test_required_remote_mode_reports_missing_configuration(self):
		config = PlatformConfig.from_mapping(
			{
				"edge_platform_mode": "remote",
				"coreedge_required": True,
			}
		)
		self.assertFalse(config.readiness()["ready"])
		self.assertGreaterEqual(len(config.readiness()["blockers"]), 3)


if __name__ == "__main__":
	unittest.main()
