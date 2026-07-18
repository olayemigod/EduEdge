frappe.ui.form.on("EduEdge Settings", {
	setup(frm) {
		frm.set_query("default_school_branch", () => ({
			filters: {
				company: frm.doc.default_company,
				enabled: 1,
			},
		}));
	},

	default_company(frm) {
		if (frm.doc.default_school_branch) {
			frm.set_value("default_school_branch", null);
		}
	},
});
