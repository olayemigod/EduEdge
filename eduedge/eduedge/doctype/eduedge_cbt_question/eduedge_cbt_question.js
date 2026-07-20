frappe.ui.form.on("EduEdge CBT Question", {
	setup(frm) {
		frm.set_query("school_branch", () => ({ filters: { enabled: 1 } }));
	},
	refresh(frm) {
		frm.set_df_property("options", "cannot_add_rows", frm.doc.is_active && !frm.is_new() ? 0 : 0);
	},
});

frappe.ui.form.on("EduEdge CBT Question Option", {
	options_add(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		row.display_order = (frm.doc.options || []).length;
		if (!row.option_key) {
			row.option_key = String.fromCharCode(64 + Math.min(26, row.display_order || 1));
		}
		frm.refresh_field("options");
	},
});
