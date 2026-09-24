from __future__ import annotations

from datetime import timedelta

import frappe
from education.education.test_utils import before_tests
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from eduedge.cbt.attempt_review import resolve_attempt_review
from eduedge.cbt.attempt_runtime_guard import (
    get_attempt_state,
    submit_attempt,
    sync_answers,
)
from eduedge.cbt.attempts import prepare_attempt, start_attempt
from eduedge.cbt.result_readiness import get_result_readiness
from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD


class TestCBTCandidateOfflineResilientFlow(FrappeTestCase):
    """DB-backed freeze for the school CBT offline-resilient server lifecycle."""

    def setUp(self) -> None:
        before_tests()
        frappe.set_user("Administrator")
        self.suffix = frappe.generate_hash(length=8).upper()
        self.company = "_Test Company"

    def _insert(self, doctype: str, **values):
        return frappe.get_doc({"doctype": doctype, **values}).insert(
            ignore_permissions=True
        )

    def _insert_guarded(self, doctype: str, **values):
        doc = frappe.get_doc({"doctype": doctype, **values})
        doc.flags.eduedge_access_guarded = True
        return doc.insert(ignore_permissions=True)

    def _make_foundation(self):
        institution = self._insert(
            "EduEdge Institution",
            institution_name=f"QA CBT School {self.suffix}",
            institution_code=f"QACBT{self.suffix}",
            company=self.company,
            institution_type="PRIMARY",
            enabled=1,
        )
        branch = self._insert(
            "EduEdge School Branch",
            branch_name=f"QA CBT Campus {self.suffix}",
            branch_code=f"QACBT{self.suffix}",
            company=self.company,
            institution=institution.name,
            enabled=1,
        )

        course_values = {
            "course_name": f"QA CBT Mathematics {self.suffix}",
        }
        course_meta = frappe.get_meta("Course")
        if course_meta.has_field(BRANCH_FIELD):
            course_values[BRANCH_FIELD] = branch.name
        if course_meta.has_field(INSTITUTION_FIELD):
            course_values[INSTITUTION_FIELD] = institution.name
        if course_meta.has_field("company"):
            course_values["company"] = self.company
        course = self._insert("Course", **course_values)

        student = self._insert(
            "Student",
            first_name="QA",
            last_name=f"CBT Learner {self.suffix}",
            student_email_id=f"qa-cbt-{self.suffix.lower()}@example.com",
            enabled=1,
            **{BRANCH_FIELD: branch.name},
        )

        centre = self._insert(
            "EduEdge Examination Centre",
            centre_name=f"QA CBT Centre {self.suffix}",
            centre_code=f"QACBT-C-{self.suffix}",
            centre_type="School Examination Centre",
            school_branch=branch.name,
            centre_status="Active",
            capacity=30,
        )

        question = self._insert(
            "EduEdge CBT Question",
            question_code=f"QACBT-Q-{self.suffix}",
            ownership_scope="School Question Bank",
            school_branch=branch.name,
            course=course.name,
            difficulty="Moderate",
            question_type="Single Choice",
            question_text="<p>What is 2 + 2?</p>",
            default_mark=1,
            negative_mark=0,
            status="Approved",
            options=[
                {"option_text": "4", "is_correct": 1},
                {"option_text": "5", "is_correct": 0},
            ],
        )

        template = self._insert(
            "EduEdge CBT Exam Template",
            template_title=f"QA Offline CBT {self.suffix}",
            template_code=f"QACBT-T-{self.suffix}",
            exam_scope="School Examination",
            template_reuse_scope="Branch-wide",
            school_branch=branch.name,
            exam_purpose="Other",
            template_mode="Fixed Question Set",
            subject_applicability="Specific Subject",
            course=course.name,
            duration_minutes=30,
            maximum_attempts=1,
            pass_percentage=50,
            navigation_policy="Free Navigation",
            auto_submit_on_timeout=1,
            allow_resume=1,
            randomise_questions=0,
            randomise_options=0,
            marking_policy="Use Question Marks",
            result_release_policy="Manual Approval",
            device_change_policy="Allowed Before First Answer Only",
            attempt_review_policy="Review Flagged Attempts Only",
            status="Approved",
            questions=[{"question": question.name, "display_order": 1}],
        )

        scheduled_start = now_datetime() - timedelta(minutes=1)
        schedule = self._insert_guarded(
            "EduEdge CBT Exam Schedule",
            schedule_title=f"QA Offline Schedule {self.suffix}",
            schedule_code=f"QACBT-S-{self.suffix}",
            exam_template=template.name,
            examination_centre=centre.name,
            scheduled_start=scheduled_start,
            require_candidate_check_in=0,
            candidate_start_mode="Automatic Start at Scheduled Time",
            allow_late_entry=1,
            late_entry_grace_minutes=5,
            status="Draft",
        )

        assignment = self._insert_guarded(
            "EduEdge CBT Candidate Assignment",
            exam_schedule=schedule.name,
            student=student.name,
            assignment_status="Draft",
        )

        # This test freezes the attempt engine, not the upstream schedule lifecycle.
        # Seed the already-governed operational state without duplicating schedule
        # readiness/activation tests in this fixture.
        frappe.db.set_value(
            "EduEdge CBT Exam Schedule",
            schedule.name,
            "status",
            "Active",
            update_modified=False,
        )
        frappe.db.set_value(
            "EduEdge CBT Candidate Assignment",
            assignment.name,
            "assignment_status",
            "Released",
            update_modified=False,
        )

        return {
            "institution": institution,
            "branch": branch,
            "course": course,
            "student": student,
            "centre": centre,
            "question": question,
            "template": template,
            "schedule": schedule,
            "assignment": assignment,
        }

    def test_candidate_offline_resilient_attempt_lifecycle(self):
        fixture = self._make_foundation()

        launch = prepare_attempt(fixture["assignment"].name)
        attempt_name = launch["attempt"]
        launch_token = launch["launch_token"]
        client_session = f"qa-session-{self.suffix.lower()}"

        attempt = frappe.get_doc("EduEdge CBT Attempt", attempt_name)
        self.assertEqual(attempt.attempt_status, "Prepared")
        self.assertNotEqual(attempt.launch_token_hash, launch_token)
        self.assertEqual(attempt.question_count, 1)

        prepared_state = get_attempt_state(attempt_name, launch_token)
        self.assertEqual(prepared_state["status"], "Prepared")
        self.assertEqual(prepared_state["questions"], [])
        self.assertEqual(prepared_state["answers"], {})

        with self.assertRaises(frappe.DuplicateEntryError):
            prepare_attempt(fixture["assignment"].name)

        started = start_attempt(attempt_name, launch_token, client_session)
        self.assertEqual(started["status"], "In Progress")
        self.assertEqual(len(started["questions"]), 1)
        self.assertGreater(started["seconds_remaining"], 0)

        question = started["questions"][0]
        option_id = question["options"][0]["id"]
        client_saved_at = str(now_datetime())
        answers = [
            {
                "question_snapshot_key": question["snapshot_key"],
                "client_revision": 1,
                "client_saved_at": client_saved_at,
                "answer": {"selected_option_ids": [option_id]},
            }
        ]
        first_sync = sync_answers(
            attempt_name,
            launch_token,
            client_session,
            f"qa-batch-1-{self.suffix}",
            answers,
            reported_pending_count=0,
        )
        self.assertEqual(first_sync["status"], "Applied")
        self.assertEqual(first_sync["applied_count"], 1)
        self.assertEqual(first_sync["answered_count"], 1)

        replay = sync_answers(
            attempt_name,
            launch_token,
            client_session,
            f"qa-batch-1-{self.suffix}",
            answers,
            reported_pending_count=0,
        )
        self.assertTrue(replay["idempotent_replay"])
        self.assertEqual(replay["applied_count"], 1)

        pending_submission = submit_attempt(
            attempt_name,
            launch_token,
            client_session,
            reported_pending_count=1,
        )
        self.assertEqual(pending_submission["status"], "Pending Sync")

        blocked = get_result_readiness(fixture["schedule"].name)
        blocker_codes = {row["code"] for row in blocked["approval_blockers"]}
        self.assertIn("PENDING_SYNC", blocker_codes)
        self.assertFalse(blocked["ready_for_result_processing"])
        self.assertFalse(blocked["ready_for_result_approval"])

        reconciled_answers = [
            {
                "question_snapshot_key": question["snapshot_key"],
                "client_revision": 2,
                "client_saved_at": client_saved_at,
                "answer": {"selected_option_ids": [option_id]},
            }
        ]
        reconciled = sync_answers(
            attempt_name,
            launch_token,
            client_session,
            f"qa-batch-2-{self.suffix}",
            reconciled_answers,
            reported_pending_count=0,
        )
        self.assertEqual(reconciled["status"], "Submitted")
        self.assertEqual(reconciled["reported_pending_count"], 0)

        terminal_state = get_attempt_state(
            attempt_name,
            launch_token,
            client_session,
        )
        self.assertEqual(terminal_state["status"], "Submitted")
        self.assertEqual(terminal_state["questions"], [])

        attempt.reload()
        self.assertEqual(attempt.attempt_status, "Submitted")
        self.assertEqual(attempt.reported_pending_sync_count, 0)
        self.assertEqual(attempt.requires_review, 1)
        self.assertIn(
            "Answers were reconciled after submission or timeout.",
            attempt.review_reasons,
        )

        after_reconciliation = get_result_readiness(fixture["schedule"].name)
        blocker_codes = {
            row["code"] for row in after_reconciliation["approval_blockers"]
        }
        self.assertNotIn("PENDING_SYNC", blocker_codes)
        self.assertIn("REVIEW_REQUIRED", blocker_codes)
        self.assertFalse(after_reconciliation["ready_for_result_processing"])

        review = resolve_attempt_review(
            attempt_name,
            "Accept for Scoring",
            "Offline reconciliation verified against the server cutoff.",
        )
        self.assertEqual(review["requires_review_after"], 0)

        ready_for_processing = get_result_readiness(fixture["schedule"].name)
        blocker_codes = {
            row["code"] for row in ready_for_processing["approval_blockers"]
        }
        self.assertTrue(ready_for_processing["ready_for_result_processing"])
        self.assertFalse(ready_for_processing["ready_for_result_approval"])
        self.assertNotIn("PENDING_SYNC", blocker_codes)
        self.assertNotIn("REVIEW_REQUIRED", blocker_codes)
        self.assertIn("NOT_SCORED", blocker_codes)

        answer = frappe.db.get_value(
            "EduEdge CBT Attempt Answer",
            {
                "attempt": attempt_name,
                "question_snapshot_key": question["snapshot_key"],
            },
            ["client_revision", "server_revision"],
            as_dict=True,
        )
        self.assertEqual(answer.client_revision, 2)
        self.assertEqual(answer.server_revision, 2)
        self.assertEqual(
            frappe.db.count("EduEdge CBT Sync Log", {"attempt": attempt_name}),
            2,
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
