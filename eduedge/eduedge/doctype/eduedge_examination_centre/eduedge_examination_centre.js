const SCHOOL_CENTRE = "School Examination Centre";
const PUBLIC_CENTRE = "EduEdge Exam Centre";

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

async function applyCentreGovernance(frm) {
	const access = await getPublicExamAccess();
	const canAuthorPublic = Boolean(access.capabilities?.author?.allowed);
	frm.__can_author_public_exams = canAuthorPublic;
	frm.set_df_property(
		"centre_type",
		"options",
		canAuthorPublic ? `${SCHOOL_CENTRE}\n${PUBLIC_CENTRE}` : SCHOOL_CENTRE
	);
	if (frm.is_new() && !canAuthorPublic && frm.doc.centre_type !== SCHOOL_CENTRE) {
		await frm.set_value("centre_type", SCHOOL_CENTRE);
	}
	if (!canAuthorPublic && frm.doc.centre_type === PUBLIC_CENTRE) {
		frm.set_df_property("centre_type", "read_only", 1);
	}
}

frappe.ui.form.on("EduEdge Examination Centre", {
	setup(frm) {
		frm.set_query("school_branch", () => ({
			query: "eduedge.api.education.school_branch_query",
		}));
	},

	refresh(frm) {
		applyCentreGovernance(frm).catch((error) => {
			console.error("Failed to resolve EduEdge public exam centre access", error);
		});
		if (!frm.is_new()) {
			frm.dashboard.set_headline(
				__("Examination Centres are saved master records. Use Centre Status instead of Submit or Cancel.")
			);
		}
	},

	async centre_type(frm) {
		if (frm.doc.centre_type === SCHOOL_CENTRE) {
			await frm.set_value("allow_public_registration", 0);
		} else {
			await frm.set_value("school_branch", null);
		}
	},
});
