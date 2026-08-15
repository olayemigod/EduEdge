from pathlib import Path
import ast
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestProgrammeOfferingInstitutionContextContract(unittest.TestCase):
	def test_backend_supports_explicit_initial_active_branch_only(self):
		api = (APP / "api" / "programme_offerings_safe.py").read_text(encoding="utf-8")
		ast.parse(api)
		self.assertIn("use_active_branch", api)
		self.assertIn("if not resolved_branch and not resolved_institution and cint(use_active_branch)", api)
		self.assertIn("get_current_school_branch()", api)
		self.assertIn('"school_branch": branch', api)
		self.assertIn('"institution": institution', api)

	def test_backend_filters_context_options_by_institution(self):
		api = (APP / "api" / "programme_offerings_safe.py").read_text(encoding="utf-8")
		for token in (
			"def _list_institutions()",
			'frappe.has_permission("EduEdge Institution", "read")',
			"get_allowed_school_branches(institution=institution)",
			"program_filters = {INSTITUTION_FIELD: institution}",
			'"institutions": _list_institutions()',
			'"calendar_context": calendar_context',
		):
			self.assertIn(token, api)

	def test_backend_exposes_calendar_backed_sessions_and_terms_for_downstream_operations(self):
		api = (APP / "api" / "programme_offerings_safe.py").read_text(encoding="utf-8")
		for token in (
			"def _institution_academic_years",
			"def _institution_calendar_terms",
			"def _institution_calendar_context",
			'"calendar_start_date": calendar.start_date',
			'"calendar_end_date": calendar.end_date',
			'"calendar": row.parent',
		):
			self.assertIn(token, api)

	def test_save_rejects_branch_institution_mismatch_server_side(self):
		api = (APP / "api" / "programme_offerings_safe.py").read_text(encoding="utf-8")
		for token in (
			'_("Selected Branch does not belong to the selected Institution.")',
			"resolved_branch, resolved_institution = _resolve_page_context(",
			'branch=school_branch',
			'institution=institution',
			'@frappe.whitelist(methods=["POST"])',
			"assert_institution_calendar_context(",
		):
			self.assertIn(token, api)
		self.assertNotIn("ignore_permissions=True", api)
		self.assertNotIn("frappe.db.set_value", api)

	def test_page_is_institution_first_and_cascades_sessional_children(self):
		component = (APP / "public" / "js" / "eduedge_programme_offerings" / "EduEdgeProgrammeOfferings.vue").read_text(encoding="utf-8")
		institution_position = component.index('<span>Institution</span>')
		branch_position = component.index('<span>Branch / Campus</span>')
		self.assertLess(institution_position, branch_position)
		for token in (
			'@change="filterInstitutionChanged"',
			'@change="draftInstitutionChanged"',
			"this.filters.branch = \"\"",
			"this.filters.department = \"\"",
			"this.filters.program = \"\"",
			"this.filters.academic_year = \"\"",
			"this.draft.school_branch = \"\"",
			"this.draft.department = \"\"",
			"this.draft.program = \"\"",
			"this.draft.academic_year = \"\"",
		):
			self.assertIn(token, component)
		self.assertNotIn('v-model="filters.academic_term"', component)
		self.assertNotIn('v-model="draft.academic_term"', component)
		self.assertIn("Not part of Programme Offering identity", component)

	def test_page_displays_resolved_calendar_and_preserves_identity_lock(self):
		component = (APP / "public" / "js" / "eduedge_programme_offerings" / "EduEdgeProgrammeOfferings.vue").read_text(encoding="utf-8")
		for token in (
			"Resolved Institution Calendar",
			"filterCalendar()",
			"draftCalendar()",
			"calendarRange(calendar)",
			"identityFieldsLocked",
			':disabled="identityFieldsLocked"',
			"Create a new {{ editorOfferingSingular }} to change its Branch",
		):
			self.assertIn(token, component)

	def test_page_uses_active_branch_only_on_first_load(self):
		component = (APP / "public" / "js" / "eduedge_programme_offerings" / "EduEdgeProgrammeOfferings.vue").read_text(encoding="utf-8")
		self.assertIn("mounted() { this.load(true, true); }", component)
		self.assertIn("use_active_branch: useActiveBranch ? 1 : 0", component)
		self.assertIn("applyFilters() { this.load(true, false); }", component)
		self.assertIn("await this.load(true, false)", component)


if __name__ == "__main__":
	unittest.main()
