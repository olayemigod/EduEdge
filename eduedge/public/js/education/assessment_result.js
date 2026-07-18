frappe.ui.form.on("Assessment Result", {
	setup(frm) {
		frm.set_query("assessment_plan", () => ({
			filters: {
				eduedge_school_branch: frm.doc.eduedge_school_branch,
				docstatus: 1,
			},
		}));
		frm.set_query("student", () => ({
			query: "eduedge.api.academic_operations.student_query",
			filters: {
				eduedge_school_branch: frm.doc.eduedge_school_branch,
				student_group: frm.doc.student_group,
			},
		}));
	},
	assessment_plan(frm) {
		frm.set_value("student", null);
	},
});
