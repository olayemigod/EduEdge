from __future__ import annotations

import frappe
from education.education.test_utils import before_tests
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from eduedge.api.student_progression import (
	finalize_progression_batch,
	get_progression_destination_options,
	prepare_progression_batch,
	preview_progression_batch,
)
from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.academic_progression import (
	PROGRAM_ALLOW_REPETITION_FIELD,
	PROGRAM_NEXT_FIELD,
	PROGRAM_PROGRESSION_MODE_FIELD,
	PROGRAM_PROMOTION,
	PROGRAM_TERMINAL_FIELD,
)
from eduedge.education.custom_fields import BRANCH_FIELD


class TestProgressionOutcomeMatrix(FrappeTestCase):
	"""Database-backed negative and lifecycle coverage for school progression."""

	def setUp(self) -> None:
		before_tests()
		frappe.set_user("Administrator")
		self.suffix = frappe.generate_hash(length=8).upper()
		self.company = "_Test Company"

	def _insert(self, doctype: str, **values):
		return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)

	def _year(self, label: str, start: str, end: str):
		year = self._insert(
			"Academic Year",
			academic_year_name=f"QA {label} {self.suffix}",
			year_start_date=start,
			year_end_date=end,
		)
		self._insert(
			"Academic Term",
			academic_year=year.name,
			term_name=f"QA {label} TERM {self.suffix}",
			term_start_date=start,
			term_end_date=end,
		)
		return year

	def _calendar(self, institution: str, year, start: str, end: str) -> None:
		self._insert(
			"EduEdge Institution Academic Calendar",
			institution=institution,
			academic_year=year.name,
			enabled=1,
			start_date=start,
			end_date=end,
		)

	def _branch(self, institution: str, label: str):
		return self._insert(
			"EduEdge School Branch",
			branch_name=f"QA {label} {self.suffix}",
			branch_code=f"QA{label[:3].upper()}{self.suffix}",
			company=self.company,
			institution=institution,
			enabled=1,
		)

	def _program(self, label: str, institution: str, department: str, *, next_program=None, terminal=0):
		return self._insert(
			"Program",
			program_name=f"{label} {self.suffix}",
			department=department,
			**{
				INSTITUTION_FIELD: institution,
				PROGRAM_PROGRESSION_MODE_FIELD: PROGRAM_PROMOTION,
				PROGRAM_NEXT_FIELD: next_program,
				PROGRAM_TERMINAL_FIELD: terminal,
				PROGRAM_ALLOW_REPETITION_FIELD: 1,
			},
		)

	def _offering(
		self,
		branch: str,
		program: str,
		year: str,
		code: str,
		*,
		study_mode: str = "Full-Time",
		delivery_mode: str = "Onsite",
	):
		return self._insert(
			"EduEdge Program Offering",
			school_branch=branch,
			program=program,
			academic_year=year,
			offering_title=f"{code} {self.suffix}",
			offering_code=f"QA-{code}-{self.suffix}",
			study_mode=study_mode,
			delivery_mode=delivery_mode,
			is_active=1,
			admission_enabled=1,
			enrollment_enabled=1,
		)

	def _student_enrollment(self, branch: str, program: str, year: str, offering: str, label: str):
		student = self._insert(
			"Student",
			first_name="QA",
			last_name=f"{label} {self.suffix}",
			student_email_id=f"qa-{label.lower()}-{self.suffix.lower()}@example.com",
			**{BRANCH_FIELD: branch},
		)
		enrollment = self._insert(
			"Program Enrollment",
			student=student.name,
			enrollment_date=nowdate(),
			program=program,
			academic_year=year,
			**{OFFERING_FIELD: offering},
		)
		enrollment.submit()
		return student, enrollment

	def _foundation(self):
		earlier = self._year("EARLIER", "2089-09-01", "2090-08-31")
		source = self._year("SOURCE", "2090-09-01", "2091-08-31")
		destination = self._year("DEST", "2091-09-01", "2092-08-31")
		institution = self._insert(
			"EduEdge Institution",
			institution_name=f"QA Progression School {self.suffix}",
			institution_code=f"QAPROG{self.suffix}",
			company=self.company,
			institution_type="PRIMARY",
			enabled=1,
		)
		for year, start, end in (
			(earlier, "2089-09-01", "2090-08-31"),
			(source, "2090-09-01", "2091-08-31"),
			(destination, "2091-09-01", "2092-08-31"),
		):
			self._calendar(institution.name, year, start, end)
		branch_a = self._branch(institution.name, "Main Campus")
		branch_b = self._branch(institution.name, "Annex Campus")
		department = self._insert(
			"Department",
			department_name=f"QA Progression Section {self.suffix}",
			company=self.company,
			is_group=0,
			**{INSTITUTION_FIELD: institution.name},
		)
		class_two = self._program("QA Class 2", institution.name, department.name, terminal=1)
		class_one = self._program(
			"QA Class 1",
			institution.name,
			department.name,
			next_program=class_two.name,
		)
		source_class_one = self._offering(branch_a.name, class_one.name, source.name, "SRC-C1")
		source_class_two = self._offering(branch_a.name, class_two.name, source.name, "SRC-C2")
		return frappe._dict(
			{
				"earlier": earlier,
				"source": source,
				"destination": destination,
				"institution": institution,
				"branch_a": branch_a,
				"branch_b": branch_b,
				"department": department,
				"class_one": class_one,
				"class_two": class_two,
				"source_class_one": source_class_one,
				"source_class_two": source_class_two,
			}
		)

	def test_promotion_rejects_same_earlier_missing_and_ambiguous_destinations(self):
		ctx = self._foundation()
		_student, enrollment = self._student_enrollment(
			ctx.branch_a.name,
			ctx.class_one.name,
			ctx.source.name,
			ctx.source_class_one.name,
			"PromotionGuard",
		)

		for invalid_year in (ctx.source.name, ctx.earlier.name):
			with self.assertRaisesRegex(frappe.ValidationError, "later Academic Session"):
				get_progression_destination_options(
					source_enrollment=enrollment.name,
					outcome="Promote",
					destination_academic_year=invalid_year,
				)

		with self.assertRaisesRegex(frappe.ValidationError, "No active sessional Programme Offering"):
			get_progression_destination_options(
				source_enrollment=enrollment.name,
				outcome="Promote",
				destination_academic_year=ctx.destination.name,
			)

		self._offering(ctx.branch_a.name, ctx.class_two.name, ctx.destination.name, "DST-C2-FT")
		self._offering(
			ctx.branch_a.name,
			ctx.class_two.name,
			ctx.destination.name,
			"DST-C2-PT",
			study_mode="Part-Time",
		)
		with self.assertRaisesRegex(frappe.ValidationError, "More than one destination Programme Offering"):
			get_progression_destination_options(
				source_enrollment=enrollment.name,
				outcome="Promote",
				destination_academic_year=ctx.destination.name,
			)

	def test_repeat_next_session_is_draft_first_and_idempotent(self):
		ctx = self._foundation()
		destination_offering = self._offering(
			ctx.branch_a.name,
			ctx.class_one.name,
			ctx.destination.name,
			"DST-REPEAT-C1",
		)
		_student, enrollment = self._student_enrollment(
			ctx.branch_a.name,
			ctx.class_one.name,
			ctx.source.name,
			ctx.source_class_one.name,
			"Repeat",
		)
		options = get_progression_destination_options(
			source_enrollment=enrollment.name,
			outcome="Repeat",
			destination_academic_year=ctx.destination.name,
		)
		self.assertEqual(options["offering"]["name"], destination_offering.name)
		self.assertEqual(options["target_program"], ctx.class_one.name)

		payload = {
			"source_enrollments": [enrollment.name],
			"outcome": "Repeat",
			"destination_academic_year": ctx.destination.name,
			"reason": "Database integration repeat QA",
			"effective_date": nowdate(),
		}
		self.assertEqual(preview_progression_batch(payload)["summary"]["blocked"], 0)
		prepared = prepare_progression_batch(payload)
		self.assertEqual((prepared["created_count"], prepared["existing_count"]), (1, 0))
		target = frappe.get_doc("Program Enrollment", prepared["created"][0]["name"])
		self.assertEqual(target.docstatus, 0)
		self.assertEqual(target.program, ctx.class_one.name)
		self.assertEqual(target.academic_year, ctx.destination.name)
		self.assertEqual(target.get(OFFERING_FIELD), destination_offering.name)
		prepared_retry = prepare_progression_batch(payload)
		self.assertEqual((prepared_retry["created_count"], prepared_retry["existing_count"]), (0, 1))
		target.submit()

		finalized = finalize_progression_batch(payload)
		self.assertEqual((finalized["finalized_count"], finalized["blocked_count"]), (1, 0))
		self.assertEqual(finalized["finalized"][0]["new_status"], "Repeated")
		self.assertFalse(finalized["finalized"][0]["existing"])
		finalized_retry = finalize_progression_batch(payload)
		self.assertEqual((finalized_retry["finalized_count"], finalized_retry["blocked_count"]), (1, 0))
		self.assertTrue(finalized_retry["finalized"][0]["existing"])
		self.assertEqual(
			frappe.db.count(
				"EduEdge Enrollment Status Log",
				{"program_enrollment": enrollment.name, "new_status": "Repeated"},
			),
			1,
		)

	def test_next_session_internal_transfer_and_cross_institution_guard(self):
		ctx = self._foundation()
		target_offering = self._offering(
			ctx.branch_b.name,
			ctx.class_one.name,
			ctx.destination.name,
			"DST-TRANSFER-C1",
		)
		_student, enrollment = self._student_enrollment(
			ctx.branch_a.name,
			ctx.class_one.name,
			ctx.source.name,
			ctx.source_class_one.name,
			"Transfer",
		)

		other_institution = self._insert(
			"EduEdge Institution",
			institution_name=f"QA Other School {self.suffix}",
			institution_code=f"QAOTHER{self.suffix}",
			company=self.company,
			institution_type="PRIMARY",
			enabled=1,
		)
		self._calendar(other_institution.name, ctx.destination, "2091-09-01", "2092-08-31")
		other_branch = self._branch(other_institution.name, "Other Campus")
		with self.assertRaisesRegex(frappe.ValidationError, "same Institution"):
			get_progression_destination_options(
				source_enrollment=enrollment.name,
				outcome="Transfer",
				destination_academic_year=ctx.destination.name,
				target_branch=other_branch.name,
			)

		options = get_progression_destination_options(
			source_enrollment=enrollment.name,
			outcome="Transfer",
			destination_academic_year=ctx.destination.name,
			target_branch=ctx.branch_b.name,
		)
		self.assertEqual(options["offering"]["name"], target_offering.name)
		self.assertEqual(options["target_program"], ctx.class_one.name)
		payload = {
			"source_enrollments": [enrollment.name],
			"outcome": "Transfer",
			"destination_academic_year": ctx.destination.name,
			"target_branch": ctx.branch_b.name,
			"reason": "Database integration transfer QA",
			"effective_date": nowdate(),
		}
		self.assertEqual(preview_progression_batch(payload)["summary"]["blocked"], 0)
		prepared = prepare_progression_batch(payload)
		self.assertEqual(prepared["created_count"], 1)
		target = frappe.get_doc("Program Enrollment", prepared["created"][0]["name"])
		self.assertEqual(target.get(BRANCH_FIELD), ctx.branch_b.name)
		self.assertEqual(target.get(OFFERING_FIELD), target_offering.name)
		target.submit()
		finalized = finalize_progression_batch(payload)
		self.assertEqual((finalized["finalized_count"], finalized["blocked_count"]), (1, 0))
		self.assertEqual(finalized["finalized"][0]["new_status"], "Transferred")
		log = frappe.get_doc("EduEdge Enrollment Status Log", finalized["finalized"][0]["name"])
		self.assertEqual(log.target_branch, ctx.branch_b.name)
		self.assertEqual(log.target_program_offering, target_offering.name)

	def test_terminal_graduation_and_non_terminal_guard(self):
		ctx = self._foundation()
		_student, terminal_enrollment = self._student_enrollment(
			ctx.branch_a.name,
			ctx.class_two.name,
			ctx.source.name,
			ctx.source_class_two.name,
			"Graduate",
		)
		graduate_payload = {
			"source_enrollments": [terminal_enrollment.name],
			"outcome": "Graduate",
			"reason": "Database integration graduation QA",
			"effective_date": nowdate(),
		}
		graduated = finalize_progression_batch(graduate_payload)
		self.assertEqual((graduated["finalized_count"], graduated["blocked_count"]), (1, 0))
		self.assertEqual(graduated["finalized"][0]["new_status"], "Graduated")
		self.assertFalse(graduated["finalized"][0]["existing"])
		graduated_retry = finalize_progression_batch(graduate_payload)
		self.assertEqual((graduated_retry["finalized_count"], graduated_retry["blocked_count"]), (1, 0))
		self.assertTrue(graduated_retry["finalized"][0]["existing"])

		_student, non_terminal_enrollment = self._student_enrollment(
			ctx.branch_a.name,
			ctx.class_one.name,
			ctx.source.name,
			ctx.source_class_one.name,
			"EarlyGraduate",
		)
		blocked = finalize_progression_batch(
			{
				"source_enrollments": [non_terminal_enrollment.name],
				"outcome": "Graduate",
				"reason": "Must not graduate a non-terminal class",
				"effective_date": nowdate(),
			}
		)
		self.assertEqual((blocked["finalized_count"], blocked["blocked_count"]), (0, 1))
		self.assertIn("terminal", blocked["blocked"][0]["reason"].lower())
