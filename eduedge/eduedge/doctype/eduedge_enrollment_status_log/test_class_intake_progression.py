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
	PROGRAM_PROMOTION,
	PROGRAM_TERMINAL_FIELD,
)
from eduedge.education.class_arm_identity import CLASS_ARM_FIELD, PREVIOUS_GROUP_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD


class TestClassIntakeProgressionIntegration(FrappeTestCase):
	"""Real database coverage for Class Intake -> Class Arm rollover -> promotion."""

	def setUp(self) -> None:
		before_tests()
		frappe.set_user("Administrator")
		self.suffix = frappe.generate_hash(length=8).upper()
		self.company = "_Test Company"

	def _insert(self, doctype: str, **values):
		return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)

	def _make_year(self, label: str, start: str, end: str):
		return self._insert(
			"Academic Year",
			academic_year_name=f"QA {label} {self.suffix}",
			year_start_date=start,
			year_end_date=end,
		)

	def _make_term(self, year: str, label: str, start: str, end: str):
		return self._insert(
			"Academic Term",
			academic_year=year,
			term_name=f"QA {label} {self.suffix}",
			term_start_date=start,
			term_end_date=end,
		)

	def _make_offering(self, branch: str, program: str, year: str, code: str):
		return self._insert(
			"EduEdge Program Offering",
			school_branch=branch,
			program=program,
			academic_year=year,
			offering_title=f"{code} {self.suffix}",
			offering_code=f"QA-{code}-{self.suffix}",
			study_mode="Full-Time",
			delivery_mode="Onsite",
			is_active=1,
			admission_enabled=1,
			enrollment_enabled=1,
		)

	def _make_program(self, label: str, institution: str, department: str, *, next_program=None, terminal=0):
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

	def test_class_intake_rollover_promotion_and_retry(self):
		source_year = self._make_year("SOURCE", "2090-09-01", "2091-08-31")
		destination_year = self._make_year("DEST", "2091-09-01", "2092-08-31")
		self._make_term(source_year.name, "SOURCE TERM", "2090-09-01", "2091-08-31")
		self._make_term(destination_year.name, "DEST TERM", "2091-09-01", "2092-08-31")

		self.assertTrue(frappe.db.exists("EduEdge Institution Type", "PRIMARY"))
		institution = self._insert(
			"EduEdge Institution",
			institution_name=f"QA Primary School {self.suffix}",
			institution_code=f"QAPRI{self.suffix}",
			company=self.company,
			institution_type="PRIMARY",
			enabled=1,
		)
		branch = self._insert(
			"EduEdge School Branch",
			branch_name=f"QA Main Campus {self.suffix}",
			branch_code=f"QABR{self.suffix}",
			company=self.company,
			institution=institution.name,
			enabled=1,
		)
		for year, start, end in (
			(source_year, "2090-09-01", "2091-08-31"),
			(destination_year, "2091-09-01", "2092-08-31"),
		):
			self._insert(
				"EduEdge Institution Academic Calendar",
				institution=institution.name,
				academic_year=year.name,
				enabled=1,
				start_date=start,
				end_date=end,
			)

		# Class Intake session discovery must expose both global Academic Years.
		options = get_programme_offering_session_options(institution=institution.name, branch=branch.name)
		visible_years = {row["name"] for row in options["options"]["academic_years"]}
		self.assertTrue({source_year.name, destination_year.name}.issubset(visible_years))

		department = self._insert(
			"Department",
			department_name=f"QA Primary Section {self.suffix}",
			company=self.company,
			is_group=0,
			**{INSTITUTION_FIELD: institution.name},
		)
		class_two = self._make_program("QA Class 2", institution.name, department.name, terminal=1)
		class_one = self._make_program(
			"QA Class 1",
			institution.name,
			department.name,
			next_program=class_two.name,
		)

		src_c1 = self._make_offering(branch.name, class_one.name, source_year.name, "SRC-C1")
		src_c2 = self._make_offering(branch.name, class_two.name, source_year.name, "SRC-C2")
		dst_c1 = self._make_offering(branch.name, class_one.name, destination_year.name, "DST-C1")
		dst_c2 = self._make_offering(branch.name, class_two.name, destination_year.name, "DST-C2")

		student = self._insert(
			"Student",
			first_name="QA",
			last_name=f"Learner {self.suffix}",
			student_email_id=f"qa-{self.suffix.lower()}@example.com",
			**{BRANCH_FIELD: branch.name},
		)
		source_enrollment = self._insert(
			"Program Enrollment",
			student=student.name,
			enrollment_date=nowdate(),
			program=class_one.name,
			academic_year=source_year.name,
			**{OFFERING_FIELD: src_c1.name},
		)
		source_enrollment.submit()
		self.assertEqual(source_enrollment.get(BRANCH_FIELD), branch.name)
		self.assertEqual(source_enrollment.get(INSTITUTION_FIELD), institution.name)

		src_group_one = save_class_arm(
			display_name="Class 1A",
			branch=branch.name,
			offering=src_c1.name,
			group_based_on="Batch",
			students=[{"student": student.name}],
		)
		src_group_two = save_class_arm(
			display_name="Class 2A",
			branch=branch.name,
			offering=src_c2.name,
			group_based_on="Batch",
			students=[],
		)
		src_group_one = frappe.get_doc("Student Group", src_group_one["name"])
		src_group_two = frappe.get_doc("Student Group", src_group_two["name"])

		rollover_preview = preview_class_arm_session_rollover(branch.name, source_year.name, destination_year.name)
		self.assertEqual(rollover_preview["summary"]["ready"], 2)
		self.assertEqual(rollover_preview["summary"]["source_students"], 1)
		self.assertEqual(rollover_preview["summary"]["students_to_carry"], 0)

		rollover = execute_selected_class_arm_session_rollover(
			branch=branch.name,
			source_academic_year=source_year.name,
			destination_academic_year=destination_year.name,
			class_arm_identities=[src_group_one.get(CLASS_ARM_FIELD), src_group_two.get(CLASS_ARM_FIELD)],
		)
		self.assertEqual((rollover["created_count"], rollover["blocked_count"]), (2, 0))
		dst_groups = {
			frappe.db.get_value("Student Group", row["name"], OFFERING_FIELD): frappe.get_doc("Student Group", row["name"])
			for row in rollover["created"]
		}
		dst_group_one = dst_groups[dst_c1.name]
		dst_group_two = dst_groups[dst_c2.name]
		self.assertEqual(dst_group_one.get(PREVIOUS_GROUP_FIELD), src_group_one.name)
		self.assertEqual(dst_group_two.get(PREVIOUS_GROUP_FIELD), src_group_two.name)
		self.assertFalse([row for row in dst_group_one.students if row.active])
		self.assertFalse([row for row in dst_group_two.students if row.active])

		page = get_student_progression_page(
			branch=branch.name,
			source_academic_year=source_year.name,
			program=class_one.name,
		)
		self.assertIn(source_enrollment.name, {row["name"] for row in page["rows"]})
		self.assertTrue(
			{source_year.name, destination_year.name}.issubset({row["name"] for row in page["academic_years"]})
		)
		destination = get_progression_destination_options(
			source_enrollment=source_enrollment.name,
			outcome="Promote",
			destination_academic_year=destination_year.name,
		)
		self.assertEqual(destination["offering"]["name"], dst_c2.name)
		self.assertIn(dst_group_two.name, {row["name"] for row in destination["student_groups"]})

		payload = {
			"source_enrollments": [source_enrollment.name],
			"outcome": "Promote",
			"destination_academic_year": destination_year.name,
			"target_student_group": dst_group_two.name,
			"reason": "Database integration promotion QA",
			"effective_date": nowdate(),
		}
		self.assertEqual(preview_progression_batch(payload)["summary"]["blocked"], 0)
		prepared = prepare_progression_batch(payload)
		self.assertEqual((prepared["created_count"], prepared["existing_count"]), (1, 0))
		target_name = prepared["created"][0]["name"]
		prepared_retry = prepare_progression_batch(payload)
		self.assertEqual((prepared_retry["created_count"], prepared_retry["existing_count"]), (0, 1))
		self.assertEqual(prepared_retry["existing"][0]["name"], target_name)

		target_enrollment = frappe.get_doc("Program Enrollment", target_name)
		self.assertEqual(target_enrollment.docstatus, 0)
		self.assertEqual(target_enrollment.get(OFFERING_FIELD), dst_c2.name)
		target_enrollment.submit()
		self.assertEqual(frappe.db.get_value("Program Enrollment", source_enrollment.name, "docstatus"), 1)

		finalized = finalize_progression_batch(payload)
		self.assertEqual((finalized["finalized_count"], finalized["blocked_count"]), (1, 0))
		self.assertFalse(finalized["finalized"][0]["existing"])
		dst_group_two.reload()
		self.assertIn(student.name, {row.student for row in dst_group_two.students if row.active})
		src_group_one.reload()
		self.assertIn(student.name, {row.student for row in src_group_one.students if row.active})
		self.assertEqual(
			frappe.db.count(
				"EduEdge Enrollment Status Log",
				{"program_enrollment": source_enrollment.name, "new_status": "Promoted"},
			),
			1,
		)

		# Retry safety is part of the release gate: the same finalization must return
		# the existing log, not create another log or report a false transition blocker.
		finalized_retry = finalize_progression_batch(payload)
		self.assertEqual((finalized_retry["finalized_count"], finalized_retry["blocked_count"]), (1, 0))
		self.assertTrue(finalized_retry["finalized"][0]["existing"])
		self.assertEqual(
			frappe.db.count(
				"EduEdge Enrollment Status Log",
				{"program_enrollment": source_enrollment.name, "new_status": "Promoted"},
			),
			1,
		)
