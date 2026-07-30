from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestNativeIdentityAuditContract(unittest.TestCase):
	def test_collision_prone_native_masters_have_friendly_identity_fields(self):
		fields = (APP / "education" / "academic_fields.py").read_text(encoding="utf-8")
		identity = (APP / "education" / "native_identity.py").read_text(encoding="utf-8")
		for doctype in ("Department", "Program", "Course", "Student Group", "Student Batch Name"):
			self.assertIn(f'"{doctype}":', fields)
			self.assertIn(f'"{doctype}":', identity)
		self.assertIn('DISPLAY_FIELD = "eduedge_display_name"', fields)
		self.assertIn('"title_field", DISPLAY_FIELD', identity)
		self.assertIn('"show_title_field_in_link", "1"', identity)
		self.assertIn("_available_native_name", identity)
		self.assertIn("select name from `tabDocType`", identity)

	def test_friendly_names_are_unique_only_inside_their_academic_scope(self):
		identity = (APP / "education" / "native_identity.py").read_text(encoding="utf-8")
		self.assertIn("_validate_friendly_scope", identity)
		self.assertIn("INSTITUTION_FIELD", identity)
		for fieldname in ("BRANCH_FIELD", '"program"', '"academic_year"', '"academic_term"'):
			self.assertIn(fieldname, identity)
		self.assertIn("DuplicateEntryError", identity)

	def test_native_identity_hooks_preserve_technical_names(self):
		hooks = (APP / "hooks.py").read_text(encoding="utf-8")
		identity = (APP / "education" / "native_identity.py").read_text(encoding="utf-8")
		for doctype in ("Department", "Program", "Course", "Student Group", "Student Batch Name"):
			self.assertIn(f'"{doctype}": {{', hooks)
		self.assertIn('"before_naming": _NATIVE_NAMING', hooks)
		self.assertIn("technical identity", identity)
		self.assertIn("old_source", identity)
		self.assertIn("new_source", identity)

	def test_department_global_root_and_friendly_quick_edit_are_safe(self):
		hierarchy = (APP / "education" / "academic_hierarchy.py").read_text(encoding="utf-8")
		mutations = (APP / "api" / "academic_foundation_mutations.py").read_text(encoding="utf-8")
		hooks = (APP / "hooks.py").read_text(encoding="utf-8")
		self.assertIn("get_root_of", hierarchy)
		self.assertIn("is_framework_root", hierarchy)
		self.assertIn("doc.set(DISPLAY_FIELD, friendly)", mutations)
		self.assertIn("doc.department_name = friendly", mutations)
		self.assertIn("academic_foundation_mutations.save_department", hooks)

	def test_programme_quick_edit_uses_display_name_not_technical_identity(self):
		api = (APP / "api" / "programmes.py").read_text(encoding="utf-8")
		hooks = (APP / "hooks.py").read_text(encoding="utf-8")
		self.assertIn("doc.set(DISPLAY_FIELD, friendly)", api)
		self.assertIn("doc.program_name = friendly", api)
		self.assertIn('"technical_name": doc.program_name', api)
		self.assertIn("programmes_display.get_programmes_page", hooks)

	def test_direct_attendance_requires_exact_schedule_identity(self):
		attendance = (APP / "education" / "attendance_validation.py").read_text(encoding="utf-8")
		branching = (APP / "education" / "branching.py").read_text(encoding="utf-8")
		self.assertIn("_resolve_exact_schedule", attendance)
		self.assertIn("len(matches) == 1", attendance)
		self.assertIn("len(matches) > 1", attendance)
		self.assertIn("Select the exact scheduled session", attendance)
		self.assertIn("attendance_validation import before_validate_student_attendance", branching)

	def test_profile_photo_validation_checks_actual_bytes(self):
		uploads = (APP / "api" / "profile_uploads.py").read_text(encoding="utf-8")
		self.assertIn("import filetype", uploads)
		self.assertIn("filetype.guess(content)", uploads)
		self.assertIn("detected_mimetype", uploads)
		self.assertIn("Only genuine JPG, PNG, and WebP images are allowed", uploads)

	def test_read_pages_keep_link_values_and_present_friendly_labels(self):
		hooks = (APP / "hooks.py").read_text(encoding="utf-8")
		foundation = (APP / "api" / "academic_foundation_display.py").read_text(encoding="utf-8")
		operations = (APP / "api" / "academic_operations_display.py").read_text(encoding="utf-8")
		offerings = (APP / "api" / "programme_offerings_display.py").read_text(encoding="utf-8")
		programmes = (APP / "api" / "programmes_display.py").read_text(encoding="utf-8")
		component = (APP / "public" / "js" / "eduedge_academic_operations" / "EduEdgeAcademicOperations.vue").read_text(encoding="utf-8")
		for token in (
			"academic_foundation_display.get_academic_foundation",
			"academic_operations_display.get_operations_context",
			"programme_offerings_display.get_programme_offerings_page",
			"programmes_display.get_programmes_page",
		):
			self.assertIn(token, hooks)
		self.assertIn("annotate_master_rows", foundation)
		self.assertIn("annotate_link", operations)
		self.assertIn("annotate_link", offerings)
		self.assertIn("annotate_master_rows", programmes)
		self.assertIn("course_display_name", component)
		self.assertIn("student_group_display_name", component)

	def test_legacy_fields_are_read_only_and_runtime_typo_is_absent(self):
		fields = (APP / "education" / "academic_fields.py").read_text(encoding="utf-8")
		self.assertIn('"read_only": 1', fields)
		self.assertNotIn("ACAMIC_SECTION_FIELD", fields)
		self.assertIn("program_meta.has_field(ACADEMIC_SECTION_FIELD)", fields)


if __name__ == "__main__":
	unittest.main()
