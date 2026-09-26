function load_eduedge_assessment_criteria(frm) {
	if (!frm.doc.course || !frm.doc.student_group || !frm.doc.eduedge_school_branch || !frm.doc.maximum_assessment_score) {
		return;
	}
	const context = {
		course: frm.doc.course,
		student_group: frm.doc.student_group,
		school_branch: frm.doc.eduedge_school_branch,
		schedule_date: frm.doc.schedule_date,
		maximum_assessment_score: frm.doc.maximum_assessment_score,
	};
	// Frappe's native course handler first calls the context-free upstream API.
	// Wait for that request to settle, then repopulate through EduEdge's exact
	// Branch + Class + assessment-date authorization path.
	frappe.after_ajax(() => {
		if (
			frm.doc.course !== context.course ||
			frm.doc.student_group !== context.student_group ||
			frm.doc.eduedge_school_branch !== context.school_branch ||
			frm.doc.schedule_date !== context.schedule_date ||
			frm.doc.maximum_assessment_score !== context.maximum_assessment_score
		) {
			return;
		}
		frappe.call({
			method: "eduedge.api.assessment_assignment_options.get_assessment_plan_criteria",
			args: {
				course: context.course,
				school_branch: context.school_branch,
				student_group: context.student_group,
				schedule_date: context.schedule_date,
			},
			callback(r) {
				if (
					frm.doc.course !== context.course ||
					frm.doc.student_group !== context.student_group ||
					frm.doc.eduedge_school_branch !== context.school_branch ||
					frm.doc.schedule_date !== context.schedule_date
				) {
					return;
				}
				frm.clear_table("assessment_criteria");
				(r.message || []).forEach((criterion) => {
					const row = frm.add_child("assessment_criteria");
					row.assessment_criteria = criterion.assessment_criteria;
					row.maximum_score =
						(Number(criterion.weightage || 0) / 100) *
						Number(frm.doc.maximum_assessment_score || 0);
				});
				frm.refresh_field("assessment_criteria");
			},
		});
	});
}

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
		// Class changes invalidate Subject and Subject-specific Examiner only.
		// Room and Supervisor are Branch-scoped and remain valid when Branch is unchanged.
		frm.set_value("course", null);
		frm.set_value("examiner", null);
	},
	course(frm) {
		frm.set_value("examiner", null);
		load_eduedge_assessment_criteria(frm);
	},
	schedule_date(frm) {
		// Date changes revalidate personnel eligibility without destroying stable
		// Class, Subject or Room context. Backend validation remains authoritative.
		frm.set_value("examiner", null);
		frm.set_value("supervisor", null);
	},
});