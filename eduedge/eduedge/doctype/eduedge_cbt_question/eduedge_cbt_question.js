const SCHOOL_BANK = "School Question Bank";
const PUBLIC_BANK = "EduEdge Examination Bank";

function getPublicExamAccess() {
	if (!window.__eduedgePublicExamAccessPromise) {
		window.__eduedgePublicExamAccessPromise = frappe
			.call("eduedge.api.cbt.get_public_exam_access_context")
			.then((response) => response.message || {})
			.catch((error) => {
				window.__eduedgePublicExamAccessPromise = null;
				throw error;
			});
	}
	return window.__eduedgePublicExamAccessPromise;
}

function supersededQuestionFilters(frm) {
	const filters = {
		status: ["in", ["Approved", "Retired"]],
		ownership_scope: frm.doc.ownership_scope,
		course: frm.doc.course,
	};
	if (frm.doc.ownership_scope === SCHOOL_BANK && frm.doc.school_branch) {
		filters.school_branch = frm.doc.school_branch;
	}
	return filters;
}

async function applyQuestionBankGovernance(frm) {
	const access = await getPublicExamAccess();
	const canAuthorPublic = Boolean(access.capabilities?.author?.allowed);
	frm.__can_author_public_exams = canAuthorPublic;
	frm.set_df_property(
		"ownership_scope",
		"options",
		canAuthorPublic ? `${SCHOOL_BANK}\n${PUBLIC_BANK}` : SCHOOL_BANK
	);
	if (frm.is_new() && !canAuthorPublic && frm.doc.ownership_scope !== SCHOOL_BANK) {
		await frm.set_value("ownership_scope", SCHOOL_BANK);
	}
	if (!canAuthorPublic && frm.doc.ownership_scope === PUBLIC_BANK) {
		frm.set_df_property("ownership_scope", "read_only", 1);
	}
}

function normaliseAnswerOptions(frm) {
	for (const [index, row] of (frm.doc.options || []).entries()) {
		row.option_key = (row.option_key || "").trim().toUpperCase();
		if (!String(row.option_text || "").trim() && row.option_key) {
			row.option_text = row.option_key;
		}
		if (!Number(row.display_order)) {
			row.display_order = index + 1;
		}
	}
	frm.refresh_field("options");
}

frappe.ui.form.on("EduEdge CBT Question", {
	setup(frm) {
		frm.set_query("school_branch", () => ({
			query: "eduedge.api.education.school_branch_query",
		}));
		frm.set_query("supersedes_question", () => ({ filters: supersededQuestionFilters(frm) }));
	},

	refresh(frm) {
		applyQuestionBankGovernance(frm).catch((error) => {
			console.error("Failed to resolve EduEdge public question bank access", error);
		});
	},

	validate(frm) {
		normaliseAnswerOptions(frm);
	},

	async ownership_scope(frm) {
		await frm.set_value("supersedes_question", null);
		if (frm.doc.ownership_scope !== SCHOOL_BANK) {
			await frm.set_value("school_branch", null);
		}
	},

	async school_branch(frm) {
		await frm.set_value("supersedes_question", null);
	},

	async course(frm) {
		await frm.set_value("supersedes_question", null);
	},

	async supersedes_question(frm) {
		if (!frm.doc.supersedes_question) return;
		const response = await frappe.db.get_value(
			"EduEdge CBT Question",
			frm.doc.supersedes_question,
			"version_number"
		);
		const previousVersion = Number(response?.message?.version_number || 0);
		if (previousVersion) {
			await frm.set_value("version_number", previousVersion + 1);
		}
	},
});
