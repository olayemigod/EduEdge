from __future__ import annotations

import unittest

from eduedge.platform.config import (
	PlatformConfig,
	is_local_development,
	is_secure_remote_url,
	normalize_mode,
	parse_bool,
)


class TestPlatformConfig(unittest.TestCase):
	def test_unconfigured_hosted_site_requires_remote_coreedge(self):
		config = PlatformConfig.from_mapping({})
		self.assertEqual(config.mode, "remote")
		self.assertTrue(config.remote_enabled)
		self.assertTrue(config.required)
		self.assertTrue(config.fail_closed)
		self.assertFalse(config.readiness()["ready"])

	def test_local_development_defaults_to_explicit_standalone(self):
		for values in (
			{"developer_mode": 1},
			{"site_name": "eduedge.local"},
			{"host_name": "http://localhost:8000"},
		):
			with self.subTest(values=values):
				config = PlatformConfig.from_mapping(values)
				self.assertTrue(config.local_development)
				self.assertEqual(config.mode, "standalone")
				self.assertFalse(config.required)
				self.assertFalse(config.fail_closed)

	def test_legacy_and_invalid_modes_fail_towards_remote(self):
		self.assertEqual(normalize_mode("shared_hosted"), "remote")
		self.assertEqual(normalize_mode("white_label"), "remote")
		self.assertEqual(normalize_mode("unsupported"), "remote")
		self.assertEqual(normalize_mode(None, default="standalone"), "standalone")

	def test_local_development_detection_is_explicit(self):
		self.assertTrue(is_local_development({"site_name": "school.local"}))
		self.assertTrue(is_local_development({"developer_mode": True}))
		self.assertFalse(is_local_development({"site_name": "school.example.com"}))

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

	def test_explicit_production_standalone_is_visible_and_not_silently_required(self):
		config = PlatformConfig.from_mapping(
			{
				"site_name": "school.example.com",
				"edge_platform_mode": "standalone",
				"coreedge_required": False,
			}
		)
		self.assertEqual(config.mode, "standalone")
		self.assertIn("outside local development", " ".join(config.readiness()["warnings"]))

	def test_remote_transport_requires_https_outside_local_development(self):
		self.assertTrue(is_secure_remote_url("https://coreedge.processedge.com.ng"))
		self.assertTrue(is_secure_remote_url("http://localhost:8000"))
		self.assertTrue(is_secure_remote_url("http://coreedge.local:8000"))
		self.assertFalse(is_secure_remote_url("http://coreedge.example.com"))
		self.assertFalse(is_secure_remote_url("ftp://coreedge.example.com"))

		config = PlatformConfig.from_mapping(
			{
				"edge_platform_mode": "remote",
				"coreedge_base_url": "http://coreedge.example.com",
				"coreedge_tenant_key": "TENANT-1",
				"coreedge_site_identifier": "school.example.com",
				"coreedge_client_id": "client",
				"coreedge_client_secret": "secret",
			}
		)
		self.assertFalse(config.secure_transport)
		self.assertIn("must use HTTPS", " ".join(config.readiness()["blockers"]))


if __name__ == "__main__":
	unittest.main()
