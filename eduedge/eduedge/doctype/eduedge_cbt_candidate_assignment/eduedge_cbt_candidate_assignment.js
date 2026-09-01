async function copyCandidateLaunchLink(link, statusElement) {
	try {
		await navigator.clipboard.writeText(link);
		statusElement.textContent = __("Candidate link copied.");
	} catch (error) {
		statusElement.textContent = __("Copy the link manually from the field above.");
	}
}

function showCandidateLaunchDialog(result) {
	const dialog = new frappe.ui.Dialog({
		title: __("Candidate Examination Link"),
		fields: [
			{
				fieldname: "launch_notice",
				fieldtype: "HTML",
				options: `<div class="alert alert-warning mb-3">${frappe.utils.escape_html(result.launch_notice || "")}</div>`,
			},
			{
				fieldname: "attempt",
				fieldtype: "Data",
				label: __("Attempt"),
				read_only: 1,
				default: result.attempt,
			},
			{
				fieldname: "launch_url",
				fieldtype: "Small Text",
				label: __("Secure Candidate Link"),
				read_only: 1,
				default: result.launch_url,
			},
			{
				fieldname: "link_status",
				fieldtype: "HTML",
				options: '<p class="text-muted small mb-0" aria-live="polite"></p>',
			},
		],
		primary_action_label: __("Copy Candidate Link"),
		primary_action() {
			const statusElement = dialog.fields_dict.link_status.wrapper.querySelector("p");
			copyCandidateLaunchLink(result.launch_url, statusElement);
		},
		secondary_action_label: __("Open Candidate Page"),
		secondary_action() {
			window.open(result.launch_url, "_blank", "noopener,noreferrer");
		},
	});
	dialog.show();
}

async function prepareCandidateLaunch(frm) {
	frm.disable_save();
	try {
		const response = await frappe.call({
			method: "eduedge.cbt.candidate_launch.prepare_candidate_launch",
			args: { candidate_assignment: frm.doc.name },
			freeze: true,
			freeze_message: __("Preparing secure candidate attempt…"),
		});
		if (response.message) showCandidateLaunchDialog(response.message);
	} finally {
		frm.enable_save();
	}
}

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

	refresh(frm) {
		if (
			!frm.is_new() &&
			frm.doc.assignment_status === "Released" &&
			frm.doc.exam_scope === "School Examination" &&
			frappe.model.can_write(frm.doctype)
		) {
			frm.add_custom_button(__("Prepare Candidate Attempt"), () => prepareCandidateLaunch(frm), __("CBT"));
		}
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
