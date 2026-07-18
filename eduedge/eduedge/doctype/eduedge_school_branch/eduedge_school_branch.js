frappe.ui.form.on("EduEdge School Branch", {
	setup(frm) {
		frm.set_query("cost_center", () => ({
			filters: { company: frm.doc.company, is_group: 0, disabled: 0 },
		}));
		frm.set_query("default_warehouse", () => ({
			filters: { company: frm.doc.company, is_group: 0, disabled: 0 },
		}));
	},

	company(frm) {
		for (const fieldname of ["cost_center", "default_warehouse"]) {
			if (frm.doc[fieldname]) {
				frm.set_value(fieldname, null);
			}
		}
	},
});
