function set_cbt_queries(frm) {
	frm.set_query("school_branch", () => ({ filters: { enabled: 1 } }));
	frm.set_query("student_group", () => {
		const filters = {
			disabled: 0,
			eduedge_school_branch: frm.doc.school_branch || "",
			academic_year: frm.doc.academic_year || "",
		};
		if (frm.doc.academic_term) filters.academic_term = ["in", [frm.doc.academic_term, ""]];
		return { filters };
	});
	frm.set_query("question", "questions", () => ({
		filters: {
			school_branch: frm.doc.school_branch || "",
			course: frm.doc.course || "",
			is_active: 1,
		},
	}));
}

function clear_exam_scope_dependants(frm, { clear_group = false, clear_questions = false } = {}) {
	if (clear_group) frm.set_value("student_group", null);
	if (clear_questions && (frm.doc.questions || []).length) {
		frm.clear_table("questions");
		frm.refresh_field("questions");
	}
}

async function run_cbt_exam_action(frm, method, success_message) {
	await frappe.call({
		method: `eduedge.api.cbt.${method}`,
		args: { exam: frm.doc.name },
		freeze: true,
		freeze_message: __("Updating CBT Exam..."),
	});
	frappe.show_alert({ message: __(success_message), indicator: "green" });
	await frm.reload_doc();
}

frappe.ui.form.on("EduEdge CBT Exam", {
	setup(frm) {
		set_cbt_queries(frm);
	},
	refresh(frm) {
		set_cbt_queries(frm);
		if (frm.is_new()) return;
		if (frm.doc.status === "Draft") {
			frm.add_custom_button(__("Schedule Exam"), () =>
				run_cbt_exam_action(frm, "schedule_exam", "CBT Exam scheduled"),
			);
		}
		if (frm.doc.status === "Scheduled") {
			frm.add_custom_button(__("Activate Exam"), () =>
				run_cbt_exam_action(frm, "activate_exam", "CBT Exam activated"),
			);
			frm.add_custom_button(__("Cancel Exam"), () =>
				run_cbt_exam_action(frm, "close_exam", "CBT Exam cancelled"),
			);
		}
		if (frm.doc.status === "Active") {
			frm.add_custom_button(__("Close Exam"), () =>
				run_cbt_exam_action(frm, "close_exam", "CBT Exam closed"),
			);
		}
	},
	school_branch(frm) {
		clear_exam_scope_dependants(frm, { clear_group: true, clear_questions: true });
	},
	course(frm) {
		clear_exam_scope_dependants(frm, { clear_questions: true });
	},
	academic_year(frm) {
		clear_exam_scope_dependants(frm, { clear_group: true });
	},
	academic_term(frm) {
		clear_exam_scope_dependants(frm, { clear_group: true });
	},
});
