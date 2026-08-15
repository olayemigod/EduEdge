from pathlib import Path
import ast
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstitutionTypeProgrammeTerminologyContract(unittest.TestCase):
	def test_registry_defaults_cover_department_programme_and_offering(self):
		defaults = (APP / "education" / "institution_type_defaults.py").read_text()
		self.assertIn('"department",', defaults)
		for token in (
			'"department": ("School Section", "School Sections")',
			'"programme": ("Class", "Classes")',
			'"programme_offering": ("Class Intake", "Class Intakes")',
			'"department": ("Department", "Departments")',
			'"programme_offering": ("Programme Intake", "Programme Intakes")',
			'"department": ("Training Category", "Training Categories")',
			'"programme_offering": ("Intake", "Intakes")',
		):
			self.assertIn(token, defaults)

	def test_runtime_hierarchy_terms_match_native_doctype_roles(self):
		service = (APP / "services" / "institution_context.py").read_text()
		ast.parse(service)
		for token in (
			'resolved["department"] = _term_row("School Section", "School Sections"',
			'resolved["programme"] = _term_row("Class", "Classes"',
			'resolved["programme_offering"] = _term_row("Class Intake", "Class Intakes"',
			'resolved["academic_level"] = _term_row("Class Level", "Class Levels"',
			'resolved["academic_section"] = _term_row("Faculty / School", "Faculties / Schools"',
			'resolved["department"] = _term_row("Department", "Departments"',
			'resolved["department"] = _term_row("Training Category", "Training Categories"',
		):
			self.assertIn(token, service)
		self.assertNotIn('resolved["programme"] = _term_row("Programme", "Programmes", sequence=30)\n\telif code == "TERTIARY"', service)

	def test_programme_api_returns_permission_checked_institution_contexts(self):
		api = (APP / "api" / "programmes.py").read_text()
		ast.parse(api)
		for token in (
			'def get_programme_terminology(',
			'_assert_institution_access(institution)',
			'row["context"] = context',
			'row["institution_type_name"]',
			'get_effective_institution_context(institution=row.name)',
		):
			self.assertIn(token, api)

	def test_programme_edgesuite_page_uses_selected_and_draft_contexts(self):
		component = (APP / "public" / "js" / "eduedge_programmes" / "EduEdgeProgrammes.vue").read_text()
		for token in (
			"mixedInstitutionView",
			"pageContext()",
			"draftContext()",
			'"Class / Programme"',
			'"Classes / Programmes"',
			"editorProgrammeSingular",
			"editorDepartmentSingular",
			"institution.institution_type_name",
			"@change=\"draftInstitutionChanged\"",
		):
			self.assertIn(token, component)

	def test_offering_editor_follows_selected_branch_context_without_term_identity(self):
		component = (APP / "public" / "js" / "eduedge_programme_offerings" / "EduEdgeProgrammeOfferings.vue").read_text()
		for token in (
			"draftContext: {}",
			"editorProgrammeSingular",
			"editorOfferingSingular",
			"editorDepartmentSingular",
			"editorAcademicYearSingular",
			"this.draftContext = result.active_context || this.activeContext",
			"Full Academic Session",
			"Not part of Programme Offering identity",
		):
			self.assertIn(token, component)
		self.assertNotIn("editorAcademicTermSingular", component)
		self.assertNotIn('v-model="draft.academic_term"', component)

	def test_native_program_form_uses_document_institution_context(self):
		script = (APP / "public" / "js" / "education" / "program.js").read_text()
		for token in (
			"applyProgramTerminology",
			"eduedge.api.programmes.get_programme_terminology",
			"frm.doc.eduedge_institution",
			'frm.set_df_property("program_name", "label", `${programme} Name`)',
			'frm.set_df_property("department", "label", department)',
			"updates.department = null",
		):
			self.assertIn(token, script)

	def test_technical_doctype_identity_remains_stable(self):
		programmes = (APP / "api" / "programmes.py").read_text()
		offerings = (APP / "eduedge" / "doctype" / "eduedge_program_offering" / "eduedge_program_offering.json").read_text()
		self.assertIn('"Program"', programmes)
		self.assertIn('"name": "EduEdge Program Offering"', offerings)
		self.assertNotIn("rename_doc", programmes)


if __name__ == "__main__":
	unittest.main()
