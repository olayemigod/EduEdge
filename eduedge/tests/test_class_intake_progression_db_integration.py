from __future__ import annotations

import frappe
from education.education.test_utils import before_tests
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from eduedge.api.class_arm_session_rollover import (
	execute_selected_class_arm_session_rollover,
	preview_class_arm_session_rollover,
)
from eduedge.api.class_arms import save_class_arm
from eduedge.api.programme_offering_session_options import get_programme_offering_session_options
from eduedge.api.student_progression import (
	finalize_progression_batch,
	get_progression_destination_options,
	get_student_progression_page,
	prepare_progression_batch,
	preview_progression_batch,
)
from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.academic_progression import (
	PROGRAM_ALLOW_REPETITION_FIELD,
	PROGRAM_NEXT_FIELD,
	PROGRAM_PROGRESSION_MODE_FIELD,
	PROGRAM_TERMINAL_FIELD,
	PROGRAM_PROMOTION,
)
from eduedge.education.class_arm_identity import CLASS_ARM_FIELD, PREVIOUS_GROUP_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD


class TestClassIntakeProgressionDbIntegration(FrappeTestCase):
	"""Exercise the real Primary/Secondary Class Intake -> rollover -> progression path."""

	def setUp(self) -> None:
		before_tests()
		frappe.set_user("Administrator")
		self.suffix = frappe.generate_hash(length=8).upper()
		self.company = "_Test Company"

	def _academic_year(self, label: str, start_date: str, end_date: str):
		return frappe.get_doc(
			{
				"doctype": "Academic Year",
				"academic_year_name": f"QA {label} {self.suffix}",
				"year_start_date": start_date,
				"year_end_date": end_date,
			}
		).insert(ignore_permissions=True)

	def _term(self, year: str, label: str, start_date: str, end_date: str):
		return frappe.get_doc(
			{
				"doctype": "Academic Term",
				"academic_year": year,
				"term_name": f"QA Term {label} {self.suffix}",
				"term_start_date": start_date,
				"term_end_date": end_date,
			}
		).insert(ignore_permissions=True)

	def _calendar(self, institution: str, year: str, start_date: str, end_date: str):
		return frappe.get_doc(
			{
				"doctype": "EduEdge Institution Academic Calendar",
				"institution": institution,
				"academic_year": year,
				"enabled": 1,
				"start_date": start_date,
				"end_date": end_date,
			}
		).insert(ignore_permissions=True)

	def _offering(self, *, branch: str, program: str, year: str, label: str):
		return frappe.get_doc(
			{
				"doctype": "EduEdge Program Offering",
				"school_branch": branch,
				"program": program,
				"academic_year": year,
				"offering_title": f"{label} {self.suffix}",
				"offering_code": f"QA-{label}-{self.suffix}",
				"study_mode": "Full-Time",
				"delivery_mode": "Onsite",
				"is_active": 1,
				"admission_enabled": 1,
				"enrollment_enabled": 1,
			}
		).insert(ignore_permissions=True)

	def _program(self, *, name: str, institution: str, department: str, next_program: str | None = None, terminal: int = 0):
		doc = frappe.get_doc(
			{
				"doctype": "Program",
				"program_name": f"{name} {self.suffix}",
				"department": department,
				INSTITUTION_FIELD: institution,
				PROGRAM_PROGRESSION_MODE_FIELD: PROGRAM_PROMOTION,
				PROGRAM_NEXT_FIELD: next_program,
				PROGRAM_TERMINAL_FIELD: terminal,
				PROGRAM_ALLOW_REPETITION_FIELD: 1,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def test_class_intake_rollover_promotion_and_finalize_retry_are_safe(self):
		# Native sessions remain the academic masters. EduEdge calendars make the
		# sessions operationally ready without changing Class Intake discovery.
		source_year = self._academic_year("SOURCE", "2090-09-01", "2091-08-31")
		destination_year = self._academic_year("DEST", "2091-09-01", "2092-08-31")
		self._term(source_year.name, "SOURCE", "2090-09-01", "2091-08-31")
		self._term(destination_year.name, "DEST", "2091-09-01", "2092-08-31")

		self.assertTrue(frappe.db.exists("EduEdge Institution Type", "PRIMARY"))
		institution = frappe.get_doc(
			{
				"doctype": "EduEdge Institution",
				"institution_name": f"QA Primary School {self.suffix}",
				"institution_code": f"QA-PRI-{self.suffix}",
				"company": self.company,
				"institution_type": "PRIMARY",
				"enabled": 1,
				"is_default": 1,
			}
		).insert(ignore_permissions=True)
		branch = frappe.get_doc(
			{
				"doctype": "EduEdge School Branch",
				"branch_name": f"QA Main Campus {self.suffix}",
				"branch_code": f"QA-BR-{self.suffix}",
				"company": self.company,
				"institution": institution.name,
				"enabled": 1,
				"is_main_branch": 1,
				"is_default": 1,
			}
		).insert(ignore_permissions=True)
		self._calendar(institution.name, source_year.name, "2090-09-01", "2091-08-31")
		self._calendar(institution.name, destination_year.name, "2091-09-01", "2092-08-31")

		# Class Intake must expose both Sessions from the global Academic Year master.
		intake_options = get_programme_offering_session_options(
			institution=institution.name,
			branch=branch.name,
		)
		visible_years = {row["name"] for row in intake_options["options"]["academic_years"]}
		self.assertIn(source_year.name, visible_years)
		self.assertIn(destination_year.name, visible_years)

		department = frappe.get_doc(
			{
				"doctype": "Department",
				"department_name": f"QA Primary Section {self.suffix}",
				"company": self.company,
				"is_group": 0,
				INSTITUTION_FIELD: institution.name,
			}
		).insert(ignore_permissions=True)

		class_two = self._program(
			name="QA Class 2",
			institution=institution.name,
			department=department.name,
			terminal=1,
		)
		class_one = self._program(
			name="QA Class 1",
			institution=institution.name,
			department=department.name,
			next_program=class_two.name,
		)

		# A normal school has each Class Intake available in each Session. Structural
		# Class Arm rollover therefore prepares Class 1A and Class 2A independently;
		# promotion later allocates the learner to the prepared Class 2A.
		source_class_one = self._offering(branch=branch.name, program=class_one.name, year=source_year.name, label="SRC-C1")
		source_class_two = self._offering(branch=branch.name, program=class_two.name, year=source_year.name, label="SRC-C2")
		destination_class_one = self._offering(branch=branch.name, program=class_one.name, year=destination_year.name, label="DST-C1")
		destination_class_two = self._offering(branch=branch.name, program=class_two.name, year=destination_year.name, label="DST-C2")

		student = frappe.get_doc(
			{
				"doctype": "Student",
				"first_name": "QA",
				"last_name": f"Learner {self.suffix}",
				"student_email_id": f"qa-{self.suffix.lower()}@example.com",
				BRANCH_FIELD: branch.name,
			}
		).insert(ignore_permissions=True)

		source_enrollment = frappe.get_doc(
			{
				"doctype": "Program Enrollment",
				"student": student.name,
				"enrollment_date": nowdate(),
				"program": class_one.name,
				"academic_year": source_year.name,
				OFFERING_FIELD: source_class_one.name,
			}
		).insert(ignore_permissions=True)
		source_enrollment.submit()
		self.assertEqual(source_enrollment.docstatus, 1)
		self.assertEqual(source_enrollment.get(BRANCH_FIELD), branch.name)
		self.assertEqual(source_enrollment.get(INSTITUTION_FIELD), institution.name)

		class_one_group = save_class_arm(
			display_name="Class 1A",
			branch=branch.name,
			offering=source_class_one.name,
			group_based_on="Batch",
			students=[{"student": student.name}],
		)
		class_two_group = save_class_arm(
			display_name="Class 2A",
			branch=branch.name,
			offering=source_class_two.name,
			group_based_on="Batch",
			students=[],
		)
		source_group_one_doc = frappe.get_doc("Student Group", class_one_group["name"])
		source_group_two_doc = frappe.get_doc("Student Group", class_two_group["name"])

		rollover_preview = preview_class_arm_session_rollover(
			branch.name,
			source_year.name,
			destination_year.name,
		)
		self.assertEqual(rollover_preview["summary"]["ready"], 2)
		self.assertEqual(rollover_preview["summary"]["source_students"], 1)
		self.assertEqual(rollover_preview["summary"]["students_pending_progression"], 1)
		self.assertEqual(rollover_preview["summary"]["students_to_carry"], 0)

		rollover_result = execute_selected_class_arm_session_rollover(
			branch=branch.name,
			source_academic_year=source_year.name,
			destination_academic_year=destination_year.name,
			class_arm_identities=[
				source_group_one_doc.get(CLASS_ARM_FIELD),
				source_group_two_doc.get(CLASS_ARM_FIELD),
			],
		)
		self.assertEqual(rollover_result["created_count"], 2)
		self.assertEqual(rollover_result["blocked_count"], 0)

		destination_groups = {
			frappe.db.get_value("Student Group", row["name"], OFFERING_FIELD): frappe.get_doc("Student Group", row["name"])
			for row in rollover_result["created"]
		}
		destination_group_one = destination_groups[destination_class_one.name]
		destination_group_two = destination_groups[destination_class_two.name]
		self.assertEqual(destination_group_one.get(PREVIOUS_GROUP_FIELD), source_group_one_doc.name)
		self.assertEqual(destination_group_two.get(PREVIOUS_GROUP_FIELD), source_group_two_doc.name)
		self.assertFalse([row for row in destination_group_one.students if row.active])
		self.assertFalse([row for row in destination_group_two.students if row.active])

		progression_page = get_student_progression_page(
			branch=branch.name,
			source_academic_year=source_year.name,
			program=class_one.name,
		)
		self.assertIn(source_enrollment.name, {row["name"] for row in progression_page["rows"]})
		progression_years = {row["name"] for row in progression_page["academic_years"]}
		self.assertIn(source_year.name, progression_years)
		self.assertIn(destination_year.name, progression_years)

		destination_options = get_progression_destination_options(
			source_enrollment=source_enrollment.name,
			outcome="Promote",
			destination_academic_year=destination_year.name,
		)
		self.assertEqual(destination_options["offering"]["name"], destination_class_two.name)
		self.assertEqual(destination_options["target_program"], class_two.name)
		self.assertIn(destination_group_two.name, {row["name"] for row in destination_options["student_groups"]})

		payload = {
			"source_enrollments": [source_enrollment.name],
			"outcome": "Promote",
			"destination_academic_year": destination_year.name,
			"target_student_group": destination_group_two.name,
			"reason": "Database integration promotion QA",
			"effective_date": nowdate(),
		}
		progression_preview = preview_progression_batch(payload)
		self.assertEqual(progression_preview["summary"], {"selected": 1, "ready": 1, "blocked": 0})

		prepared = prepare_progression_batch(payload)
		self.assertEqual(prepared["created_count"], 1)
		self.assertEqual(prepared["existing_count"], 0)
		target_enrollment_name = prepared["created"][0]["name"]
		target_enrollment = frappe.get_doc("Program Enrollment", target_enrollment_name)
		self.assertEqual(target_enrollment.docstatus, 0)
		self.assertEqual(target_enrollment.program, class_two.name)
		self.assertEqual(target_enrollment.academic_year, destination_year.name)
		self.assertEqual(target_enrollment.get(OFFERING_FIELD), destination_class_two.name)

		# Preparation is idempotent and must not create a second destination draft.
		prepared_retry = prepare_progression_batch(payload)
		self.assertEqual(prepared_retry["created_count"], 0)
		self.assertEqual(prepared_retry["existing_count"], 1)
		self.assertEqual(prepared_retry["existing"][0]["name"], target_enrollment_name)

		target_enrollment.submit()
		self.assertEqual(target_enrollment.docstatus, 1)
		self.assertEqual(frappe.db.get_value("Program Enrollment", source_enrollment.name, "docstatus"), 1)

		finalized = finalize_progression_batch(payload)
		self.assertEqual(finalized["finalized_count"], 1)
		self.assertEqual(finalized["blocked_count"], 0)
		self.assertEqual(finalized["finalized"][0]["new_status"], "Promoted")
		self.assertFalse(finalized["finalized"][0]["existing"])

		destination_group_two.reload()
		self.assertIn(student.name, {row.student for row in destination_group_two.students if row.active})
		source_group_one_doc.reload()
		self.assertIn(student.name, {row.student for row in source_group_one_doc.students if row.active})
		self.assertEqual(
			frappe.db.count(
				"EduEdge Enrollment Status Log",
				{"program_enrollment": source_enrollment.name, "new_status": "Promoted"},
			),
			1,
		)

		# A retried HTTP/RPC finalization after a successful response must be
		# idempotent: return the existing lifecycle decision, not a false blocker.
		finalized_retry = finalize_progression_batch(payload)
		self.assertEqual(finalized_retry["finalized_count"], 1)
		self.assertEqual(finalized_retry["blocked_count"], 0)
		self.assertTrue(finalized_retry["finalized"][0]["existing"])
		self.assertEqual(
			frappe.db.count(
				"EduEdge Enrollment Status Log",
				{"program_enrollment": source_enrollment.name, "new_status": "Promoted"},
			),
			1,
		)
