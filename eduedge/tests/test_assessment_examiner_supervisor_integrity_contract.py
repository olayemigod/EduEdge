from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAssessmentExaminerSupervisorIntegrityContract(unittest.TestCase):
    def test_backend_requires_exact_subject_assignment_for_examiner_only(self):
        source = (APP / "education" / "assessment_operations.py").read_text(encoding="utf-8")
        self.assertIn("def _validate_examiner_and_supervisor", source)
        self.assertIn("assert_schedule_instructor_assignment(", source)
        self.assertIn("doc.examiner", source)
        self.assertIn("effective Subject Instructor Assignment", source)
        self.assertIn("doc.supervisor", source)
        self.assertIn("Supervisor/Invigilator does not need to teach the assessed Subject", source)
        self.assertIn("active Branch eligibility", source)

    def test_form_uses_exact_teaching_query_for_examiner_and_branch_query_for_supervisor(self):
        source = (APP / "public" / "js" / "education" / "assessment_plan.js").read_text(encoding="utf-8")
        examiner = source.split('frm.set_query("examiner"', 1)[1].split('frm.set_query("supervisor"', 1)[0]
        supervisor = source.split('frm.set_query("supervisor"', 1)[1]
        self.assertIn("eduedge.api.teaching_assignment_options.course_schedule_instructor_query", examiner)
        self.assertIn("student_group: frm.doc.student_group", examiner)
        self.assertIn("course: frm.doc.course", examiner)
        self.assertIn("reference_date: frm.doc.schedule_date", examiner)
        self.assertIn("eduedge.api.academic_operations.instructor_query", supervisor)
        self.assertIn("course(frm)", source)
        self.assertIn('frm.set_value("examiner", null)', source)


if __name__ == "__main__":
    unittest.main()
