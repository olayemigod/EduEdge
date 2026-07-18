frappe.ui.form.on('Student Attendance', {
	setup(frm) {
		frm.set_query('student_group', () => ({
			query: 'eduedge.api.academic_operations.student_group_query',
			filters: {
				eduedge_school_branch: frm.doc.eduedge_school_branch,
			},
		}));
		frm.set_query('student', () => ({
			query: 'eduedge.api.academic_operations.student_group_member_query',
			filters: {
				student_group: frm.doc.student_group,
			},
		}));
	},
});
