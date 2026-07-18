frappe.ui.form.on('Student', {
	setup(frm) {
		frm.set_query('eduedge_school_branch', () => ({
			query: 'eduedge.api.education.school_branch_query',
		}));
	},

	student_applicant(frm) {
		if (!frm.doc.student_applicant) return;
		frappe.db.get_value(
			'Student Applicant',
			frm.doc.student_applicant,
			'eduedge_school_branch'
		).then(({ message }) => {
			if (message?.eduedge_school_branch) {
				frm.set_value('eduedge_school_branch', message.eduedge_school_branch);
			}
		});
	},
});
