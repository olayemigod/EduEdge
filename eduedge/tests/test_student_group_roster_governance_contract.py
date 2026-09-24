from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
QUERY = APP / "api" / "academic_group_context.py"
OPERATIONS = APP / "education" / "academic_operations.py"
FORM = APP / "public" / "js" / "education" / "student_group.js"
CLASS_ARMS_API = APP / "api" / "class_arms.py"
CLASS_ARMS_PAGE = APP / "public" / "js" / "eduedge_class_arms" / "EduEdgeClassArms.vue"


class TestStudentGroupRosterGovernanceContract(unittest.TestCase):
    def test_limited_instructor_roster_search_rehydrates_authoritative_group_context(self):
        source = QUERY.read_text(encoding="utf-8")
        for token in (
            "def _authoritative_roster_filters",
            "is_limited_instructor_user(frappe.session.user)",
            'filters.get("student_group")',
            'group_doc = frappe.get_doc("Student Group", group_name)',
            'group_doc.check_permission("write")',
            'requested_branch and requested_branch != branch',
            'assert_branch_access(branch)',
            'OFFERING_FIELD: group_doc.get(OFFERING_FIELD)',
            '"academic_year": group_doc.academic_year',
            '"academic_term": group_doc.academic_term',
            '"program": group_doc.program',
            '"batch": group_doc.batch',
            '"student_category": group_doc.student_category',
            '"course": group_doc.course',
        ):
            self.assertIn(token, source)

        query = source.split("def student_group_student_query", 1)[1]
        self.assertIn("filters = _authoritative_roster_filters(filters)", query)
        self.assertIn("limit %(start)s, %(page_len)s", query)

    def test_native_roster_query_sends_saved_group_identity(self):
        source = FORM.read_text(encoding="utf-8")
        self.assertIn('student_group: frm.is_new() ? "" : frm.doc.name', source)
        self.assertIn(
            'query: "eduedge.api.academic_group_context.student_group_student_query"',
            source,
        )

    def test_existing_student_group_academic_identity_is_server_side_immutable(self):
        source = OPERATIONS.read_text(encoding="utf-8")
        for token in (
            "STUDENT_GROUP_IDENTITY_FIELDS = (",
            "BRANCH_FIELD,",
            "OFFERING_FIELD,",
            '"eduedge_class_arm"',
            '"program"',
            '"academic_year"',
            '"academic_term"',
            '"batch"',
            '"group_based_on"',
            '"student_category"',
            '"course"',
            "def _validate_student_group_identity",
            "doc.get_doc_before_save()",
            "Existing Student Group academic context cannot be changed",
            "_validate_student_group_identity(doc)",
        ):
            self.assertIn(token, source)

        validate = source.split("def before_validate_student_group", 1)[1].split(
            "def _validate_student_group_identity",
            1,
        )[0]
        self.assertLess(
            validate.index('resolve_exact_offering(doc, purpose="enrollment")'),
            validate.index("_validate_student_group_identity(doc)"),
        )

    def test_native_form_locks_group_basis_category_and_course_on_existing_groups(self):
        source = FORM.read_text(encoding="utf-8")
        lock = source.split("function applyExistingPeriodLock", 1)[1].split(
            "frappe.ui.form.on", 1
        )[0]
        for fieldname in (
            '"group_based_on"',
            '"student_category"',
            '"course"',
        ):
            self.assertIn(fieldname, lock)

    def test_server_validates_roster_student_category_and_course_enrollment(self):
        source = OPERATIONS.read_text(encoding="utf-8")
        block = source.split("def _validate_student_group_enrollment", 1)[1].split(
            "def before_validate_room", 1
        )[0]
        for token in (
            'base_filters["student_category"] = doc.student_category',
            '"Program Enrollment"',
            'filters={**base_filters, OFFERING_FIELD: offering}',
            'fallback_filters["student_batch_name"] = doc.batch',
            '"Program Enrollment Course"',
            '"parent": ["in", enrollment_names]',
            '"course": doc.course',
            "is not enrolled in Course / Subject",
        ):
            self.assertIn(token, block)
        self.assertNotIn(
            'if frappe.db.exists("Program Enrollment", {**filters, OFFERING_FIELD: offering}):\n\t\t\treturn',
            block,
        )


    def test_edgesuite_class_arm_editor_cannot_retarget_existing_grouping_identity(self):
        api = CLASS_ARMS_API.read_text(encoding="utf-8")
        page = CLASS_ARMS_PAGE.read_text(encoding="utf-8")

        for token in (
            'if str(doc.group_based_on or "") != group_based_on or str(doc.course or "") != str(course or ""):',
            "Existing Class Arm grouping basis and Course / Subject cannot be changed.",
            "Create or carry forward a new session Class Arm for a different grouping structure.",
        ):
            self.assertIn(token, api)

        for token in (
            ':disabled="Boolean(draft.name) || draft.legacy_term_bound" @change="groupBasisChanged"',
            ':disabled="Boolean(draft.name) || draft.legacy_term_bound"><option value="">Select {{ courseSingular }}</option>',
            "Grouping basis and Course / Subject are fixed for an existing Academic Session Class Arm.",
        ):
            self.assertIn(token, page)


if __name__ == "__main__":
    unittest.main()
