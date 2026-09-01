import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestPhase6DRuntimeSchemaContract(unittest.TestCase):
    def test_program_offering_schema_uses_real_start_and_end_fields(self):
        metadata = json.loads(
            (APP / "eduedge" / "doctype" / "eduedge_program_offering" / "eduedge_program_offering.json").read_text(
                encoding="utf-8"
            )
        )
        fields = {row["fieldname"] for row in metadata["fields"]}
        self.assertIn("start_date", fields)
        self.assertIn("end_date", fields)
        self.assertNotIn("period_start_date", fields)
        self.assertNotIn("period_end_date", fields)

    def test_shared_offering_period_resolver_uses_explicit_dates_then_academic_fallback(self):
        source = (APP / "education" / "offerings.py").read_text(encoding="utf-8")
        for token in (
            "def academic_period_dates",
            "def resolve_program_offering_period_dates",
            '["start_date", "end_date", "academic_year", "academic_term"]',
            'getter("start_date") or fallback_start',
            'getter("end_date") or fallback_end',
        ):
            self.assertIn(token, source)

    def test_academic_readiness_does_not_query_nonexistent_offering_period_columns(self):
        source = (APP / "api" / "academic_readiness.py").read_text(encoding="utf-8")
        block = source[source.index("def _offering_rows"):source.index("def _group_rows")]
        self.assertIn('"academic_term", "start_date", "end_date", "is_active"', block)
        self.assertIn("resolve_program_offering_period_dates(value)", block)
        self.assertNotIn('"academic_term", "period_start_date", "period_end_date", "is_active"', block)
        self.assertNotIn('order_by="period_start_date', block)

    def test_scheme_controller_and_workbench_resolve_periods_without_fake_columns(self):
        controller = (
            APP / "eduedge" / "doctype" / "eduedge_scheme_of_work" / "eduedge_scheme_of_work.py"
        ).read_text(encoding="utf-8")
        controller_block = controller[
            controller.index("def _apply_academic_context"):controller.index("def _validate_student_group")
        ]
        self.assertIn('"start_date"', controller_block)
        self.assertIn('"end_date"', controller_block)
        self.assertIn("resolve_program_offering_period_dates(offering)", controller_block)
        self.assertNotIn('"period_start_date",', controller_block)
        self.assertNotIn('"period_end_date",', controller_block)

        workbench = (APP / "api" / "scheme_of_work_workbench.py").read_text(encoding="utf-8")
        workbench_block = workbench[workbench.index("def _offering_options"):workbench.index("def _group_options")]
        self.assertIn('"start_date", "end_date", "is_active"', workbench_block)
        self.assertIn("resolve_program_offering_period_dates(row)", workbench_block)
        self.assertNotIn('"period_start_date", "period_end_date"', workbench_block)

    def test_lesson_plan_offering_options_use_real_offering_fields(self):
        source = (APP / "api" / "lesson_plans.py").read_text(encoding="utf-8")
        block = source[source.index("def _offering_options"):source.index("def _group_options")]
        self.assertIn('"start_date"', block)
        self.assertIn('"end_date"', block)
        self.assertIn("resolve_program_offering_period_dates(row)", block)
        self.assertNotIn('"period_start_date",', block.split("result = []", 1)[0])
        self.assertNotIn('"period_end_date",', block.split("result = []", 1)[0])

    def test_assignment_register_accepts_dict_or_frappe_dict_rows(self):
        source = (APP / "api" / "instructor_assignment_register.py").read_text(encoding="utf-8")
        for token in (
            "def _row_value",
            "def _row_name",
            "allowed_names = [_row_name(row) for row in allowed",
            '"branches": {_row_name(row): row for row in allowed',
            "allowed_names = {_row_name(row) for row in allowed",
        ):
            self.assertIn(token, source)
        self.assertNotIn("allowed_names = [row.name for row in allowed]", source)
        self.assertNotIn("allowed_names = {row.name for row in allowed}", source)


if __name__ == "__main__":
    unittest.main()
