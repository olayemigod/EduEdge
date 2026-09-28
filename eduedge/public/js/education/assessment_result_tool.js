frappe.ui.form.on("Assessment Result Tool", {
	setup(frm) {
		frm.set_query("assessment_plan", () => ({
			query: "eduedge.api.assessment_assignment_options.assessment_result_plan_query",
			filters: {},
		}));
	},
});
