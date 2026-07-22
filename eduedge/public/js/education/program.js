frappe.ui.form.on('Program', {
	setup(frm) {
		frm.set_query('eduedge_academic_section', () => ({
			query: 'eduedge.api.academic_context.institution_scoped_query',
			filters: { institution: frm.doc.eduedge_institution },
		}));
	},

	refresh(frm) {
		const label = frappe.eduedge?.term?.('programme', { fallback: __('Program') }) || __('Program');
		frm.set_df_property('program_name', 'label', `${label} Name`);
		frm.set_df_property('eduedge_academic_section', 'label', frappe.eduedge?.term?.('academic_section', { fallback: __('Academic Section') }) || __('Academic Section'));
	},

	eduedge_institution(frm) {
		if (frm.doc.eduedge_academic_section) frm.set_value('eduedge_academic_section', null);
	},
});
