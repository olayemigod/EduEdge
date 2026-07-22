function setEnrollmentQueries(frm) {
	frm.set_query('student', () => ({
		query: 'eduedge.api.education.student_query',
		filters: { eduedge_school_branch: frm.doc.eduedge_school_branch },
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
	frm.set_query('eduedge_program_offering', () => ({
		query: 'eduedge.api.academic_context.program_offering_query',
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			program: frm.doc.program,
			academic_year: frm.doc.academic_year,
			academic_term: frm.doc.academic_term,
			purpose: 'enrollment',
		},
	}));
}

async function applyOffering(frm) {
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
		student_batch: message.student_batch || null,
		eduedge_academic_level: message.academic_level || null,
	});
	setEnrollmentQueries(frm);
}

frappe.ui.form.on('Program Enrollment', {
	setup(frm) {
		setEnrollmentQueries(frm);
	},

	refresh(frm) {
		frm.set_df_property('eduedge_program_offering', 'label', frappe.eduedge?.term?.('programme_offering', { fallback: __('Programme Offering') }) || __('Programme Offering'));
		frm.set_df_property('program', 'label', frappe.eduedge?.term?.('programme', { fallback: __('Program') }) || __('Program'));
		frm.set_df_property('eduedge_academic_level', 'label', frappe.eduedge?.term?.('academic_level', { fallback: __('Academic Level') }) || __('Academic Level'));
	},

	async student(frm) {
		if (!frm.doc.student) {
			if (!frm.doc.eduedge_program_offering) await frm.set_value('eduedge_school_branch', null);
			setEnrollmentQueries(frm);
			return;
		}
		const { message } = await frappe.db.get_value('Student', frm.doc.student, 'eduedge_school_branch');
		if (!frm.doc.eduedge_program_offering && message?.eduedge_school_branch) {
			await frm.set_value('eduedge_school_branch', message.eduedge_school_branch);
		}
		setEnrollmentQueries(frm);
	},

	eduedge_program_offering(frm) {
		applyOffering(frm);
	},

	academic_year(frm) {
		if (!frm.doc.eduedge_program_offering) frm.set_value('academic_term', null);
		setEnrollmentQueries(frm);
	},

	academic_term(frm) {
		setEnrollmentQueries(frm);
	},

	program(frm) {
		setEnrollmentQueries(frm);
	},

	eduedge_school_branch(frm) {
		setEnrollmentQueries(frm);
	},
});
