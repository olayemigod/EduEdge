frappe.ui.form.on("EduEdge CBT Candidate Assignment", {
	setup(frm) {
		frm.set_query("exam_schedule", () => ({
			filters: { status: ["in", ["Draft", "Ready"]] },
		}));
		frm.set_query("student", () => {
			const filters = {};
			if (frm.doc.school_branch) {
				filters.eduedge_school_branch = frm.doc.school_branch;
			}
			return { filters };
		});
	},

	exam_schedule(frm) {
		if (!frm.doc.exam_schedule) {
			frm.set_value({
				exam_template: null,
				exam_scope: null,
				school_branch: null,
				course: null,
				student_group: null,
				candidate_type: "EduEdge Student",
			});
			return;
		}
		frappe.db.get_value(
			"EduEdge CBT Exam Schedule",
			frm.doc.exam_schedule,
			["exam_template", "exam_scope", "school_branch", "course"],
		).then(({ message }) => {
			if (!message) return;
			frm.set_value({
				exam_template: message.exam_template,
				exam_scope: message.exam_scope,
				school_branch: message.school_branch,
				course: message.course,
				candidate_type: message.exam_scope === "EduEdge Public Examination"
					? "Public Candidate Reference"
					: "EduEdge Student",
				student: null,
				public_candidate_reference: null,
				candidate_name: null,
			});
		});
	},
});
