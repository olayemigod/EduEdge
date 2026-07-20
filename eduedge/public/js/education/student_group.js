frappe.ui.form.on('Student Group', {
	setup(frm) {
		frm.set_query('eduedge_school_branch', () => ({
			query: 'eduedge.api.education.school_branch_query',
		}));
		frm.set_query('student', 'students', () => ({
			query: 'eduedge.api.academic_operations.student_group_student_query',
			filters: {
				eduedge_school_branch: frm.doc.eduedge_school_branch,
				academic_year: frm.doc.academic_year,
				academic_term: frm.doc.academic_term,
				group_based_on: frm.doc.group_based_on,
				program: frm.doc.program,
				batch: frm.doc.batch,
				student_category: frm.doc.student_category,
				course: frm.doc.course,
			},
		}));
		frm.set_query('instructor', 'instructors', () => ({
			query: 'eduedge.api.academic_operations.instructor_query',
			filters: {
				eduedge_school_branch: frm.doc.eduedge_school_branch,
			},
		}));
		frm.set_query('program', () => ({
			query: 'eduedge.api.education.program_query',
			filters: {
				eduedge_school_branch: frm.doc.eduedge_school_branch,
				academic_year: frm.doc.academic_year,
				academic_term: frm.doc.academic_term,
				purpose: 'enrollment',
			},
		}));
	},

	onload(frm) {
		if (!frm.is_new() || frm.doc.eduedge_school_branch) return;
		frappe.call('eduedge.api.branch_context.get_current_school_branch').then(({ message }) => {
			if (message?.name) frm.set_value('eduedge_school_branch', message.name);
		});
	},

	eduedge_school_branch(frm) {
		frm.set_value('program', null);
		frm.clear_table('students');
		frm.clear_table('instructors');
		frm.refresh_fields(['students', 'instructors']);
	},
});
