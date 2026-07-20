function setEnrollmentQueries(frm) {
	frm.set_query('student', () => ({
		query: 'eduedge.api.education.student_query',
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
}

frappe.ui.form.on('Program Enrollment', {
	setup(frm) {
		setEnrollmentQueries(frm);
	},

	student(frm) {
		if (!frm.doc.student) {
			frm.set_value('eduedge_school_branch', null);
			frm.set_value('program', null);
			setEnrollmentQueries(frm);
			return;
		}
		frappe.db.get_value('Student', frm.doc.student, 'eduedge_school_branch').then(({ message }) => {
			const branch = message?.eduedge_school_branch || null;
			if (frm.doc.eduedge_school_branch !== branch) {
				frm.set_value('program', null);
			}
			frm.set_value('eduedge_school_branch', branch);
			setEnrollmentQueries(frm);
		});
	},

	academic_year(frm) {
		frm.set_value('academic_term', null);
		frm.set_value('program', null);
		setEnrollmentQueries(frm);
	},

	academic_term(frm) {
		frm.set_value('program', null);
		setEnrollmentQueries(frm);
	},

	eduedge_school_branch(frm) {
		setEnrollmentQueries(frm);
	},
});
