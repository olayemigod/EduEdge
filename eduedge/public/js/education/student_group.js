function setStudentGroupQueries(frm) {
	frm.set_query("eduedge_school_branch", () => ({ query: "eduedge.api.education.school_branch_query" }));
	frm.set_query("eduedge_program_offering", () => ({
		query: "eduedge.api.academic_context.program_offering_query",
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			program: frm.doc.program,
			academic_year: frm.doc.academic_year,
			academic_term: frm.doc.academic_term,
			purpose: "enrollment",
		},
	}));
	frm.set_query("program", () => ({
		query: "eduedge.api.education.program_query",
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			academic_year: frm.doc.academic_year,
			academic_term: frm.doc.academic_term,
			purpose: "enrollment",
		},
	}));
	frm.set_query("course", () => ({
		query: "eduedge.api.academic_operations_review.course_query",
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			program: frm.doc.program,
		},
	}));
	frm.set_query("student", "students", () => ({
		query: "eduedge.api.academic_group_context.student_group_student_query",
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			eduedge_program_offering: frm.doc.eduedge_program_offering,
			academic_year: frm.doc.academic_year,
			academic_term: frm.doc.academic_term,
			group_based_on: frm.doc.group_based_on,
			program: frm.doc.program,
			batch: frm.doc.batch,
			student_category: frm.doc.student_category,
			course: frm.doc.course,
		},
	}));
}

async function applyStudentGroupOffering(frm) {
	if (!frm.doc.eduedge_program_offering || !frm.is_new()) return;
	const selectedOffering = frm.doc.eduedge_program_offering;
	frm.__eduedge_applying_offering = true;
	try {
		const { message } = await frappe.call("eduedge.api.academic_context.get_programme_offering_context", { offering: selectedOffering });
		if (!message || frm.doc.eduedge_program_offering !== selectedOffering) return;
		await frappe.model.set_value(frm.doctype, frm.docname, {
			eduedge_school_branch: message.school_branch || null,
			eduedge_institution: message.institution || null,
			program: message.program || null,
			academic_year: message.academic_year || null,
			academic_term: message.academic_term || null,
			batch: message.student_batch || null,
			course: null,
		});
		frm.clear_table("students");
		frm.refresh_field("students");
		setStudentGroupQueries(frm);
	} finally {
		frm.__eduedge_applying_offering = false;
	}
}

async function clearStudentGroupContext(frm, fields) {
	if (!frm.is_new() || frm.__eduedge_applying_offering || frm.__eduedge_clearing_context) return;
	frm.__eduedge_clearing_context = true;
	try {
		const values = {};
		for (const fieldname of fields) if (frm.doc[fieldname]) values[fieldname] = null;
		if (Object.keys(values).length) await frappe.model.set_value(frm.doctype, frm.docname, values);
		frm.clear_table("students");
		frm.refresh_field("students");
		setStudentGroupQueries(frm);
	} finally {
		frm.__eduedge_clearing_context = false;
	}
}

function applyExistingPeriodLock(frm) {
	const locked = !frm.is_new();
	for (const fieldname of ["eduedge_school_branch", "eduedge_program_offering", "eduedge_class_arm", "program", "academic_year", "academic_term", "batch"]) {
		if (frm.fields_dict[fieldname]) frm.set_df_property(fieldname, "read_only", locked ? 1 : frm.fields_dict[fieldname].df.read_only || 0);
	}
	if (frm.fields_dict.instructors) {
		frm.set_df_property("instructors", "read_only", 1);
		frm.set_df_property("instructors", "description", __("Historical native Instructor rows are read-only. Manage teaching responsibility through EduEdge Instructor Assignments."));
	}
	if (frm.fields_dict.eduedge_display_name) {
		frm.set_df_property("eduedge_display_name", "description", __("Reusable school-facing Class Arm name. The native Student Group name is the period-specific technical identity."));
	}
}

frappe.ui.form.on("Student Group", {
	setup(frm) { setStudentGroupQueries(frm); },
	refresh(frm) {
		frm.set_df_property("eduedge_program_offering", "label", frappe.eduedge?.term?.("programme_offering", { fallback: __("Programme Offering") }) || __("Programme Offering"));
		frm.set_df_property("program", "label", frappe.eduedge?.term?.("programme", { fallback: __("Programme / Class") }) || __("Programme / Class"));
		frm.set_df_property("academic_year", "label", frappe.eduedge?.term?.("academic_year", { fallback: __("Academic Session") }) || __("Academic Session"));
		frm.set_df_property("academic_term", "label", frappe.eduedge?.term?.("academic_term", { fallback: __("Term / Semester") }) || __("Term / Semester"));
		frm.set_df_property("student_group_name", "label", __("Operational Student Group ID"));
		frm.set_df_property("course", "label", frappe.eduedge?.term?.("course", { fallback: __("Course / Subject") }) || __("Course / Subject"));
		if (frm.fields_dict.eduedge_academic_level) frm.set_df_property("eduedge_academic_level", "hidden", 1);
		applyExistingPeriodLock(frm);
		setStudentGroupQueries(frm);
	},
	onload(frm) {
		if (!frm.is_new() || frm.doc.eduedge_school_branch) return;
		frappe.call("eduedge.api.branch_context.get_current_school_branch").then(({ message }) => {
			if (message?.name) frm.set_value("eduedge_school_branch", message.name);
		});
	},
	eduedge_program_offering(frm) { applyStudentGroupOffering(frm); },
	eduedge_school_branch(frm) { clearStudentGroupContext(frm, ["eduedge_program_offering", "eduedge_institution", "program", "academic_year", "academic_term", "batch", "course"]); },
	academic_year(frm) { clearStudentGroupContext(frm, ["eduedge_program_offering", "academic_term", "course"]); },
	academic_term(frm) { clearStudentGroupContext(frm, ["eduedge_program_offering", "course"]); },
	program(frm) { clearStudentGroupContext(frm, ["eduedge_program_offering", "course"]); },
	batch(frm) { clearStudentGroupContext(frm, ["eduedge_program_offering"]); },
	course(frm) { if (frm.is_new() && !frm.__eduedge_applying_offering) { frm.clear_table("students"); frm.refresh_field("students"); } },
	group_based_on(frm) { clearStudentGroupContext(frm, ["eduedge_program_offering", "program", "batch", "course"]); },
});
