from pathlib import Path
import ast
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSessionLaunchOperationalReadinessContract(unittest.TestCase):
    def test_service_is_read_only_and_reuses_existing_session_sources(self):
        source = (APP / "api" / "session_launch_operational_readiness.py").read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn("get_structure_context", source)
        self.assertIn("get_learner_context", source)
        self.assertIn("get_delivery_context", source)
        self.assertIn("get_assessment_cbt_readiness", source)
        self.assertIn('"read_only": True', source)
        self.assertNotIn(".insert(", source)
        self.assertNotIn(".save(", source)
        self.assertNotIn("frappe.db.set_value", source)

    def test_status_contract_distinguishes_ready_attention_and_blocked(self):
        source = (APP / "api" / "session_launch_operational_readiness.py").read_text(encoding="utf-8")
        self.assertIn('STATUS_READY = "Ready"', source)
        self.assertIn('STATUS_ATTENTION = "Attention"', source)
        self.assertIn('STATUS_BLOCKED = "Blocked"', source)
        self.assertIn('"blockers": [row for row in categories if row["status"] == STATUS_BLOCKED]', source)
        self.assertIn('"warnings": [row for row in categories if row["status"] == STATUS_ATTENTION]', source)

    def test_partial_branch_scope_and_timetable_collisions_are_hard_blockers(self):
        source = (APP / "api" / "session_launch_operational_readiness.py").read_text(encoding="utf-8")
        self.assertIn('STATUS_READY if complete else STATUS_BLOCKED', source)
        self.assertIn("_assessment_conflict_rows", source)
        self.assertIn("buckets: dict[tuple[str, str, str], list[dict]] = defaultdict(list)", source)
        self.assertIn('blocked = bool(conflicts)', source)
        self.assertIn('"timetable_conflicts": len(conflicts)', source)
        self.assertNotIn("_find_overlap", source)

    def test_structure_uses_canonical_intended_class_count(self):
        source = (APP / "api" / "session_launch_operational_readiness.py").read_text(encoding="utf-8")
        self.assertIn('summary.get("intended_classes")', source)
        self.assertNotIn('summary.get("classes")', source)

    def test_optional_unplanned_cbt_does_not_block_session_launch(self):
        source = (APP / "api" / "session_launch_operational_readiness.py").read_text(encoding="utf-8")
        self.assertIn('if not state.get("planned"):', source)
        self.assertIn('_("No CBT sitting is planned for this Session. CBT is optional and does not block launch.")', source)
        self.assertIn('"status": "Not Planned"', source)

    def test_readiness_covers_current_academic_operational_sources_only(self):
        source = (APP / "api" / "session_launch_operational_readiness.py").read_text(encoding="utf-8")
        for category in (
            '"foundation"',
            '"branch_scope"',
            '"structure"',
            '"learners"',
            '"academic_delivery"',
            '"assessment"',
            '"cbt"',
            '"school_calendar"',
            '"attendance"',
        ):
            self.assertIn(category, source)
        for future_module in ("boarding", "pickup", "edgepay", "parent_portal"):
            self.assertNotIn(f'"{future_module}"', source.lower())

    def test_session_launch_embeds_operational_readiness_panel(self):
        source = (APP / "public" / "js" / "eduedge_ui" / "components" / "EduEdgeSessionLaunchPanel.vue").read_text(encoding="utf-8")
        panel = (APP / "public" / "js" / "eduedge_ui" / "components" / "EduEdgeSessionOperationalReadinessPanel.vue").read_text(encoding="utf-8")
        self.assertIn('import EduEdgeSessionOperationalReadinessPanel from "./EduEdgeSessionOperationalReadinessPanel.vue";', source)
        self.assertIn('"assessment_cbt", "operational_readiness"', source)
        self.assertIn("activeStepKey === 'operational_readiness'", source)
        self.assertIn("handleOperationalUpdated", source)
        self.assertIn("get_session_launch_operational_readiness", panel)
        self.assertIn("Save Operational Readiness here", panel)
        self.assertIn("Overall readiness", panel)

    def test_calendar_precedes_operational_readiness_and_final_review(self):
        source = (APP / "api" / "session_launch.py").read_text(encoding="utf-8")
        calendar = source.index('"key": "school_calendar"')
        operational = source.index('"key": "operational_readiness"')
        final_review = source.index('"key": "final_review"')
        self.assertLess(calendar, operational)
        self.assertLess(operational, final_review)


if __name__ == "__main__":
    unittest.main()
