from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestProgrammeCurriculumGovernanceContract(unittest.TestCase):
	def test_backend_updates_native_program_course_rows_safely(self):
		api = (APP / "api" / "programme_curriculum_governance.py").read_text(encoding="utf-8")
		for token in (
			"add_programme_courses",
			"update_programme_course_requirement",
			"remove_programme_course",
			'@frappe.whitelist(methods=["POST"])',
			'doc.append("courses", {"course": name, "required": required_value})',
			"row.required = 1 if cint(required) else 0",
			"doc.remove(row)",
			"subject_master_deleted",
			"Existing academic history will not be altered",
			"require_eduedge_access",
			"doc.check_permission(permission_type)",
		):
			self.assertIn(token, api)
		self.assertNotIn("ignore_permissions", api)
		self.assertNotIn("frappe.db.set_value", api)
		self.assertNotIn("frappe.delete_doc", api)

	def test_removal_requires_exact_programme_scoped_dependency_checks(self):
		api = (APP / "api" / "programme_curriculum_governance.py").read_text(encoding="utf-8")
		for token in (
			"_dependency_summary",
			"_programme_offerings",
			"EduEdge Instructor Assignment",
			"Course Schedule",
			"Assessment Plan",
			"Assessment Result",
			"EduEdge CBT Exam Schedule",
			"if len(usable) < 2",
			"Never fall back to a global Subject-only check",
		):
			self.assertIn(token, api)

	def test_programmes_bundle_installs_governance_controls_from_mounted_proxy(self):
		entry = (APP / "public" / "js" / "eduedge_programmes.bundle.js").read_text(encoding="utf-8")
		ui = (APP / "public" / "js" / "eduedge_programmes" / "curriculum_governance.js").read_text(encoding="utf-8")
		for token in (
			"installProgrammeCurriculumGovernance",
			"curriculum_governance",
			"const proxy = originalMount(root)",
			"installProgrammeCurriculumGovernance(app, root, proxy)",
		):
			self.assertIn(token, entry)
		for token in (
			"mountedProxy = null",
			"mountedProxy || app?._instance?.proxy",
			"Required or Optional",
			"Add as Required",
			"Add as Optional",
			"Remove",
			"Subject master will not be deleted",
			"update_programme_course_requirement",
			"remove_programme_course",
			"add_programme_courses",
			"MutationObserver",
		):
			self.assertIn(token, ui)

	def test_class_modal_save_uses_explicit_post_and_server_identity(self):
		entry = (APP / "public" / "js" / "eduedge_programmes.bundle.js").read_text(encoding="utf-8")
		fix = (APP / "public" / "js" / "eduedge_programmes" / "programme_modal_save_fix.js").read_text(encoding="utf-8")
		for token in (
			"installProgrammeModalSaveFix",
			"programme_modal_save_fix",
			"installProgrammeModalSaveFix(proxy)",
		):
			self.assertIn(token, entry)
		for token in (
			"eduedge.api.programmes.save_programme",
			'type: "POST"',
			"programme: savedDraft.name || undefined",
			"The server did not return the saved Class identity",
			"await proxy.load(true)",
			"proxy.programmeModalOpen = false",
		):
			self.assertIn(token, fix)


if __name__ == "__main__":
	unittest.main()
