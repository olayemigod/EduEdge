frappe.ui.form.on("EduEdge User Branch Access", {
	setup(frm) {
		frm.set_query("user", () => ({ filters: { enabled: 1, user_type: "System User" } }));
		frm.set_query("company", () => ({ filters: { is_group: 0 } }));
		frm.set_query("institution", () => ({
			filters: { company: frm.doc.company, enabled: 1 },
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
