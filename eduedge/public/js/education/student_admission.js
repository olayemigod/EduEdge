function setAdmissionQueries(frm) {
	frm.set_query('eduedge_school_branch', () => ({
		query: 'eduedge.api.education.school_branch_query',
	}));
	frm.set_query('program', 'program_details', () => ({
		query: 'eduedge.api.education.program_query',
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			academic_year: frm.doc.academic_year,
			purpose: 'admission',
		},
	}));
}

frappe.ui.form.on('Student Admission', {
	setup(frm) {
		setAdmissionQueries(frm);
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
		setAdmissionQueries(frm);
		if (frm.is_new() && (frm.doc.program_details || []).length) {
			frm.clear_table('program_details');
			frm.refresh_field('program_details');
		}
	},

	academic_year(frm) {
		setAdmissionQueries(frm);
		if (frm.is_new() && (frm.doc.program_details || []).length) {
			frm.clear_table('program_details');
			frm.refresh_field('program_details');
		}
	},
});
