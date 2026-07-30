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
	frm.set_df_property('eduedge_academic_section', 'label', frappe.eduedge?.term?.('academic_section', { fallback: __('Academic Section') }) || __('Academic Section'));
}

frappe.ui.form.on('Program', {
	setup(frm) {
		frm.set_query('eduedge_academic_section', () => ({
			query: 'eduedge.api.academic_context.institution_scoped_query',
			filters: { institution: frm.doc.eduedge_institution },
		}));
	},

	refresh(frm) {
		configureProgrammeIdentity(frm);
	},

	eduedge_display_name(frm) {
		if (frm.is_new() && frm.doc.eduedge_display_name) {
			frm.set_value('program_name', frm.doc.eduedge_display_name);
		}
	},

	validate(frm) {
		if (frm.is_new() && frm.doc.eduedge_display_name && !frm.doc.program_name) {
			frm.doc.program_name = frm.doc.eduedge_display_name;
		}
	},

	eduedge_institution(frm) {
		if (frm.doc.eduedge_academic_section) frm.set_value('eduedge_academic_section', null);
	},
});
