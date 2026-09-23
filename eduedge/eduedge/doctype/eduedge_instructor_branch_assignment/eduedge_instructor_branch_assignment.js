const EMPTY_INSTITUTION = "__eduedge_no_institution__";

function lockEligibilityIdentity(frm) {
	const locked = !frm.is_new();
	frm.set_df_property("instructor", "read_only", locked ? 1 : 0);
	frm.set_df_property("school_branch", "read_only", locked ? 1 : 0);
}

async function refreshInstructorInstitution(frm, { clearBranch = false } = {}) {
	if (clearBranch && frm.doc.school_branch) {
		await frm.set_value("school_branch", null);
	}

	frm.__eduedge_instructor_institution = EMPTY_INSTITUTION;
	if (!frm.doc.instructor) {
		frm.refresh_field("school_branch");
		return;
	}

	const response = await frappe.db.get_value(
		"Instructor",
		frm.doc.instructor,
		"eduedge_institution",
	);
	const institution = response?.message?.eduedge_institution || "";
	frm.__eduedge_instructor_institution = institution || EMPTY_INSTITUTION;

	if (frm.is_new() && frm.doc.school_branch && institution) {
		const branchResponse = await frappe.db.get_value(
			"EduEdge School Branch",
			frm.doc.school_branch,
			"institution",
		);
		if (
			branchResponse?.message?.institution
			&& branchResponse.message.institution !== institution
		) {
			await frm.set_value("school_branch", null);
		}
	}
	frm.refresh_field("school_branch");
}

frappe.ui.form.on("EduEdge Instructor Branch Assignment", {
	setup(frm) {
		frm.set_query("school_branch", () => ({
			query: "eduedge.api.education.school_branch_query",
			filters: {
				institution: frm.__eduedge_instructor_institution || EMPTY_INSTITUTION,
			},
		}));
		frm.set_query("instructor", () => ({
			query: "eduedge.api.instructor_branch_eligibility.instructor_branch_eligibility_instructor_query",
		}));
	},

	refresh(frm) {
		lockEligibilityIdentity(frm);
		void refreshInstructorInstitution(frm);
	},

	instructor(frm) {
		if (!frm.is_new()) return;
		void refreshInstructorInstitution(frm, { clearBranch: true });
	},
});
