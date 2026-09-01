import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSchemeOfWorkFoundationContract(unittest.TestCase):
    def test_master_and_child_doctypes_define_versioned_academic_context(self):
        master = json.loads((APP / "eduedge" / "doctype" / "eduedge_scheme_of_work" / "eduedge_scheme_of_work.json").read_text())
        child = json.loads((APP / "eduedge" / "doctype" / "eduedge_scheme_of_work_item" / "eduedge_scheme_of_work_item.json").read_text())
        fields = {row["fieldname"]: row for row in master["fields"]}
        for fieldname in (
            "school_branch", "program_offering", "student_group", "course", "academic_year", "academic_term",
            "period_start_date", "period_end_date", "version_no", "supersedes_scheme", "status", "items",
            "prepared_by", "approved_by", "approved_on", "snapshot_on", "offering_title_snapshot",
            "student_group_name_snapshot", "course_name_snapshot",
        ):
            self.assertIn(fieldname, fields)
        self.assertEqual(fields["items"]["options"], "EduEdge Scheme of Work Item")
        self.assertEqual(child.get("istable"), 1)
        child_fields = {row["fieldname"] for row in child["fields"]}
        for fieldname in (
            "sequence", "week_no", "topic", "topic_name_snapshot", "topic_description_snapshot",
            "learning_objective", "planned_start_date", "planned_end_date", "estimated_periods",
        ):
            self.assertIn(fieldname, child_fields)

    def test_controller_validates_exact_offering_group_course_topic_and_dates(self):
        source = (APP / "eduedge" / "doctype" / "eduedge_scheme_of_work" / "eduedge_scheme_of_work.py").read_text()
        for token in (
            "assert_branch_access(offering.school_branch)",
            "Program Course",
            "Course Topic",
            "TOPIC_SCOPE_CLASS",
            "TOPIC_SCOPE_CLASS_ARM",
            "Scheme item dates cannot precede the academic period",
            "Scheme item dates cannot extend beyond the academic period",
            "Scheme item Sequence values must be unique",
        ):
            self.assertIn(token, source)

    def test_approved_scheme_is_immutable_and_snapshotted(self):
        source = (APP / "eduedge" / "doctype" / "eduedge_scheme_of_work" / "eduedge_scheme_of_work.py").read_text()
        api = (APP / "api" / "scheme_of_work.py").read_text()
        self.assertIn("Approved Scheme of Work curriculum is immutable", source)
        self.assertIn("def snapshot_scheme_context", source)
        self.assertIn("topic_name_snapshot", source)
        self.assertIn("topic_description_snapshot", source)
        self.assertIn("def approve_scheme", api)
        self.assertIn('doc.status = "Approved"', api)
        self.assertIn("doc.snapshot_on = doc.approved_on", api)
        self.assertIn('previous.status = "Retired"', api)

    def test_instructor_authoring_uses_exact_assignment_period_and_capability_governance(self):
        api = (APP / "api" / "scheme_of_work.py").read_text()
        for token in (
            "get_active_instructor_names_for_user",
            "def _scheme_assignment_rows",
            "_date_overlap(row.valid_from, row.valid_to, doc.period_start_date, doc.period_end_date)",
            "def _write_reference_date",
            "def _effective_on",
            'capability = "can_manage_subject_topics" if write else "can_view_subject_content"',
            "assignment_capability_enforcement_enabled()",
            "does not cover this Scheme's Branch, Class, Class Arm and Subject context",
            "Your current or scheduled Instructor Assignment does not permit editing this Scheme of Work now",
            "Only academic management can approve a Scheme of Work",
        ):
            self.assertIn(token, api)

    def test_existing_draft_is_authorised_before_caller_context_is_applied(self):
        api = (APP / "api" / "scheme_of_work.py").read_text()
        block = api[api.index("def save_scheme"):api.index("def approve_scheme")]
        original_auth = block.index("_context_authorized(doc, write=True)")
        caller_mutation = block.index("for fieldname in EDITABLE_FIELDS")
        self.assertLess(original_auth, caller_mutation)
        self.assertIn("rewrite it into a context they are authorised to manage", block)

    def test_versioning_never_mutates_approved_content_in_place(self):
        api = (APP / "api" / "scheme_of_work.py").read_text()
        controller = (APP / "eduedge" / "doctype" / "eduedge_scheme_of_work" / "eduedge_scheme_of_work.py").read_text()
        self.assertIn("def create_next_version", api)
        self.assertIn("frappe.copy_doc(source)", api)
        self.assertIn("doc.version_no = cint(source.version_no) + 1", api)
        self.assertIn("doc.supersedes_scheme = source.name", api)
        self.assertIn("Approved or Retired Schemes of Work are retained as academic history", controller)


if __name__ == "__main__":
    unittest.main()
