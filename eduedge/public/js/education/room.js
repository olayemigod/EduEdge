frappe.ui.form.on('Room', {
	setup(frm) {
		frm.set_query('eduedge_school_branch', () => ({
			query: 'eduedge.api.education.school_branch_query',
		}));
	},

	onload(frm) {
		if (!frm.is_new() || frm.doc.eduedge_school_branch) return;
		frappe.call('eduedge.api.branch_context.get_current_school_branch').then(({ message }) => {
			if (message?.name) frm.set_value('eduedge_school_branch', message.name);
		});
	},
});
