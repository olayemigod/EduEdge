const PROGRAM_PROMOTION = 'Program Promotion';
const LEVEL_PROGRESSION = 'Level Progression';
const NO_PROGRESSION = 'No Automatic Progression';

function configureProgrammeIdentity(frm) {
	const label = frappe.eduedge?.term?.('programme', { fallback: __('Program') }) || __('Program');
	if (frm.fields_dict.eduedge_display_name) {
		frm.set_df_property('eduedge_display_name', 'label', `${label} Name`);
		frm.set_df_property('eduedge_display_name', 'reqd', 1);
	}
	if (frm.fields_dict.program_name) {
		frm.set_df_property('program_name', 'label', __('Technical Programme / Class ID'));
		frm.set_df_property('program_name', 'hidden', 1);
	}
	if (frm.fields_dict.eduedge_academic_section) frm.set_df_property('eduedge_academic_section', 'hidden', 1);
}

function setProgrammeQueries(frm) {
	frm.set_query('department', () => ({
		query: 'eduedge.api.academic_context.institution_scoped_query',
		filters: { institution: frm.doc.eduedge_institution },
	}));
	frm.set_query('eduedge_next_program', () => ({
		filters: {
			eduedge_institution: frm.doc.eduedge_institution,
			name: ['!=', frm.doc.name || ''],
		},
	}));
	frm.set_query('eduedge_academic_level', 'courses', () => ({
		query: 'eduedge.api.academic_context.institution_scoped_query',
		filters: {
			institution: frm.doc.eduedge_institution,
			program: frm.doc.name,
		},
	}));
	frm.set_query('course', 'courses', () => ({
		filters: { eduedge_institution: frm.doc.eduedge_institution },
	}));
}

function configureProgressionFields(frm) {
	const mode = frm.doc.eduedge_progression_mode || NO_PROGRESSION;
	const usesPrograms = mode === PROGRAM_PROMOTION;
	const usesLevels = mode === LEVEL_PROGRESSION;
	if (frm.fields_dict.eduedge_next_program) {
		frm.set_df_property('eduedge_next_program', 'hidden', usesPrograms && !frm.doc.eduedge_terminal_program ? 0 : 1);
		frm.set_df_property('eduedge_next_program', 'reqd', 0);
	}
	if (frm.fields_dict.eduedge_progression_sequence) frm.set_df_property('eduedge_progression_sequence', 'hidden', mode === NO_PROGRESSION ? 1 : 0);
	if (frm.fields_dict.eduedge_allow_repetition) frm.set_df_property('eduedge_allow_repetition', 'hidden', mode === NO_PROGRESSION ? 1 : 0);
	if (frm.fields_dict.eduedge_terminal_program) frm.set_df_property('eduedge_terminal_program', 'hidden', usesLevels ? 1 : 0);
	if (frm.fields_dict.courses?.grid?.get_field('eduedge_academic_level')) {
		frm.fields_dict.courses.grid.get_field('eduedge_academic_level').df.hidden = usesLevels ? 0 : 1;
		frm.fields_dict.courses.grid.get_field('eduedge_period_number').df.hidden = usesLevels ? 0 : 1;
		frm.fields_dict.courses.grid.get_field('eduedge_credit_units').df.hidden = usesLevels ? 0 : 1;
		frm.fields_dict.courses.grid.refresh();
	}
}

async function applyInstitutionProgressionDefault(frm) {
	if (!frm.doc.eduedge_institution || !frm.is_new()) return;
	const { message } = await frappe.db.get_value('EduEdge Institution', frm.doc.eduedge_institution, 'institution_type');
	const type = String(message?.institution_type || '').toUpperCase();
	const mode = ['PRIMARY', 'SECONDARY'].includes(type) ? PROGRAM_PROMOTION : ['TERTIARY', 'TRAINING_CENTRE'].includes(type) ? LEVEL_PROGRESSION : NO_PROGRESSION;
	await frm.set_value('eduedge_progression_mode', mode);
	configureProgressionFields(frm);
}

frappe.ui.form.on('Program', {
	setup(frm) { setProgrammeQueries(frm); },
	refresh(frm) {
		configureProgrammeIdentity(frm);
		configureProgressionFields(frm);
		setProgrammeQueries(frm);
		if (!frm.is_new() && frm.doc.eduedge_progression_mode === LEVEL_PROGRESSION) {
			frm.add_custom_button(__('Manage Academic Levels'), () => {
				frappe.set_route('List', 'EduEdge Academic Level', { institution: frm.doc.eduedge_institution, program: frm.doc.name });
			}, __('Academic Progression'));
		}
	},
	eduedge_display_name(frm) {
		if (frm.is_new() && frm.doc.eduedge_display_name) frm.set_value('program_name', frm.doc.eduedge_display_name);
	},
	validate(frm) {
		if (frm.is_new() && frm.doc.eduedge_display_name && !frm.doc.program_name) frm.doc.program_name = frm.doc.eduedge_display_name;
	},
	async eduedge_institution(frm) {
		await frm.set_value({ department: null, eduedge_next_program: null });
		for (const row of frm.doc.courses || []) row.eduedge_academic_level = null;
		frm.refresh_field('courses');
		setProgrammeQueries(frm);
		await applyInstitutionProgressionDefault(frm);
	},
	eduedge_progression_mode(frm) {
		if (frm.doc.eduedge_progression_mode !== PROGRAM_PROMOTION) frm.set_value('eduedge_next_program', null);
		if (frm.doc.eduedge_progression_mode !== LEVEL_PROGRESSION) {
			for (const row of frm.doc.courses || []) row.eduedge_academic_level = null;
			frm.refresh_field('courses');
		}
		configureProgressionFields(frm);
	},
	eduedge_terminal_program(frm) {
		if (frm.doc.eduedge_terminal_program) frm.set_value('eduedge_next_program', null);
		configureProgressionFields(frm);
	},
});
