frappe.ui.form.on('EduEdge Program Offering', {
	setup(frm) {
		frm.set_query('school_branch', () => ({
			query: 'eduedge.api.education.school_branch_query',
		}));
		frm.set_query('academic_term', () => ({
			filters: {
				academic_year: frm.doc.academic_year,
			},
		}));
	},

	academic_year(frm) {
		if (frm.doc.academic_term) {
			frm.set_value('academic_term', null);
		}
	},
});
