frappe.ui.form.on("EduEdge User Branch Access", {
	setup(frm) {
		frm.set_query("user", () => ({ filters: { enabled: 1, user_type: "System User" } }));
		frm.set_query("company", () => ({ filters: { is_group: 0 } }));
		frm.set_query("school_branch", () => ({
			query: "eduedge.api.education.school_branch_query",
			filters: { company: frm.doc.company },
		}));
	},

	refresh(frm) {
		frm.toggle_reqd("school_branch", !frm.doc.hq_all_branch_access);
		frm.toggle_display("school_branch", !frm.doc.hq_all_branch_access);
		frm.toggle_display("is_default_branch", !frm.doc.hq_all_branch_access);
	},

	hq_all_branch_access(frm) {
		if (frm.doc.hq_all_branch_access) {
			frm.set_value("school_branch", null);
			frm.set_value("is_default_branch", 0);
			frm.set_value("can_switch_branch", 1);
		}
		frm.trigger("refresh");
	},

	company(frm) {
		if (frm.doc.school_branch) frm.set_value("school_branch", null);
	},
});
