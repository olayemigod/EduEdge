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

	def test_read_only_programme_user_gets_no_injected_mutation_controls(self):
		ui = (APP / "public" / "js" / "eduedge_programmes" / "curriculum_governance.js").read_text(encoding="utf-8")
		for token in (
			"function canManageCurriculum(proxy)",
			"Boolean(proxy?.canWrite)",
			"if (!canManageCurriculum(proxy))",
			"removeConfiguredControls(root)",
			"removeAvailableControls(root)",
			'.eduedge-curriculum-governance-actions',
			'.eduedge-curriculum-add-governance',
		):
			self.assertIn(token, ui)

	def test_available_subject_action_refreshes_after_each_selection_change(self):
		ui = (APP / "public" / "js" / "eduedge_programmes" / "curriculum_governance.js").read_text(encoding="utf-8")
		for token in (
			"selectedCourses(proxy)",
			"syncAvailableControls",
			"eduedge-curriculum-add-selected",
			"if (existingControls)",
			"syncAvailableControls(existingControls, proxy)",
			"add.disabled = !count",
			'root.addEventListener("change", schedule, true)',
		):
			self.assertIn(token, ui)

	def test_class_modal_save_uses_explicit_post_and_server_identity(self):
		entry = (APP / "public" / "js" / "eduedge_programmes.bundle.js").read_text(encoding="utf-8")
		fix = (APP / "public" / "js" / "eduedge_programmes" / "programme_modal_save_fix.js").read_text(encoding="utf-8")
		component = (APP / "public" / "js" / "eduedge_programmes" / "EduEdgeProgrammes.vue").read_text(encoding="utf-8")
		master = (APP / "api" / "programme_master.py").read_text(encoding="utf-8")
		for token in (
			"installProgrammeModalSaveFix",
			"programme_modal_save_fix",
			"installProgrammeModalSaveFix(proxy)",
		):
			self.assertIn(token, entry)
		for token in (
			"eduedge.api.programme_master.save_programme",
			'type: "POST"',
			"programme: savedDraft.name || undefined",
			"program_name: savedDraft.program_name",
			"The server did not return the saved Class identity",
			"await proxy.load(true)",
			"proxy.programmeModalOpen = false",
		):
			self.assertIn(token, fix)
		self.assertIn('v-model.trim="draft.program_name"', component)
		for token in (
			'@frappe.whitelist(methods=["POST"])',
			"from frappe.model.rename_doc import rename_doc",
			"_assert_programme_name_available",
			'rename_doc(',
			'"Program",',
			"force=False",
			"merge=False",
			"ignore_permissions=False",
			"show_alert=False",
			"doc.program_name = requested_name",
			'"renamed_from": renamed_from',
		):
			self.assertIn(token, master)
		self.assertNotIn("ignore_permissions=True", master)
		self.assertNotIn("frappe.db.set_value", master)
		self.assertNotIn("frappe.delete_doc", master)


if __name__ == "__main__":
	unittest.main()
