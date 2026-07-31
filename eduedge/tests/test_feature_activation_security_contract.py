from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


def test_feature_gate_blocks_direct_cbt_rpc_and_exposes_scheduler_wrapper():
	gate = (APP / "security" / "feature_gate.py").read_text()
	request = (APP / "security" / "request_method.py").read_text()
	hooks = (APP / "hooks.py").read_text()

	for expected in (
		"FEATURE_SETTINGS",
		"FEATURE_COMMAND_PREFIXES",
		"FEATURE_ROUTE_PREFIXES",
		"def is_feature_enabled",
		"def require_feature",
		"def enforce_feature_for_command",
		"def run_cbt_expiry_job",
		'if not is_feature_enabled("cbt")',
	):
		assert expected in gate

	assert "from eduedge.security.feature_gate import enforce_feature_for_command" in request
	assert 'if command.startswith("eduedge.")' in request
	assert "enforce_feature_for_command(command)" in request
	assert '"eduedge.security.feature_gate.run_cbt_expiry_job"' in hooks
	assert '"eduedge.cbt.attempts.finalize_expired_attempts"' not in hooks


def test_access_manifest_hides_disabled_feature_routes():
	access = (APP / "access_control.py").read_text()
	for expected in (
		"from eduedge.security.feature_gate import feature_for_route, is_feature_enabled",
		'"cbt": is_feature_enabled("cbt")',
		"feature = feature_for_route(route)",
		"routes[route] = False",
		'"features": features',
	):
		assert expected in access
