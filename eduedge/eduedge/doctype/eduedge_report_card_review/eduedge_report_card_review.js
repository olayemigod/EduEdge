frappe.ui.form.on("EduEdge Report Card Review", {
	setup(frm) {
		frm.set_query("result_publication", () => ({
			filters: { status: "Published", report_card_ready: 1 },
		}));
		frm.set_query("student", () => ({
			query: "eduedge.api.academic_operations.student_query",
			filters: {
				eduedge_school_branch: frm.doc.school_branch,
				student_group: frm.doc.student_group,
			},
		}));
	},
	async result_publication(frm) {
		if (!frm.doc.result_publication) return;
		const response = await frappe.db.get_value(
			"EduEdge Result Publication",
			frm.doc.result_publication,
			["school_branch", "student_group", "academic_year", "academic_term", "assessment_group"]
		);
		const values = response?.message || {};
		for (const [fieldname, value] of Object.entries(values)) {
			await frm.set_value(fieldname, value || null);
		}
		await frm.set_value("student", null);
	},
	refresh(frm) {
		const isDraft = frm.doc.progression_status === "Draft";
		const canApprove = ["System Manager", "EduEdge Administrator", "School Administrator", "Academic Administrator"]
			.some((role) => frappe.user_roles.includes(role));
		frm.toggle_enable(["class_teacher_comment", "progression_recommendation"], isDraft);
		frm.toggle_enable("principal_comment", isDraft && canApprove);
	},
});
