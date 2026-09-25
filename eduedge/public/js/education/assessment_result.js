frappe.ui.form.on("Assessment Result", {
	setup(frm) {
		frm.set_query("assessment_plan", () => ({
			query: "eduedge.api.assessment_assignment_options.assessment_result_plan_query",
			filters: {
				eduedge_school_branch: frm.doc.eduedge_school_branch,
			},
		}));
		frm.set_query("student", () => ({
			query: "eduedge.api.assessment_assignment_options.assessment_result_student_query",
			filters: {
				eduedge_school_branch: frm.doc.eduedge_school_branch,
				assessment_plan: frm.doc.assessment_plan,
			},
		}));
	},
	assessment_plan(frm) {
		frm.set_value("student", null);
	},
});
