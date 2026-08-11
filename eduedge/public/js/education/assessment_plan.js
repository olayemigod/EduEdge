frappe.ui.form.on("Assessment Plan", {
	setup(frm) {
		frm.set_query("student_group", () => ({
			query: "eduedge.api.assessment_assignment_options.assessment_plan_student_group_query",
			filters: {
				eduedge_school_branch: frm.doc.eduedge_school_branch,
				academic_year: frm.doc.academic_year,
				academic_term: frm.doc.academic_term,
				schedule_date: frm.doc.schedule_date,
			},
		}));
		frm.set_query("course", () => ({
			query: "eduedge.api.assessment_assignment_options.assessment_plan_course_query",
			filters: {
				eduedge_school_branch: frm.doc.eduedge_school_branch,
				student_group: frm.doc.student_group,
				schedule_date: frm.doc.schedule_date,
			},
		}));
		frm.set_query("room", () => ({
			filters: { eduedge_school_branch: frm.doc.eduedge_school_branch },
		}));
		frm.set_query("examiner", () => ({
			query: "eduedge.api.teaching_assignment_options.course_schedule_instructor_query",
			filters: {
				eduedge_school_branch: frm.doc.eduedge_school_branch,
				student_group: frm.doc.student_group,
				course: frm.doc.course,
				reference_date: frm.doc.schedule_date,
			},
		}));
		frm.set_query("supervisor", () => ({
			query: "eduedge.api.academic_operations.instructor_query",
			filters: {
				school_branch: frm.doc.eduedge_school_branch,
				reference_date: frm.doc.schedule_date,
			},
		}));
	},
	eduedge_school_branch(frm) {
		frm.set_value("student_group", null);
		frm.set_value("course", null);
		frm.set_value("room", null);
		frm.set_value("examiner", null);
		frm.set_value("supervisor", null);
	},
	academic_year(frm) {
		frm.set_value("student_group", null);
		frm.set_value("course", null);
	},
	academic_term(frm) {
		frm.set_value("student_group", null);
		frm.set_value("course", null);
	},
	student_group(frm) {
		frm.set_value("course", null);
		frm.set_value("room", null);
		frm.set_value("examiner", null);
		frm.set_value("supervisor", null);
	},
	course(frm) {
		frm.set_value("examiner", null);
	},
	schedule_date(frm) {
		frm.set_value("student_group", null);
		frm.set_value("course", null);
		frm.set_value("examiner", null);
		frm.set_value("supervisor", null);
	},
});