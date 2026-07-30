function configureCourseIdentity(frm) {
	const label = frappe.eduedge?.term?.('course', { fallback: __('Course') }) || __('Course');
	if (frm.fields_dict.eduedge_display_name) {
		frm.set_df_property('eduedge_display_name', 'label', `${label} Name`);
		frm.set_df_property('eduedge_display_name', 'reqd', 1);
	}
	if (frm.fields_dict.course_name) {
		frm.set_df_property('course_name', 'label', __('Technical Course / Subject ID'));
		frm.set_df_property('course_name', 'hidden', 1);
	}
}

frappe.ui.form.on('Course', {
	refresh(frm) {
		configureCourseIdentity(frm);
	},

	eduedge_display_name(frm) {
		if (frm.is_new() && frm.doc.eduedge_display_name) {
			frm.set_value('course_name', frm.doc.eduedge_display_name);
		}
	},

	validate(frm) {
		if (frm.is_new() && frm.doc.eduedge_display_name && !frm.doc.course_name) {
			frm.doc.course_name = frm.doc.eduedge_display_name;
		}
	},
});
