function instructorInstitutionFilters(frm) {
	return { institution: frm.doc.eduedge_institution || "" };
}

frappe.ui.form.on("Instructor", {
	setup(frm) {
		frm.set_query("department", () => ({
			query: "eduedge.api.instructor_profiles.instructor_profile_department_query",
			filters: instructorInstitutionFilters(frm),
		}));
		frm.set_query("employee", () => ({
			query: "eduedge.api.instructor_profiles.instructor_profile_employee_query",
			filters: instructorInstitutionFilters(frm),
		}));
	},

	async eduedge_institution(frm) {
		if (frm.is_new() || frm.doc.__unsaved) {
			await frm.set_value({ department: null, employee: null });
			return;
		}
		if (frm.doc.department || frm.doc.employee) {
			await frm.set_value({ department: null, employee: null });
		}
	},
});
