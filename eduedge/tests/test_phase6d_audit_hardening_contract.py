from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestPhase6DAuditHardeningContract(unittest.TestCase):
    def test_lesson_plan_blocks_cross_instructor_takeover_before_context_resolution(self):
        source = (APP / "eduedge" / "doctype" / "eduedge_lesson_plan" / "eduedge_lesson_plan.py").read_text(encoding="utf-8")
        self.assertIn("def _validate_limited_instructor_identity", source)
        self.assertIn("You cannot modify another Instructor's Lesson Plan", source)
        validate = source[source.index("    def validate(self):"):source.index("    def _validate_status", source.index("    def validate(self):"))]
        self.assertLess(validate.index("self._validate_limited_instructor_identity()"), validate.index("self._resolve_scheme_context()"))

    def test_scheme_update_authorises_original_context_before_applying_payload(self):
        source = (APP / "api" / "scheme_of_work.py").read_text(encoding="utf-8")
        block = source[source.index("def save_scheme"):source.index("def approve_scheme")]
        original_auth = block.index("_context_authorized(doc, write=True)")
        mutation = block.index("for fieldname in EDITABLE_FIELDS")
        self.assertLess(original_auth, mutation)
        self.assertIn("_scheme_assignment_rows", source)
        self.assertIn("_date_overlap", source)
        self.assertIn("Your current or scheduled Instructor Assignment does not permit editing", source)

    def test_inactive_instructor_history_can_be_closed_only_through_governed_lifecycle(self):
        source = (APP / "eduedge" / "doctype" / "eduedge_instructor_assignment" / "eduedge_instructor_assignment.py").read_text(encoding="utf-8")
        self.assertIn("governed_closure = bool(", source)
        self.assertIn("self.ended_on and not before.ended_on", source)
        self.assertIn("self.replaced_by_assignment and not before.replaced_by_assignment", source)
        self.assertIn("self.transferred_to_assignment and not before.transferred_to_assignment", source)
        self.assertIn("if instructor.status != \"Active\" and not (governed_disable or governed_closure)", source)

    def test_primary_branch_profile_save_does_not_rewrite_historical_eligibility_dates(self):
        source = (APP / "api" / "instructor_profiles.py").read_text(encoding="utf-8")
        block = source[source.index("def _ensure_branch_eligibility"):source.index("@frappe.whitelist(methods=[\"POST\"])", source.index("def _ensure_branch_eligibility"))]
        self.assertIn("current_target", block)
        self.assertIn("_covers_date", block)
        self.assertIn("Historical and future", block)
        self.assertNotIn("doc.valid_from = doc.valid_from or", block)
        self.assertNotIn("doc.valid_to =", block.split("if current_target:", 1)[1].split("if not frappe.has_permission", 1)[0])

    def test_employee_options_are_home_institution_company_scoped_and_refresh_on_change(self):
        api = (APP / "api" / "instructor_profiles.py").read_text(encoding="utf-8")
        ui = (APP / "public" / "js" / "eduedge_instructors" / "EduEdgeInstructors.vue").read_text(encoding="utf-8")
        self.assertIn("def _employee_options", api)
        self.assertIn('filters={"status": "Active", "company": company}', api)
        self.assertNotIn('limit_page_length=1000', api)
        self.assertIn("this.data.employees = response.message?.employees || []", ui)
        self.assertIn("this.draft.employee = \"\"", ui)

    def test_teaching_evidence_is_private_owned_bounded_and_bound_to_append_only_log(self):
        api = (APP / "api" / "scheme_delivery.py").read_text(encoding="utf-8")
        ui = (APP / "public" / "js" / "eduedge_ui" / "components" / "SchemeDeliveryPanel.vue").read_text(encoding="utf-8")
        for token in (
            "def _validated_evidence_file",
            'file_url.startswith("/private/files/")',
            "row.owner != frappe.session.user",
            "row.attached_to_doctype or row.attached_to_name",
            "MAX_EVIDENCE_BYTES",
            "ALLOWED_EVIDENCE_EXTENSIONS",
            "def _bind_evidence_file",
            "file_doc.attached_to_doctype = LOG_DOCTYPE",
            'file_doc.attached_to_field = "evidence"',
        ):
            self.assertIn(token, api)
        self.assertIn("is_private: 1", ui)
        self.assertIn("row.instructor_name || row.instructor", ui)


if __name__ == "__main__":
    unittest.main()
