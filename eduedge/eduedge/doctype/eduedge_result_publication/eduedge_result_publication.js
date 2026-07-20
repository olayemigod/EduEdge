frappe.ui.form.on("EduEdge Result Publication", {
	setup(frm) {
		frm.set_query("school_branch", () => ({
			query: "eduedge.api.education.school_branch_query",
		}));
		frm.set_query("student_group", () => ({
			query: "eduedge.api.academic_operations.student_group_query",
			filters: {
				eduedge_school_branch: frm.doc.school_branch,
				academic_year: frm.doc.academic_year,
				academic_term: frm.doc.academic_term,
			},
		}));
	},
	school_branch(frm) {
		frm.set_value("student_group", null);
	},
	academic_year(frm) {
		frm.set_value("academic_term", null);
		frm.set_value("student_group", null);
	},
	academic_term(frm) {
		frm.set_value("student_group", null);
	},
});
