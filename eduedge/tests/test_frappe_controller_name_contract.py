import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
DOCTYPE_ROOT = ROOT / "eduedge" / "eduedge" / "doctype"


class TestFrappeControllerNameContract(unittest.TestCase):
    def test_standard_doctype_controllers_expose_frappe_expected_class_name(self):
        """Frappe v16 expects DocType controller class == doctype without spaces/hyphens.

        This catches names such as "Scheme of Work" where Pythonic title-casing
        (SchemeOfWork) differs from Frappe's exact contract (SchemeofWork).
        """
        failures = []
        for json_path in sorted(DOCTYPE_ROOT.glob("*/*.json")):
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if data.get("doctype") != "DocType" or data.get("custom"):
                continue
            module_dir = json_path.parent
            controller = module_dir / f"{module_dir.name}.py"
            if not controller.exists():
                continue
            expected = str(data.get("name") or "").replace(" ", "").replace("-", "")
            if not expected:
                continue
            source = controller.read_text(encoding="utf-8")
            if not re.search(rf"^(?:class\s+{re.escape(expected)}\b|{re.escape(expected)}\s*=)", source, re.MULTILINE):
                failures.append(f"{data.get('name')}: expected controller symbol {expected} in {controller.relative_to(ROOT)}")
        self.assertFalse(failures, "\n".join(failures))

    def test_scheme_controller_symbols_match_frappe_v16_exact_names(self):
        parent = (DOCTYPE_ROOT / "eduedge_scheme_of_work" / "eduedge_scheme_of_work.py").read_text(encoding="utf-8")
        child = (DOCTYPE_ROOT / "eduedge_scheme_of_work_item" / "eduedge_scheme_of_work_item.py").read_text(encoding="utf-8")
        self.assertIn("class EduEdgeSchemeofWork(Document):", parent)
        self.assertIn("class EduEdgeSchemeofWorkItem(Document):", child)
        self.assertIn("EduEdgeSchemeOfWork = EduEdgeSchemeofWork", parent)
        self.assertIn("EduEdgeSchemeOfWorkItem = EduEdgeSchemeofWorkItem", child)


if __name__ == "__main__":
    unittest.main()
