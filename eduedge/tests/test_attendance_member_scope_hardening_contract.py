from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
API = APP / "api" / "academic_operations.py"
FORM = APP / "public" / "js" / "education" / "student_attendance.js"
HOOKS = APP / "hooks.py"
SAFE = APP / "api" / "academic_operations_safe.py"
REVIEW = APP / "api" / "academic_operations_review.py"
INTEGRATION = APP / "api" / "integration_qa_hardening.py"


class TestAttendanceMemberScopeHardeningContract(unittest.TestCase):
    def test_student_group_member_lookup_requires_record_read_permission(self):
        source = API.read_text(encoding="utf-8")
        block = source.split("def student_group_member_query", 1)[1].split(
            "@frappe.whitelist()\n@frappe.validate_and_sanitize_search_inputs\ndef instructor_query",
            1,
        )[0]

        for token in (
            'group_doc = frappe.get_doc("Student Group", student_group)',
            'group_doc.check_permission("read")',
            "branch = group_doc.get(BRANCH_FIELD)",
            "assert_branch_access(branch)",
            "from `tabStudent Group Student` group_student",
        ):
            self.assertIn(token, block)

        self.assertLess(
            block.index('group_doc.check_permission("read")'),
            block.index("return frappe.db.sql("),
        )
        self.assertNotIn(
            'frappe.db.get_value("Student Group", student_group, BRANCH_FIELD)',
            block,
        )

    def test_native_attendance_student_picker_uses_hardened_member_query(self):
        source = FORM.read_text(encoding="utf-8")
        self.assertIn(
            "eduedge.api.academic_operations.student_group_member_query",
            source,
        )
        self.assertIn("student_group: frm.doc.student_group", source)


    def test_native_attendance_course_schedule_picker_is_permission_aware_and_bounded(self):
        review = REVIEW.read_text(encoding="utf-8")
        block = review.split("def student_attendance_course_schedule_query", 1)[1].split(
            "@frappe.whitelist()\n@frappe.validate_and_sanitize_search_inputs\ndef student_group_query",
            1,
        )[0]

        for token in (
            "safe._require_operations_read()",
            'group_doc = frappe.get_doc("Student Group", student_group)',
            'branch = safe.base._resolve_branch(branch or group_branch or None)',
            'query_filters[BRANCH_FIELD] = branch',
            'group_doc.check_permission("read")',
            'query_filters["student_group"] = student_group',
            'query_filters["schedule_date"] = str(getdate(reference_date))',
            'rows = frappe.get_list(',
            '"Course Schedule"',
            'fields=["name", "schedule_date", "from_time", "course", "student_group"]',
            "start=int(start)",
            "page_length=int(page_len)",
        ):
            self.assertIn(token, block)
        self.assertNotIn('frappe.get_all(', block)

        form = FORM.read_text(encoding="utf-8")
        for token in (
            "eduedge.api.academic_operations_review.student_attendance_course_schedule_query",
            "eduedge_school_branch: frm.doc.eduedge_school_branch",
            "student_group: frm.doc.student_group",
            "reference_date: frm.doc.date",
            "async function applyAttendanceScheduleContext(frm)",
            "student_group: nextGroup",
            "date: message.schedule_date || null",
            "eduedge_school_branch: message.eduedge_school_branch || null",
            "if (groupChanged) await frm.set_value('student', null)",
            "async function clearInvalidAttendanceSchedule(frm, fieldname)",
            "if (invalid) await frm.set_value('course_schedule', null)",
        ):
            self.assertIn(token, form)


    def test_legacy_attendance_tool_is_routed_through_safe_register_engine(self):
        hooks = HOOKS.read_text(encoding="utf-8")
        source = (APP / "api" / "attendance_tool_safe.py").read_text(encoding="utf-8")

        self.assertIn(
            '"education.education.doctype.student_attendance_tool.student_attendance_tool.get_student_attendance_records": "eduedge.api.attendance_tool_safe.get_student_attendance_records"',
            hooks,
        )
        self.assertIn(
            '"education.education.api.mark_attendance": "eduedge.api.attendance_tool_safe.mark_attendance"',
            hooks,
        )
        for token in (
            "safe._get_schedule_row(course_schedule)",
            "safe.get_attendance_register(",
            '"disabled": bool(row.get("locked"))',
            "safe.save_attendance_register(",
            "submit=1",
            '{"student": row.get("student"), "status": "Present"}',
            '{"student": row.get("student"), "status": "Absent"}',
        ):
            self.assertIn(token, source)
        for forbidden in (
            'frappe.get_all("Student Group Student"',
            'frappe.db.get_value("Course Schedule"',
            "frappe.qb.from_",
            'frappe.new_doc("Student Attendance")',
            ".submit()",
        ):
            self.assertNotIn(forbidden, source)


    def test_native_attendance_hook_revalidates_exact_schedule_ownership(self):
        source = (APP / "education" / "academic_operations.py").read_text(encoding="utf-8")
        hook = source.split("def before_validate_student_attendance", 1)[1].split(
            "def _validate_limited_instructor_attendance_schedule", 1
        )[0]
        guard = source.split("def _validate_limited_instructor_attendance_schedule", 1)[1].split(
            "def _resolve_exact_attendance_schedule", 1
        )[0]

        self.assertIn("_validate_limited_instructor_attendance_schedule(schedule)", hook)
        for token in (
            "is_limited_instructor_user(frappe.session.user)",
            "Limited Instructor attendance must be anchored to an exact Course Schedule.",
            'schedule_doc = frappe.get_doc("Course Schedule", schedule.name)',
            'schedule_doc.check_permission("read")',
        ):
            self.assertIn(token, guard)


    def test_attendance_register_requires_student_group_and_schedule_read_scope(self):
        source = API.read_text(encoding="utf-8")
        block = source.split("def get_attendance_register", 1)[1].split(
            "@frappe.whitelist()\n@guard_eduedge_action",
            1,
        )[0]

        for token in (
            'group = frappe.get_doc("Student Group", student_group)',
            'group.check_permission("read")',
            'is_limited_instructor_user(frappe.session.user)',
            "Limited Instructor attendance must be anchored to an exact Course Schedule.",
            'schedule_doc = frappe.get_doc("Course Schedule", course_schedule)',
            'schedule_doc.check_permission("read")',
        ):
            self.assertIn(token, block)

        self.assertNotIn(
            'frappe.db.get_value(\n\t\t"Student Group"',
            block,
        )
        self.assertNotIn(
            'frappe.db.get_value(\n\t\t\t"Course Schedule"',
            block,
        )

    def test_save_register_reuses_hardened_register_authorization(self):
        source = API.read_text(encoding="utf-8")
        block = source.split("def save_attendance_register", 1)[1].split(
            "@frappe.whitelist()\n@frappe.validate_and_sanitize_search_inputs\ndef student_group_query",
            1,
        )[0]
        self.assertIn(
            "register = get_attendance_register(student_group, date, course_schedule)",
            block,
        )


    def test_attendance_summary_uses_permission_aware_list_query(self):
        source = API.read_text(encoding="utf-8")
        block = source.split("def _get_attendance_summary", 1)[1].split(
            "@frappe.whitelist()\ndef get_attendance_register",
            1,
        )[0]
        self.assertIn('rows = frappe.get_list(', block)
        self.assertIn('"Student Attendance"', block)
        self.assertIn("limit_page_length=0", block)
        self.assertNotIn("frappe.get_all(", block)

    def test_register_write_does_not_ignore_doctype_permissions(self):
        source = API.read_text(encoding="utf-8")
        block = source.split("def save_attendance_register", 1)[1].split(
            "@frappe.whitelist()\n@frappe.validate_and_sanitize_search_inputs\ndef student_group_query",
            1,
        )[0]
        self.assertIn("doc.save()", block)
        self.assertIn("doc.submit()", block)
        self.assertNotIn("ignore_permissions", block)


    def test_edgesuite_attendance_ignores_stale_context_and_register_responses(self):
        source = (APP / "public" / "js" / "eduedge_attendance" / "EduEdgeAttendance.vue").read_text(encoding="utf-8")

        for token in (
            "contextRequestId: 0",
            "registerRequestId: 0",
            "branchSwitching: false",
            "const requestId = ++this.contextRequestId",
            "if (requestId !== this.contextRequestId) return",
            "if (requestId === this.contextRequestId) this.loading = false",
            "invalidateRegister()",
            "this.registerRequestId += 1",
            "const requestId = ++this.registerRequestId",
            "this.filters.student_group !== requestedGroup",
            "this.filters.date !== requestedDate",
            "this.filters.course_schedule !== requestedSchedule",
            "if (requestId === this.registerRequestId) this.registerLoading = false",
            ':disabled="loading || branchSwitching || saving"',
            "if (this.saving || !this.filters.branch || this.branchSwitching) return",
            "const previousBranch = this.context.filters?.branch",
            "this.filters.branch = previousBranch",
        ):
            self.assertIn(token, source)

        date_handler = source.split("async dateChanged()", 1)[1].split(
            "async scheduleChanged()", 1
        )[0]
        self.assertIn("this.invalidateRegister()", date_handler)

        schedule_handler = source.split("async scheduleChanged()", 1)[1].split(
            "async loadRegister()", 1
        )[0]
        self.assertIn("else this.invalidateRegister()", schedule_handler)


    def test_attendance_save_is_context_bound_and_controls_are_locked(self):
        source = (APP / "public" / "js" / "eduedge_attendance" / "EduEdgeAttendance.vue").read_text(encoding="utf-8")

        for token in (
            "saveRequestId: 0",
            "if (this.saving || !this.canManageAttendance",
            "const requestId = ++this.saveRequestId",
            "const requestedGroup = this.filters.student_group",
            "const requestedDate = this.register.date || this.filters.date",
            "const requestedSchedule = this.filters.course_schedule",
            "const entries = this.register.students.map",
            "student_group: requestedGroup",
            "date: requestedDate",
            "course_schedule: requestedSchedule",
            "if (requestId !== this.saveRequestId) return",
            "this.filters.student_group !== requestedGroup",
            "this.filters.date !== requestedDate",
            "this.filters.course_schedule !== requestedSchedule",
            "if (requestId === this.saveRequestId) this.saving = false",
            ':disabled="loading || branchSwitching || saving"',
            ':disabled="registerLoading || saving"',
            'if (this.saving) return',
            ':disabled="saving" @click="openRoute',
            ':disabled="saving" @click="activeTab = tab.key"',
        ):
            self.assertIn(token, source)

        save_block = source.split("async saveRegister(submit)", 1)[1].split(
            "async openCoverage(row)", 1
        )[0]
        self.assertIn("await this.loadRegister()", save_block)
        self.assertIn("await this.loadContext()", save_block)


    def test_live_attendance_routes_use_safe_runtime_overrides(self):
        hooks = HOOKS.read_text(encoding="utf-8")
        for token in (
            '"eduedge.api.academic_operations.get_operations_context": "eduedge.api.integration_qa_hardening.get_operations_context"',
            '"eduedge.api.academic_operations.get_attendance_register": "eduedge.api.academic_operations_safe.get_attendance_register"',
            '"eduedge.api.academic_operations.save_attendance_register": "eduedge.api.academic_operations_safe.save_attendance_register"',
        ):
            self.assertIn(token, hooks)

        review = REVIEW.read_text(encoding="utf-8")
        integration = INTEGRATION.read_text(encoding="utf-8")
        self.assertIn(
            "payload = safe.get_operations_context(branch=branch, date=date, student_group=student_group)",
            review,
        )
        self.assertIn(
            "payload = academic_operations_review.get_operations_context(",
            integration,
        )

    def test_safe_runtime_register_revalidates_group_and_schedule_permissions(self):
        source = SAFE.read_text(encoding="utf-8")
        register = source.split("def get_attendance_register", 1)[1].split(
            "@frappe.whitelist()\n@guard_eduedge_action",
            1,
        )[0]
        resolver = source.split("def _resolve_register_schedule", 1)[1].split(
            "@frappe.whitelist()\ndef get_attendance_register",
            1,
        )[0]
        schedule = source.split("def _get_schedule_row", 1)[1].split(
            "def _resolve_register_schedule",
            1,
        )[0]

        for token in (
            'group_doc = frappe.get_doc("Student Group", student_group)',
            'group_doc.check_permission("read")',
            "base.assert_branch_access(branch)",
        ):
            self.assertIn(token, register)

        for token in (
            'doc = frappe.get_doc("Course Schedule", course_schedule)',
            'doc.check_permission("read")',
        ):
            self.assertIn(token, schedule)

        for token in (
            "limited_instructor = is_limited_instructor_user()",
            'filters["instructor"] = resolve_exact_instructor_for_user(required=True)',
            'frappe.get_list(',
            '"Course Schedule"',
            "More than one Course Schedule exists for this Class and date.",
            "Attendance can only be recorded against a Course Schedule assigned to your Instructor profile.",
        ):
            self.assertIn(token, resolver)

    def test_safe_runtime_attendance_reads_and_writes_remain_permission_aware(self):
        source = SAFE.read_text(encoding="utf-8")
        summary = source.split("def _attendance_summary", 1)[1].split(
            "def _room_usage",
            1,
        )[0]
        coverage = source.split("def _attendance_coverage", 1)[1].split(
            "def _attendance_summary",
            1,
        )[0]
        save = source.split("def save_attendance_register", 1)[1]

        for block in (summary, coverage):
            self.assertIn('frappe.get_list(', block)
            self.assertIn('"Student Attendance"', block)
            self.assertNotIn("frappe.get_all(", block)

        for token in (
            'permissions["can_write_attendance"]',
            'permissions["can_create_attendance"]',
            'permissions["can_submit_attendance"]',
            'doc.check_permission("write")',
            'doc.check_permission("submit")',
            "doc.save()",
            "doc.submit()",
        ):
            self.assertIn(token, save)
        self.assertNotIn("ignore_permissions", save)


if __name__ == "__main__":
    unittest.main()
