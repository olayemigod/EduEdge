function setEnrollmentQueries(frm) {
	frm.set_query('eduedge_school_branch', () => ({
		query: 'eduedge.api.education.school_branch_query',
	}));
	frm.set_query('student', () => ({
		query: 'eduedge.api.education.student_query',
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			allow_cross_branch: 1,
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

function updateEnrollmentContextLocks(frm) {
	const locked = Boolean(frm.doc.eduedge_program_offering) || frm.doc.docstatus !== 0;
	frm.set_df_property('eduedge_school_branch', 'read_only', locked ? 1 : 0);
}

async function applyOffering(frm) {
	if (!frm.doc.eduedge_program_offering) {
		updateEnrollmentContextLocks(frm);
		return;
	}
	const selectedOffering = frm.doc.eduedge_program_offering;
	frm.__eduedge_applying_offering = true;
	try {
		const { message } = await frappe.call('eduedge.api.academic_context.get_programme_offering_context', {
			offering: selectedOffering,
		});
		if (!message || frm.doc.eduedge_program_offering !== selectedOffering) return;
		await frappe.model.set_value(frm.doctype, frm.docname, {
			eduedge_school_branch: message.school_branch || null,
			eduedge_institution: message.institution || null,
			program: message.program || null,
			academic_year: message.academic_year || null,
			academic_term: message.academic_term || null,
			student_batch_name: message.student_batch || null,
			eduedge_academic_level: message.academic_level || null,
		});
		setEnrollmentQueries(frm);
	} finally {
		frm.__eduedge_applying_offering = false;
		updateEnrollmentContextLocks(frm);
	}
}

function addEnrollmentLifecycleActions(frm) {
	if (frm.doc.docstatus !== 1) return;
	if (frappe.model.can_create('EduEdge Enrollment Status Log')) {
		frm.add_custom_button(__('Change Enrollment Status'), () => {
			frappe.new_doc('EduEdge Enrollment Status Log', {
				program_enrollment: frm.doc.name,
				effective_date: frappe.datetime.get_today(),
			});
		}, __('Enrollment'));
	}
	frm.add_custom_button(__('View Status History'), () => {
		frappe.set_route('List', 'EduEdge Enrollment Status Log', {
			program_enrollment: frm.doc.name,
		});
	}, __('Enrollment'));
}

frappe.ui.form.on('Program Enrollment', {
	setup(frm) {
		setEnrollmentQueries(frm);
	},

	onload(frm) {
		if (!frm.is_new() || frm.doc.eduedge_school_branch) return;
		frappe.call('eduedge.api.branch_context.get_current_school_branch').then(({ message }) => {
			if (message?.name && !frm.doc.eduedge_school_branch) frm.set_value('eduedge_school_branch', message.name);
		});
	},

	refresh(frm) {
		frm.set_df_property('eduedge_program_offering', 'label', frappe.eduedge?.term?.('programme_offering', { fallback: __('Programme Offering') }) || __('Programme Offering'));
		frm.set_df_property('program', 'label', frappe.eduedge?.term?.('programme', { fallback: __('Program') }) || __('Program'));
		frm.set_df_property('eduedge_academic_level', 'label', frappe.eduedge?.term?.('academic_level', { fallback: __('Academic Level') }) || __('Academic Level'));
		updateEnrollmentContextLocks(frm);
		addEnrollmentLifecycleActions(frm);
	},

	async student(frm) {
		if (!frm.doc.student) {
			setEnrollmentQueries(frm);
			return;
		}
		if (!frm.doc.eduedge_program_offering && !frm.doc.eduedge_school_branch) {
			const { message } = await frappe.db.get_value('Student', frm.doc.student, 'eduedge_school_branch');
			if (message?.eduedge_school_branch) await frm.set_value('eduedge_school_branch', message.eduedge_school_branch);
		}
		setEnrollmentQueries(frm);
	},

	eduedge_program_offering(frm) {
		applyOffering(frm);
	},

	academic_year(frm) {
		if (!frm.__eduedge_applying_offering && !frm.doc.eduedge_program_offering) frm.set_value('academic_term', null);
		setEnrollmentQueries(frm);
	},

	academic_term(frm) {
		setEnrollmentQueries(frm);
	},

	program(frm) {
		setEnrollmentQueries(frm);
	},

	eduedge_school_branch(frm) {
		if (frm.__eduedge_applying_offering) return;
		if (frm.doc.eduedge_program_offering) frm.set_value('eduedge_program_offering', null);
		frm.set_value('program', null);
		setEnrollmentQueries(frm);
		updateEnrollmentContextLocks(frm);
	},
});
