function setCourseScheduleQueries(frm) {
	frm.set_query('student_group', () => ({
		query: 'eduedge.api.academic_operations.student_group_query',
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			reference_date: frm.doc.schedule_date,
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
}

frappe.ui.form.on('Course Schedule', {
	setup(frm) {
		setCourseScheduleQueries(frm);
	},

	refresh(frm) {
		frm.set_df_property('student_group', 'label', frappe.eduedge?.term?.('student_group', { fallback: __('Student Group / Class Arm') }) || __('Student Group / Class Arm'));
		frm.set_df_property('instructor', 'label', frappe.eduedge?.term?.('instructor', { fallback: __('Instructor') }) || __('Instructor'));
		frm.set_df_property('room', 'label', frappe.eduedge?.term?.('room', { fallback: __('Room') }) || __('Room'));
		setCourseScheduleQueries(frm);
	},

	student_group(frm) {
		if (!frm.doc.student_group) {
			frm.set_value('eduedge_school_branch', null);
			frm.set_value('instructor', null);
			frm.set_value('room', null);
			return;
		}
		frappe.db.get_value('Student Group', frm.doc.student_group, 'eduedge_school_branch')
			.then(({ message }) => {
				frm.set_value('eduedge_school_branch', message?.eduedge_school_branch || null);
				frm.set_value('instructor', null);
				frm.set_value('room', null);
				setCourseScheduleQueries(frm);
			});
	},

	schedule_date(frm) {
		frm.set_value('instructor', null);
		setCourseScheduleQueries(frm);
	},

	eduedge_school_branch(frm) {
		if (frm.doc.student_group) {
			frappe.db.get_value('Student Group', frm.doc.student_group, 'eduedge_school_branch')
				.then(({ message }) => {
					if (message?.eduedge_school_branch !== frm.doc.eduedge_school_branch) {
						frm.set_value('student_group', null);
					}
				});
		}
		frm.set_value('instructor', null);
		frm.set_value('room', null);
		setCourseScheduleQueries(frm);
	},
});
