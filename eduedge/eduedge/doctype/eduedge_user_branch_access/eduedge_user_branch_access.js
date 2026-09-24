async function applyAccessScopeOptions(frm) {
	const response = await frappe.call("eduedge.api.user_branch_access.get_user_branch_access_authoring_context");
	const levels = response.message?.access_levels || [];
	frm.set_df_property("access_scope", "options", levels.join("\n"));
	if (frm.is_new() && levels.length && !levels.includes(frm.doc.access_scope)) {
		await frm.set_value("access_scope", levels[levels.length - 1]);
	}
}

frappe.ui.form.on("EduEdge User Branch Access", {
	setup(frm) {
		frm.set_query("user", () => ({
			query: "eduedge.api.user_branch_access.user_branch_access_user_query",
			filters: { company: frm.doc.company },
		}));
		frm.set_query("company", () => ({
			query: "eduedge.api.user_branch_access.user_branch_access_company_query",
			filters: { access_scope: frm.doc.access_scope || "Branch" },
		}));
		frm.set_query("institution", () => ({
			query: "eduedge.api.user_branch_access.user_branch_access_institution_query",
			filters: {
				company: frm.doc.company,
				access_scope: frm.doc.access_scope || "Branch",
			},
		}));
		frm.set_query("school_branch", () => ({
			query: "eduedge.api.education.school_branch_query",
			filters: {
				company: frm.doc.company,
				institution: frm.doc.institution,
			},
		}));
	},

	refresh(frm) {
		applyAccessScopeOptions(frm);
		const scope = frm.doc.access_scope || (frm.doc.hq_all_branch_access ? "Company" : "Branch");
		frm.toggle_reqd("institution", ["Institution", "Branch"].includes(scope));
		frm.toggle_reqd("school_branch", scope === "Branch");
		frm.toggle_display("institution", scope !== "Company");
		frm.toggle_display("school_branch", scope === "Branch");
		frm.toggle_display("branch_name", scope === "Branch");
		frm.toggle_display("is_default_branch", scope === "Branch");
		frm.toggle_display("can_switch_branch", scope === "Branch");
		frm.toggle_enable("institution", scope !== "Company");
	},

	access_scope(frm) {
		const scope = frm.doc.access_scope;
		if (scope === "Company") {
			frm.set_value({
				institution: null,
				school_branch: null,
				is_default_branch: 0,
				can_switch_branch: 1,
			});
		} else if (scope === "Institution") {
			frm.set_value({
				school_branch: null,
				is_default_branch: 0,
				can_switch_branch: 1,
			});
		}
		frm.trigger("refresh");
	},

	company(frm) {
		if (frm.doc.institution) frm.set_value("institution", null);
		if (frm.doc.school_branch) frm.set_value("school_branch", null);
	},

	institution(frm) {
		if (frm.doc.school_branch) frm.set_value("school_branch", null);
	},
});
