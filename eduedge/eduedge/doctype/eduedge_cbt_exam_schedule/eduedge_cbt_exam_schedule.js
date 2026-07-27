const CBT_SCHEDULE_LOCKED_STATUSES = ["Active", "Suspended", "Completed", "Cancelled"];
const CBT_SCHEDULE_POLICY_FIELDS = [
	"exam_template",
	"assessment_plan",
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

function runResultSyncAction(frm, method, successMessage) {
	frappe.call({
		method,
		args: { exam_schedule: frm.doc.name },
		freeze: true,
		freeze_message: __("Validating approved CBT results..."),
		callback({ message }) {
			if (!message) return;
			frappe.show_alert({ message: successMessage(message), indicator: "green" }, 8);
			frm.reload_doc();
		},
	});
}

frappe.ui.form.on("EduEdge CBT Exam Schedule", {
	setup(frm) {
		frm.set_query("exam_template", () => ({ filters: { status: "Approved" } }));
		frm.set_query("assessment_plan", () => {
			const filters = { docstatus: 1 };
			if (frm.doc.school_branch) filters.eduedge_school_branch = frm.doc.school_branch;
			if (frm.doc.course) filters.course = frm.doc.course;
			if (frm.doc.student_group) filters.student_group = frm.doc.student_group;
			if (frm.doc.academic_year) filters.academic_year = frm.doc.academic_year;
			if (frm.doc.academic_term) filters.academic_term = frm.doc.academic_term;
			if (frm.doc.assessment_group) filters.assessment_group = frm.doc.assessment_group;
			return { filters };
		});
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

		if (
			!frm.is_new() &&
			frm.doc.exam_scope === "School Examination" &&
			frm.doc.status === "Completed" &&
			frm.doc.assessment_plan
		) {
			frm.add_custom_button(
				__("Prepare Assessment Result Drafts"),
				() =>
					runResultSyncAction(
						frm,
						"eduedge.cbt.result_sync.prepare_schedule_assessment_results",
						(message) =>
							__("Prepared {0} draft result(s); {1} already prepared.", [
								message.prepared_count || 0,
								message.existing_count || 0,
							]),
					),
				__("CBT Results"),
			);
			frm.add_custom_button(
				__("Submit Prepared Assessment Results"),
				() =>
					runResultSyncAction(
						frm,
						"eduedge.cbt.result_sync.submit_schedule_assessment_results",
						(message) =>
							__("Submitted {0} assessment result(s); {1} were already submitted.", [
								message.submitted_count || 0,
								message.existing_submitted_count || 0,
							]),
					),
				__("CBT Results"),
			);
		}
	},

	exam_template(frm) {
		frm.set_value("assessment_plan", null);
		if (!frm.doc.exam_template) {
			frm.set_value({
				exam_scope: null,
				school_branch: null,
				course: null,
				student_group: null,
				academic_year: null,
				academic_term: null,
				assessment_group: null,
				maximum_assessment_score: 0,
				examination_centre: null,
			});
			return;
		}
		frappe.db.get_value(
			"EduEdge CBT Exam Template",
			frm.doc.exam_template,
			[
				"exam_scope",
				"school_branch",
				"course",
				"student_group",
				"academic_year",
				"academic_term",
				"assessment_group",
				"default_examination_centre",
			],
		).then(({ message }) => {
			if (!message) return;
			frm.set_value({
				exam_scope: message.exam_scope,
				school_branch: message.school_branch,
				course: message.course,
				student_group: message.student_group,
				academic_year: message.academic_year,
				academic_term: message.academic_term,
				assessment_group: message.assessment_group,
				maximum_assessment_score: 0,
				examination_centre: message.default_examination_centre || null,
			});
		});
	},

	assessment_plan(frm) {
		if (!frm.doc.assessment_plan) {
			frm.set_value("maximum_assessment_score", 0);
			return;
		}
		frappe.db.get_value(
			"Assessment Plan",
			frm.doc.assessment_plan,
			["student_group", "academic_year", "academic_term", "assessment_group", "maximum_assessment_score"],
		).then(({ message }) => {
			if (!message) return;
			frm.set_value({
				student_group: message.student_group,
				academic_year: message.academic_year,
				academic_term: message.academic_term,
				assessment_group: message.assessment_group,
				maximum_assessment_score: message.maximum_assessment_score,
			});
		});
	},
});
