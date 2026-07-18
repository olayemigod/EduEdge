function setApplicantQueries(frm) {
	frm.set_query('eduedge_school_branch', () => ({
		query: 'eduedge.api.education.school_branch_query',
	}));
	frm.set_query('program', () => ({
		query: 'eduedge.api.education.program_query',
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			academic_year: frm.doc.academic_year,
			academic_term: frm.doc.academic_term,
			purpose: 'admission',
		},
	}));
	frm.set_query('student_admission', () => ({
		query: 'eduedge.api.education.student_admission_query',
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			academic_year: frm.doc.academic_year,
			program: frm.doc.program,
		},
	}));
}

frappe.ui.form.on('Student Applicant', {
	setup(frm) {
		setApplicantQueries(frm);
	},

	onload(frm) {
		if (!frm.is_new() || frm.doc.eduedge_school_branch) return;
		frappe.call('eduedge.api.branch_context.get_current_school_branch').then(({ message }) => {
			if (message?.name && !frm.doc.eduedge_school_branch) {
				frm.set_value('eduedge_school_branch', message.name);
			}
		});
	},

	eduedge_school_branch(frm) {
		frm.set_value('program', null);
		frm.set_value('student_admission', null);
		setApplicantQueries(frm);
	},

	academic_year(frm) {
		frm.set_value('academic_term', null);
		frm.set_value('program', null);
		frm.set_value('student_admission', null);
		setApplicantQueries(frm);
	},

	academic_term(frm) {
		frm.set_value('program', null);
		frm.set_value('student_admission', null);
		setApplicantQueries(frm);
	},

	program(frm) {
		frm.set_value('student_admission', null);
		setApplicantQueries(frm);
	},
});
