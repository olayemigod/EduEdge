const PROGRAM_PROMOTION = 'Program Promotion';
const LEVEL_PROGRESSION = 'Level Progression';

function configureStudentGroupIdentity(frm) {
	const label = frappe.eduedge?.term?.('student_group', { fallback: __('Student Group / Class Arm / Lecture Group') }) || __('Student Group / Class Arm / Lecture Group');
	if (frm.fields_dict.eduedge_display_name) {
		frm.set_df_property('eduedge_display_name', 'label', `${label} Name`);
		frm.set_df_property('eduedge_display_name', 'reqd', 1);
	}
	if (frm.fields_dict.student_group_name) {
		frm.set_df_property('student_group_name', 'label', __('Technical Group ID'));
		frm.set_df_property('student_group_name', 'hidden', 1);
	}
}

function setStudentGroupQueries(frm) {
	frm.set_query('eduedge_school_branch', () => ({ query: 'eduedge.api.education.school_branch_query' }));
	frm.set_query('eduedge_program_offering', () => ({
		query: 'eduedge.api.academic_context.program_offering_query',
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			program: frm.doc.program,
			eduedge_academic_level: frm.doc.eduedge_academic_level,
			academic_year: frm.doc.academic_year,
			academic_term: frm.doc.academic_term,
			purpose: 'enrollment',
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
	frm.set_query('eduedge_academic_level', () => ({
		query: 'eduedge.api.academic_context.institution_scoped_query',
		filters: { institution: frm.doc.eduedge_institution, program: frm.doc.program },
	}));
	frm.set_query('course', () => ({
		query: 'eduedge.api.academic_operations_review.course_query',
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			program: frm.doc.program,
			eduedge_academic_level: frm.doc.eduedge_academic_level,
			academic_year: frm.doc.academic_year,
			academic_term: frm.doc.academic_term,
		},
	}));
	frm.set_query('student', 'students', () => ({
		query: 'eduedge.api.academic_group_context.student_group_student_query',
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			eduedge_program_offering: frm.doc.eduedge_program_offering,
			eduedge_academic_level: frm.doc.eduedge_academic_level,
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
		filters: { eduedge_school_branch: frm.doc.eduedge_school_branch },
	}));
}

async function applyStudentGroupOffering(frm) {
	if (!frm.doc.eduedge_program_offering) return;
	const selectedOffering = frm.doc.eduedge_program_offering;
	frm.__eduedge_applying_offering = true;
	try {
		const { message } = await frappe.call('eduedge.api.academic_context.get_programme_offering_context', { offering: selectedOffering });
		if (!message || frm.doc.eduedge_program_offering !== selectedOffering) return;
		await frappe.model.set_value(frm.doctype, frm.docname, {
			eduedge_school_branch: message.school_branch || null,
			eduedge_institution: message.institution || null,
			program: message.program || null,
			eduedge_academic_level: message.eduedge_academic_level || message.academic_level || null,
			academic_year: message.academic_year || null,
			academic_term: message.academic_term || null,
			batch: message.student_batch || null,
			course: null,
		});
		frm.clear_table('students');
		frm.refresh_field('students');
		setStudentGroupQueries(frm);
		await configureGroupProgression(frm);
	} finally {
		frm.__eduedge_applying_offering = false;
	}
}

async function clearStudentGroupContext(frm, fields, { clearInstructors = false } = {}) {
	if (frm.__eduedge_applying_offering || frm.__eduedge_clearing_context) return;
	frm.__eduedge_clearing_context = true;
	try {
		const values = {};
		for (const fieldname of fields) if (frm.doc[fieldname]) values[fieldname] = null;
		if (Object.keys(values).length) await frappe.model.set_value(frm.doctype, frm.docname, values);
		frm.clear_table('students');
		if (clearInstructors) frm.clear_table('instructors');
		frm.refresh_fields(clearInstructors ? ['students', 'instructors'] : ['students']);
		setStudentGroupQueries(frm);
	} finally {
		frm.__eduedge_clearing_context = false;
	}
}

async function configureGroupProgression(frm) {
	let mode = '';
	if (frm.doc.program) {
		const { message } = await frappe.db.get_value('Program', frm.doc.program, 'eduedge_progression_mode');
		mode = message?.eduedge_progression_mode || '';
	}
	frm.__eduedge_progression_mode = mode;
	const legacyMismatch = !frm.is_new() && ((mode === PROGRAM_PROMOTION && (frm.doc.eduedge_academic_level || frm.doc.academic_term)) || (mode === LEVEL_PROGRESSION && (!frm.doc.eduedge_academic_level || !frm.doc.academic_term)));
	if (frm.fields_dict.eduedge_academic_level) {
		frm.set_df_property('eduedge_academic_level', 'hidden', mode === LEVEL_PROGRESSION || legacyMismatch ? 0 : 1);
		frm.set_df_property('eduedge_academic_level', 'read_only', frm.doc.eduedge_program_offering ? 1 : 0);
	}
	if (frm.fields_dict.academic_term) frm.set_df_property('academic_term', 'hidden', mode === PROGRAM_PROMOTION && !legacyMismatch ? 1 : 0);
	if (legacyMismatch) frm.dashboard.set_headline_alert(__('Legacy Student Group context detected. Select a corrected Programme Offering before changing Branch, Programme, Level or period.'), 'orange');
}

function offeringListHtml(rows) {
	return rows.slice(0, 20).map((row) => `<div><strong>${frappe.utils.escape_html(row.name)}</strong> — ${frappe.utils.escape_html([row.offering_title, row.academic_level, row.academic_year, row.academic_term, row.school_branch].filter(Boolean).join(' · '))}</div>`).join('');
}

async function openRolloverDialog(frm) {
	const { message } = await frappe.call('eduedge.api.progression_workflow.get_student_group_rollover_options', { student_group: frm.doc.name });
	const rows = message?.target_offerings || [];
	if (!rows.length) {
		frappe.msgprint({ title: __('Rollover Student Group'), message: __('No eligible target Programme Offering is configured for the next Class or Academic Level.'), indicator: 'orange' });
		return;
	}
	const dialog = new frappe.ui.Dialog({
		title: __('Rollover Student Group'),
		fields: [
			{ fieldname: 'guidance', fieldtype: 'HTML', options: `<p>${__('Create a new session-specific group. Students and instructors will not be copied.')}</p><div class="small text-muted">${offeringListHtml(rows)}</div>` },
			{ fieldname: 'target_program_offering', fieldtype: 'Select', label: __('Target Programme Offering'), options: ['', ...rows.map((row) => row.name)].join('\n'), reqd: 1 },
			{ fieldname: 'group_name', fieldtype: 'Data', label: __('New Group / Class Arm / Lecture Group Name'), default: message.suggested_group_name, reqd: 1 },
		],
		primary_action_label: __('Create Group'),
		async primary_action(values) {
			dialog.get_primary_btn().prop('disabled', true);
			try {
				const { message: result } = await frappe.call('eduedge.api.progression_workflow.rollover_student_group', {
					student_group: frm.doc.name,
					target_program_offering: values.target_program_offering,
					group_name: values.group_name,
				});
				dialog.hide();
				frappe.show_alert({ message: result.created ? __('New Student Group created') : __('Existing Student Group opened'), indicator: 'green' });
				frappe.set_route('Form', 'Student Group', result.name);
			} finally {
				dialog.get_primary_btn().prop('disabled', false);
			}
		},
	});
	dialog.show();
}

frappe.ui.form.on('Student Group', {
	setup(frm) { setStudentGroupQueries(frm); },
	async refresh(frm) {
		configureStudentGroupIdentity(frm);
		frm.set_df_property('eduedge_program_offering', 'label', frappe.eduedge?.term?.('programme_offering', { fallback: __('Programme Offering') }) || __('Programme Offering'));
		frm.set_df_property('program', 'label', frappe.eduedge?.term?.('programme', { fallback: __('Programme / Class') }) || __('Programme / Class'));
		frm.set_df_property('academic_year', 'label', frappe.eduedge?.term?.('academic_year', { fallback: __('Academic Session') }) || __('Academic Session'));
		frm.set_df_property('academic_term', 'label', frappe.eduedge?.term?.('academic_term', { fallback: __('Term / Semester') }) || __('Term / Semester'));
		frm.set_df_property('course', 'label', frappe.eduedge?.term?.('course', { fallback: __('Course / Subject') }) || __('Course / Subject'));
		if (frm.fields_dict.eduedge_academic_level) frm.set_df_property('eduedge_academic_level', 'label', frappe.eduedge?.term?.('academic_level', { fallback: __('Academic Level') }) || __('Academic Level'));
		setStudentGroupQueries(frm);
		await configureGroupProgression(frm);
		if (!frm.is_new() && !frm.doc.disabled && frappe.model.can_create('Student Group')) frm.add_custom_button(__('Rollover Group'), () => openRolloverDialog(frm), __('Academic Progression'));
	},
	onload(frm) {
		if (!frm.is_new() || frm.doc.eduedge_school_branch) return;
		frappe.call('eduedge.api.branch_context.get_current_school_branch').then(({ message }) => { if (message?.name) frm.set_value('eduedge_school_branch', message.name); });
	},
	eduedge_display_name(frm) { if (frm.is_new() && frm.doc.eduedge_display_name) frm.set_value('student_group_name', frm.doc.eduedge_display_name); },
	validate(frm) { if (frm.is_new() && frm.doc.eduedge_display_name && !frm.doc.student_group_name) frm.doc.student_group_name = frm.doc.eduedge_display_name; },
	eduedge_program_offering(frm) { applyStudentGroupOffering(frm); },
	eduedge_school_branch(frm) { clearStudentGroupContext(frm, ['eduedge_program_offering', 'eduedge_institution', 'program', 'eduedge_academic_level', 'academic_year', 'academic_term', 'batch', 'course'], { clearInstructors: true }); },
	academic_year(frm) { clearStudentGroupContext(frm, ['eduedge_program_offering', 'academic_term', 'course']); },
	academic_term(frm) { clearStudentGroupContext(frm, ['eduedge_program_offering', 'course']); },
	async program(frm) { await clearStudentGroupContext(frm, ['eduedge_program_offering', 'eduedge_academic_level', 'course']); await configureGroupProgression(frm); },
	eduedge_academic_level(frm) { clearStudentGroupContext(frm, ['eduedge_program_offering', 'course']); },
	batch(frm) { clearStudentGroupContext(frm, ['eduedge_program_offering']); },
	course(frm) { if (!frm.__eduedge_applying_offering) { frm.clear_table('students'); frm.refresh_field('students'); } },
	group_based_on(frm) { clearStudentGroupContext(frm, ['eduedge_program_offering', 'program', 'eduedge_academic_level', 'batch', 'course']); },
});
