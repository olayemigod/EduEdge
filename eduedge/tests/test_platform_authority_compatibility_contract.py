from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SECURITY = ROOT / "eduedge" / "security" / "__init__.py"


def test_super_administrator_uses_shared_platform_branch_authority():
	content = SECURITY.read_text()
	assert 'PRIVILEGED_ROLES.add("EduEdge Super Administrator")' in content
	assert "grants no DocType permission" in content


def test_legacy_hq_all_branch_setting_fails_closed():
	content = SECURITY.read_text()
	for expected in (
		"def safe_hq_all_branch_view_enabled",
		"if not meta.has_field(\"allow_hq_all_branch_view\")",
		"return False",
		"bool(cint(value or 0))",
		"branch_context.is_hq_all_branch_view_enabled = safe_hq_all_branch_view_enabled",
	):
		assert expected in content
