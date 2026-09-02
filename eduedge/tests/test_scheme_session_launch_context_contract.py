from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSchemeSessionLaunchContextContract(unittest.TestCase):
    def test_backend_filters_scheme_history_by_exact_academic_session(self):
        source = (APP / "api" / "scheme_of_work_session_context.py").read_text(encoding="utf-8")
        for token in (
            "def get_scheme_workbench(",
            '"academic_year": academic_year',
            'filters[fieldname] = value',
            '"academic_year": year',
            'offering_year != year',
            'scheme_api._context_authorized(doc, write=False)',
            'MAX_SCAN_ROWS = 1000',
            '"locked": True',
            '"source": "Academic Session Launch"',
        ):
            self.assertIn(token, source)

    def test_scheme_bundle_installs_session_context_runtime(self):
        bundle = (APP / "public" / "js" / "eduedge_scheme_of_work.bundle.js").read_text(encoding="utf-8")
        self.assertIn('import { installSchemeSessionContext } from "./eduedge_scheme_of_work/session_context"', bundle)
        self.assertIn("installSchemeSessionContext(EduEdgeSchemeOfWork)", bundle)

    def test_runtime_consumes_route_year_and_explains_approval_gate(self):
        source = (APP / "public" / "js" / "eduedge_scheme_of_work" / "session_context.js").read_text(encoding="utf-8")
        for token in (
            '"academic_year", "program_offering", "academic_term"',
            'const value = params.get(key)',
            'params.get("branch") || params.get("school_branch")',
            'academic_year: this.filters.academic_year || undefined',
            'eduedge.api.scheme_of_work_session_context.get_scheme_workbench',
            'data-eduedge-session-context',
            'Academic Session',
            'Approval requires at least one Scheme Item',
            'await this.save()',
            'await this.runAction("eduedge.api.scheme_of_work.approve_scheme"',
        ):
            self.assertIn(token, source)

    def test_backend_approval_still_requires_real_scheme_items(self):
        source = (APP / "api" / "scheme_of_work.py").read_text(encoding="utf-8")
        self.assertIn('if not doc.get("items"):', source)
        self.assertIn('Add at least one Scheme item before approval.', source)


if __name__ == "__main__":
    unittest.main()
