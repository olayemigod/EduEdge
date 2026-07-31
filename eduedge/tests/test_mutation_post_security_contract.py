from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
MUTATION_PREFIXES = (
	"save_",
	"create_",
	"update_",
	"delete_",
	"submit_",
	"cancel_",
	"approve_",
	"reject_",
	"publish_",
	"unpublish_",
	"switch_",
	"clear_",
	"perform_",
	"resolve_",
	"prepare_",
	"assign_",
	"import_",
	"upload_",
	"set_",
	"mark_",
	"record_",
	"finalize_",
	"sync_",
)


def _is_whitelist(decorator: ast.expr) -> bool:
	call = decorator if isinstance(decorator, ast.Call) else None
	value = call.func if call else decorator
	return (
		isinstance(value, ast.Attribute)
		and value.attr == "whitelist"
		and isinstance(value.value, ast.Name)
		and value.value.id == "frappe"
	)


def _is_post_only(decorator: ast.expr) -> bool:
	if not isinstance(decorator, ast.Call) or not _is_whitelist(decorator):
		return False
	for keyword in decorator.keywords:
		if keyword.arg != "methods":
			continue
		if isinstance(keyword.value, (ast.List, ast.Tuple)):
			values = {
				item.value.upper()
				for item in keyword.value.elts
				if isinstance(item, ast.Constant) and isinstance(item.value, str)
			}
			return values == {"POST"}
	return False


class TestMutationPostSecurityContract(unittest.TestCase):
	def test_all_whitelisted_mutations_are_post_only(self):
		violations: list[str] = []
		for path in sorted(APP.rglob("*.py")):
			if "/tests/" in path.as_posix():
				continue
			try:
				tree = ast.parse(path.read_text(encoding="utf-8"))
			except SyntaxError:
				continue
			for node in ast.walk(tree):
				if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
					continue
				whitelist_decorators = [decorator for decorator in node.decorator_list if _is_whitelist(decorator)]
				if not whitelist_decorators or not node.name.startswith(MUTATION_PREFIXES):
					continue
				if not any(_is_post_only(decorator) for decorator in whitelist_decorators):
					violations.append(f"{path.relative_to(ROOT)}:{node.lineno}:{node.name}")
		self.assertEqual([], violations, "Mutation endpoints must use @frappe.whitelist(methods=['POST']):\n" + "\n".join(violations))


if __name__ == "__main__":
	unittest.main()
