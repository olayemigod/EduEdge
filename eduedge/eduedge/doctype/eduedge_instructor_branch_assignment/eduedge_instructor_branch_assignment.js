frappe.ui.form.on('EduEdge Instructor Branch Assignment', {
	setup(frm) {
		frm.set_query('school_branch', () => ({
			query: 'eduedge.api.education.school_branch_query',
		}));
		frm.set_query('instructor', () => ({
			filters: { status: 'Active' },
		}));
	},
});
