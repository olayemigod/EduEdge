from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestClassArmRefactorContract(unittest.TestCase):
    def test_reusable_master_exists_and_is_branch_scoped(self):
        doctype = APP / "eduedge/doctype/eduedge_class_arm/eduedge_class_arm.json"
        self.assertTrue(doctype.exists())
        payload = json.loads(doctype.read_text(encoding="utf-8"))
        self.assertEqual(payload["autoname"], "hash")
        self.assertEqual(payload["title_field"], "class_arm_name")
        fields = {row["fieldname"]: row for row in payload["fields"]}
        for fieldname in ("class_arm_name", "class_arm_code", "school_branch", "institution", "program", "default_capacity", "enabled"):
            self.assertIn(fieldname, fields)
        self.assertEqual(fields["school_branch"]["options"], "EduEdge School Branch")
        self.assertEqual(fields["program"]["options"], "Program")

    def test_student_group_gets_identity_lineage_without_renaming_history(self):
        source = (APP / "education/class_arm_identity.py").read_text(encoding="utf-8")
        for token in ("eduedge_class_arm", "eduedge_display_name", "eduedge_previous_student_group", "backfill_class_arm_identities"):
            self.assertIn(token, source)
        self.assertIn('frappe.db.set_value("Student Group", row.name, updates, update_modified=False)', source)
        self.assertNotIn('frappe.rename_doc("Student Group"', source)

    def test_new_operational_group_uses_collision_safe_technical_identity(self):
        source = (APP / "api/class_arms.py").read_text(encoding="utf-8")
        identity = (APP / "education/class_arm_identity.py").read_text(encoding="utf-8")
        self.assertIn("generate_operational_group_name", source)
        self.assertIn("hashlib.sha1", identity)
        self.assertNotIn("doc.student_group_name = friendly_name", source)
        self.assertIn("CLASS_ARM_FIELD", source)
        self.assertIn("OFFERING_FIELD", source)

    def test_existing_session_context_is_server_immutable_and_legacy_history_is_protected(self):
        source = (APP / "api/class_arms.py").read_text(encoding="utf-8")
        identity = (APP / "education/class_arm_identity.py").read_text(encoding="utf-8")
        self.assertIn("An existing Class Arm cannot be moved to another Branch, Offering, or Academic Session", source)
        self.assertIn("Legacy term-bound Class Arms are historical", source)
        self.assertIn('"academic_term": None', source)
        self.assertIn("Academic context cannot be changed on an existing Class Arm session", identity)
        self.assertIn("Prepare the next Academic Session instead", identity)
        for fieldname in ("BRANCH_FIELD", "OFFERING_FIELD", '"program"', '"academic_year"', '"academic_term"', "CLASS_ARM_FIELD"):
            self.assertIn(fieldname, identity)

    def test_instructor_assignment_remains_authoritative(self):
        api = (APP / "api/class_arms.py").read_text(encoding="utf-8")
        ui = (APP / "public/js/eduedge_class_arms/EduEdgeClassArms.vue").read_text(encoding="utf-8")
        self.assertIn("Teaching responsibility is managed through Instructor Assignments", api)
        self.assertIn("if instructor_rows:", api)
        self.assertNotIn('instructors: JSON.stringify', ui)
        self.assertNotIn('doc.set("instructors", [])', api)
        self.assertNotIn('doc.append("instructors"', api)
        self.assertIn("openInstructorAssignments", ui)

    def test_session_rollover_is_post_only_later_session_and_enrollment_revalidated(self):
        api = (APP / "api/class_arms.py").read_text(encoding="utf-8")
        rollover = (APP / "api/class_arm_session_rollover.py").read_text(encoding="utf-8")
        ui = (APP / "public/js/eduedge_class_arms/EduEdgeClassArms.vue").read_text(encoding="utf-8")
        for endpoint in (
            "execute_selected_class_arm_session_rollover",
            "preview_single_class_arm_session_rollover",
            "execute_single_class_arm_session_rollover",
        ):
            self.assertIn(f"def {endpoint}", rollover)
        self.assertGreaterEqual(rollover.count('@frappe.whitelist(methods=["POST"])'), 3)
        self.assertIn("Select a later destination Academic Session", api)
        self.assertIn("Program Enrollment", api)
        self.assertIn('"docstatus": 1', api)
        self.assertIn("enrollment_filters[OFFERING_FIELD] = context.name", api)
        self.assertIn("PREVIOUS_GROUP_FIELD", api)
        self.assertIn("previous_student_group=source_doc.name", rollover)
        self.assertIn("Source Session records", ui)
        self.assertIn("historical assessments/results/CBT records will remain unchanged", ui)

    def test_branch_security_hooks_cover_class_arm_master(self):
        hooks = (APP / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('"EduEdge Class Arm": "eduedge.education.class_arm_permissions.class_arm_query"', hooks)
        self.assertIn('"EduEdge Class Arm": "eduedge.education.class_arm_permissions.has_class_arm_permission"', hooks)
        permissions = (APP / "education/class_arm_permissions.py").read_text(encoding="utf-8")
        self.assertIn("_branch_condition", permissions)
        self.assertIn("has_school_branch_permission", permissions)

    def test_install_and_migrate_are_idempotent_foundation_entrypoints(self):
        install = (APP / "install.py").read_text(encoding="utf-8")
        self.assertIn("ensure_class_arm_foundation", install)
        self.assertEqual(install.count("ensure_class_arm_foundation()"), 2)


if __name__ == "__main__":
    unittest.main()
