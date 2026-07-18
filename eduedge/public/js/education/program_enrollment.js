frappe.ui.form.on('Program Enrollment', {
	setup(frm) {
		frm.set_query('student', () => ({
			query: 'eduedge.api.education.student_query',
			filters: {
				eduedge_school_branch: frm.doc.eduedge_school_branch,
			},
		}));
	},

	student(frm) {
		if (!frm.doc.student) {
			frm.set_value('eduedge_school_branch', null);
			return;
		}
		frappe.db.get_value('Student', frm.doc.student, 'eduedge_school_branch').then(({ message }) => {
			frm.set_value('eduedge_school_branch', message?.eduedge_school_branch || null);
		});
	},
});
