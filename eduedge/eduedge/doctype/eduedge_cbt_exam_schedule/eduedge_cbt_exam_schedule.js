const CBT_SCHEDULE_LOCKED_STATUSES = ["Active", "Suspended", "Completed", "Cancelled"];
const CBT_SCHEDULE_POLICY_FIELDS = [
	"exam_template",
	"examination_centre",
	"scheduled_start",
	"check_in_opens_at",
	"require_candidate_check_in",
	"candidate_start_mode",
	"allow_late_entry",
	"late_entry_grace_minutes",
	"primary_invigilator",
	"allow_invigilator_time_extension",
	"maximum_time_extension_minutes",
	"allow_invigilator_force_submit",
];

frappe.ui.form.on("EduEdge CBT Exam Schedule", {
	setup(frm) {
		frm.set_query("exam_template", () => ({ filters: { status: "Approved" } }));
		frm.set_query("examination_centre", () => {
			const filters = { centre_status: "Active" };
			if (frm.doc.exam_scope === "School Examination" && frm.doc.school_branch) {
				filters.centre_type = "School Examination Centre";
				filters.school_branch = frm.doc.school_branch;
			} else if (frm.doc.exam_scope === "EduEdge Public Examination") {
				filters.centre_type = "EduEdge Exam Centre";
			}
			return { filters };
		});
		frm.set_query("primary_invigilator", () => ({
			filters: { enabled: 1, user_type: "System User" },
		}));
	},

	refresh(frm) {
		const locked = CBT_SCHEDULE_LOCKED_STATUSES.includes(frm.doc.status);
		CBT_SCHEDULE_POLICY_FIELDS.forEach((fieldname) => frm.toggle_enable(fieldname, !locked));
	},

	exam_template(frm) {
		if (!frm.doc.exam_template) {
			frm.set_value({
				exam_scope: null,
				school_branch: null,
				course: null,
				examination_centre: null,
			});
			return;
		}
		frappe.db.get_value(
			"EduEdge CBT Exam Template",
			frm.doc.exam_template,
			["exam_scope", "school_branch", "course", "default_examination_centre"],
		).then(({ message }) => {
			if (!message) return;
			frm.set_value({
				exam_scope: message.exam_scope,
				school_branch: message.school_branch,
				course: message.course,
				examination_centre: message.default_examination_centre || null,
			});
		});
	},
});
