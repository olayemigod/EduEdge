function setCourseScheduleQueries(frm) {
	frm.set_query("student_group", () => ({
		query: "eduedge.api.academic_operations.student_group_query",
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			reference_date: frm.doc.schedule_date,
			program: frm.__eduedge_student_group_program || undefined,
		},
	}));
	frm.set_query("course", () => ({
		query: "eduedge.api.academic_operations_review.course_query",
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			program: frm.__eduedge_student_group_program || "",
		},
	}));
	frm.set_query("instructor", () => ({
		query: "eduedge.api.teaching_assignment_options.course_schedule_instructor_query",
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			student_group: frm.doc.student_group,
			course: frm.doc.course,
			reference_date: frm.doc.schedule_date,
		},
	}));
	frm.set_query("room", () => ({
		query: "eduedge.api.academic_operations.room_query",
		filters: { eduedge_school_branch: frm.doc.eduedge_school_branch },
	}));
}

async function getStudentGroupContext(frm) {
	if (!frm.doc.student_group) return null;
	const selectedGroup = frm.doc.student_group;
	const { message } = await frappe.db.get_value(
		"Student Group",
		selectedGroup,
		["eduedge_school_branch", "program", "course", "group_based_on"]
	);
	if (frm.doc.student_group !== selectedGroup) return null;
	return message || null;
}

async function hydrateStudentGroupContext(frm) {
	// Opening/refreshing an existing Course Schedule must never mutate its saved
	// Subject, Instructor or Room. We only hydrate query context here.
	if (!frm.doc.student_group) {
		frm.__eduedge_student_group_program = "";
		setCourseScheduleQueries(frm);
		return;
	}
	const message = await getStudentGroupContext(frm);
	if (!message) return;
	frm.__eduedge_student_group_program = message.program || "";
	setCourseScheduleQueries(frm);
}

async function applyStudentGroupChange(frm) {
	// Destructive cascading belongs only to an explicit parent-field change, not
	// form refresh. This prevents saved schedules becoming dirty merely by opening.
	if (!frm.doc.student_group) {
		frm.__eduedge_student_group_program = "";
		frm.__eduedge_applying_group_context = true;
		try {
			await frm.set_value({ eduedge_school_branch: null, course: null, instructor: null, room: null });
		} finally {
			frm.__eduedge_applying_group_context = false;
		}
		setCourseScheduleQueries(frm);
		return;
	}
	const message = await getStudentGroupContext(frm);
	if (!message) return;
	frm.__eduedge_student_group_program = message.program || "";
	const fixedCourse = message.group_based_on === "Course" ? (message.course || null) : null;
	frm.__eduedge_applying_group_context = true;
	try {
		await frm.set_value({
			eduedge_school_branch: message.eduedge_school_branch || null,
			course: fixedCourse,
			instructor: null,
			room: null,
		});
	} finally {
		frm.__eduedge_applying_group_context = false;
	}
	setCourseScheduleQueries(frm);
}

frappe.ui.form.on("Course Schedule", {
	setup(frm) { setCourseScheduleQueries(frm); },
	refresh(frm) {
		frm.set_df_property("student_group", "label", frappe.eduedge?.term?.("student_group", { fallback: __("Student Group / Class Arm / Level") }) || __("Student Group / Class Arm / Level"));
		frm.set_df_property("course", "label", frappe.eduedge?.term?.("course", { fallback: __("Course / Subject") }) || __("Course / Subject"));
		frm.set_df_property("instructor", "label", frappe.eduedge?.term?.("instructor", { fallback: __("Instructor") }) || __("Instructor"));
		frm.set_df_property("room", "label", frappe.eduedge?.term?.("room", { fallback: __("Room") }) || __("Room"));
		if (frm.doc.student_group) hydrateStudentGroupContext(frm);
		else setCourseScheduleQueries(frm);
	},
	student_group(frm) { applyStudentGroupChange(frm); },
	async course(frm) {
		if (frm.__eduedge_applying_group_context) {
			setCourseScheduleQueries(frm);
			return;
		}
		await frm.set_value("instructor", null);
		setCourseScheduleQueries(frm);
	},
	async schedule_date(frm) {
		frm.__eduedge_student_group_program = "";
		await frm.set_value({ student_group: null, course: null, instructor: null, room: null, eduedge_school_branch: null });
		setCourseScheduleQueries(frm);
	},
	async eduedge_school_branch(frm) {
		if (frm.__eduedge_applying_group_context) {
			setCourseScheduleQueries(frm);
			return;
		}
		if (frm.doc.student_group) {
			const { message } = await frappe.db.get_value("Student Group", frm.doc.student_group, "eduedge_school_branch");
			if (message?.eduedge_school_branch !== frm.doc.eduedge_school_branch) {
				frm.__eduedge_student_group_program = "";
				await frm.set_value({ student_group: null, course: null });
			}
		}
		await frm.set_value({ instructor: null, room: null });
		setCourseScheduleQueries(frm);
	},
});