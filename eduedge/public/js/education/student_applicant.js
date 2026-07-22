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
	frm.set_query('eduedge_program_offering', () => ({
		query: 'eduedge.api.academic_context.program_offering_query',
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			program: frm.doc.program,
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

async function applyApplicantOffering(frm) {
	if (!frm.doc.eduedge_program_offering) return;
	const { message } = await frappe.call('eduedge.api.academic_context.get_programme_offering_context', {
		offering: frm.doc.eduedge_program_offering,
	});
	if (!message) return;
	await frappe.model.set_value(frm.doctype, frm.docname, {
		eduedge_school_branch: message.school_branch || null,
		eduedge_institution: message.institution || null,
		program: message.program || null,
		academic_year: message.academic_year || null,
		academic_term: message.academic_term || null,
		eduedge_academic_level: message.academic_level || null,
	});
	setApplicantQueries(frm);
}

frappe.ui.form.on('Student Applicant', {
	setup(frm) {
		setApplicantQueries(frm);
	},

	refresh(frm) {
		frm.set_df_property('eduedge_program_offering', 'label', frappe.eduedge?.term?.('programme_offering', { fallback: __('Programme Offering') }) || __('Programme Offering'));
		frm.set_df_property('program', 'label', frappe.eduedge?.term?.('programme', { fallback: __('Program') }) || __('Program'));
	},

	onload(frm) {
		if (!frm.is_new() || frm.doc.eduedge_school_branch) return;
		frappe.call('eduedge.api.branch_context.get_current_school_branch').then(({ message }) => {
			if (message?.name && !frm.doc.eduedge_school_branch) frm.set_value('eduedge_school_branch', message.name);
		});
	},

	eduedge_program_offering(frm) {
		applyApplicantOffering(frm);
	},

	eduedge_school_branch(frm) {
		if (frm.doc.eduedge_program_offering) frm.set_value('eduedge_program_offering', null);
		frm.set_value('program', null);
		frm.set_value('student_admission', null);
		setApplicantQueries(frm);
	},

	academic_year(frm) {
		if (!frm.doc.eduedge_program_offering) frm.set_value('academic_term', null);
		frm.set_value('student_admission', null);
		setApplicantQueries(frm);
	},

	academic_term(frm) {
		frm.set_value('student_admission', null);
		setApplicantQueries(frm);
	},

	program(frm) {
		frm.set_value('student_admission', null);
		setApplicantQueries(frm);
	},
});
