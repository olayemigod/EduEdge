frappe.ui.form.on('Course Schedule', {
	setup(frm) {
		frm.set_query('student_group', () => ({
			query: 'eduedge.api.academic_operations.student_group_query',
			filters: {
				eduedge_school_branch: frm.doc.eduedge_school_branch,
			},
		}));
		frm.set_query('instructor', () => ({
			query: 'eduedge.api.academic_operations.instructor_query',
			filters: {
				eduedge_school_branch: frm.doc.eduedge_school_branch,
				reference_date: frm.doc.schedule_date,
			},
		}));
		frm.set_query('room', () => ({
			query: 'eduedge.api.academic_operations.room_query',
			filters: {
				eduedge_school_branch: frm.doc.eduedge_school_branch,
			},
		}));
	},

	student_group(frm) {
		if (!frm.doc.student_group) {
			frm.set_value('eduedge_school_branch', null);
			return;
		}
		frappe.db.get_value('Student Group', frm.doc.student_group, 'eduedge_school_branch')
			.then(({ message }) => {
				frm.set_value('eduedge_school_branch', message?.eduedge_school_branch || null);
				frm.set_value('instructor', null);
				frm.set_value('room', null);
			});
	},
});
