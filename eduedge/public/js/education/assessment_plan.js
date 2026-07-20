frappe.ui.form.on("Assessment Plan", {
	setup(frm) {
		frm.set_query("student_group", () => ({
			query: "eduedge.api.academic_operations.student_group_query",
			filters: {
				eduedge_school_branch: frm.doc.eduedge_school_branch,
				academic_year: frm.doc.academic_year,
				academic_term: frm.doc.academic_term,
			},
		}));
		frm.set_query("room", () => ({
			filters: { eduedge_school_branch: frm.doc.eduedge_school_branch },
		}));
		for (const fieldname of ["examiner", "supervisor"]) {
			frm.set_query(fieldname, () => ({
				query: "eduedge.api.academic_operations.instructor_query",
				filters: {
					school_branch: frm.doc.eduedge_school_branch,
					reference_date: frm.doc.schedule_date,
				},
			}));
		}
	},
	student_group(frm) {
		frm.set_value("room", null);
		frm.set_value("examiner", null);
		frm.set_value("supervisor", null);
	},
	schedule_date(frm) {
		frm.set_value("examiner", null);
		frm.set_value("supervisor", null);
	},
});
