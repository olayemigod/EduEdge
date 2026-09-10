frappe.ui.form.on('Course', {
	refresh(frm) {
		const label = frappe.eduedge?.term?.('course', { fallback: __('Course') }) || __('Course');
		if (frm.fields_dict.course_name) frm.set_df_property('course_name', 'label', `${label} Name`);
	},
});
