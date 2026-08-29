from pathlib import Path
import ast
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSessionLaunchFinalReviewContract(unittest.TestCase):
    def test_activation_service_is_syntax_valid_and_has_explicit_roles(self):
        source = (APP / "api" / "session_launch_final_review.py").read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn("ACTIVATION_ROLES", source)
        self.assertIn('"Academic Administrator"', source)
        self.assertIn("_require_activation_permission", source)
        self.assertIn("frappe.PermissionError", source)

    def test_hard_blockers_cannot_be_overridden(self):
        source = (APP / "api" / "session_launch_final_review.py").read_text(encoding="utf-8")
        self.assertIn('if blocked:', source)
        self.assertIn('_("Session activation is blocked by: {0}.")', source)
        self.assertIn("frappe.ValidationError", source)
        self.assertNotIn("override_blocker", source)
        self.assertNotIn("force_activate", source)

    def test_warnings_require_audited_acknowledgement(self):
        source = (APP / "api" / "session_launch_final_review.py").read_text(encoding="utf-8")
        self.assertIn("MIN_WARNING_ACK_LENGTH", source)
        self.assertIn("if warnings and len(acknowledgement) < MIN_WARNING_ACK_LENGTH:", source)
        self.assertIn('"warning_acknowledgement": warning_acknowledgement', source)

    def test_activation_is_serialized_and_has_no_manual_commit(self):
        source = (APP / "api" / "session_launch_final_review.py").read_text(encoding="utf-8")
        self.assertIn("_lock_institution(doc.institution)", source)
        self.assertIn("for update", source.lower())
        self.assertNotIn("frappe.db.commit", source)
        self.assertNotIn("frappe.db.rollback", source)

    def test_activation_snapshot_is_canonical_and_hashed(self):
        source = (APP / "api" / "session_launch_final_review.py").read_text(encoding="utf-8")
        self.assertIn("json.dumps(snapshot, sort_keys=True", source)
        self.assertIn("hashlib.sha256", source)
        self.assertIn("doc.readiness_snapshot_hash = snapshot_hash", source)
        self.assertIn("doc.readiness_snapshot = snapshot_text", source)
        self.assertIn('"previous_active": previous or {}', source)

    def test_launch_doctype_contains_activation_audit_fields(self):
        path = APP / "eduedge" / "doctype" / "eduedge_academic_session_launch" / "eduedge_academic_session_launch.json"
        meta = json.loads(path.read_text(encoding="utf-8"))
        fields = {row["fieldname"]: row for row in meta["fields"] if row.get("fieldname")}
        for fieldname in (
            "ready_by",
            "ready_on",
            "activated_by",
            "activated_on",
            "previous_active_launch",
            "previous_active_academic_year",
            "warning_acknowledgement",
            "readiness_snapshot_hash",
            "readiness_snapshot",
        ):
            self.assertIn(fieldname, fields)
            self.assertEqual(fields[fieldname].get("read_only"), 1)

    def test_launch_manager_roles_have_read_only_doctype_access(self):
        path = APP / "eduedge" / "doctype" / "eduedge_academic_session_launch" / "eduedge_academic_session_launch.json"
        meta = json.loads(path.read_text(encoding="utf-8"))
        permissions = {row["role"]: row for row in meta.get("permissions", [])}
        for role in ("EduEdge Administrator", "School Administrator", "Academic Administrator", "Registrar"):
            self.assertEqual(permissions[role].get("read"), 1)
            self.assertFalse(permissions[role].get("create"))
            self.assertFalse(permissions[role].get("write"))
            self.assertFalse(permissions[role].get("delete"))

    def test_activation_snapshot_is_immutable_after_activation(self):
        source = (APP / "eduedge" / "doctype" / "eduedge_academic_session_launch" / "eduedge_academic_session_launch.py").read_text(encoding="utf-8")
        self.assertIn("IMMUTABLE_ACTIVATION_FIELDS", source)
        self.assertIn('previous.status not in {"Active", "Closed"}', source)
        self.assertIn("_protect_activation_snapshot", source)
        self.assertIn("activation snapshot is immutable", source)

    def test_final_review_panel_is_embedded_in_session_launch(self):
        launch = (APP / "public" / "js" / "eduedge_ui" / "components" / "EduEdgeSessionLaunchPanel.vue").read_text(encoding="utf-8")
        panel = (APP / "public" / "js" / "eduedge_ui" / "components" / "EduEdgeSessionFinalReviewPanel.vue").read_text(encoding="utf-8")
        self.assertIn('import EduEdgeSessionFinalReviewPanel from "./EduEdgeSessionFinalReviewPanel.vue";', launch)
        self.assertIn('"operational_readiness", "final_review"', launch)
        self.assertIn("activeStepKey === 'final_review'", launch)
        self.assertIn("@activated=\"handleActivated\"", launch)
        self.assertIn("Activate Session", panel)
        self.assertIn("Acknowledge & Activate", panel)
        self.assertIn("Hard blockers cannot be overridden", panel)


if __name__ == "__main__":
    unittest.main()
