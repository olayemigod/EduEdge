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
		query: "eduedge.api.academic_operations.instructor_query",
		filters: { eduedge_school_branch: frm.doc.eduedge_school_branch, reference_date: frm.doc.schedule_date },
	}));
	frm.set_query("room", () => ({
		query: "eduedge.api.academic_operations.room_query",
		filters: { eduedge_school_branch: frm.doc.eduedge_school_branch },
	}));
}

async function applyStudentGroupContext(frm) {
	if (!frm.doc.student_group) {
		frm.__eduedge_student_group_program = "";
		await frm.set_value({ eduedge_school_branch: null, course: null, instructor: null, room: null });
		setCourseScheduleQueries(frm);
		return;
	}
	const selectedGroup = frm.doc.student_group;
	const { message } = await frappe.db.get_value("Student Group", selectedGroup, ["eduedge_school_branch", "program", "course"]);
	if (frm.doc.student_group !== selectedGroup) return;
	frm.__eduedge_student_group_program = message?.program || "";
	await frm.set_value({
		eduedge_school_branch: message?.eduedge_school_branch || null,
		course: message?.course || null,
		instructor: null,
		room: null,
	});
	setCourseScheduleQueries(frm);
}

frappe.ui.form.on("Course Schedule", {
	setup(frm) { setCourseScheduleQueries(frm); },
	refresh(frm) {
		frm.set_df_property("student_group", "label", frappe.eduedge?.term?.("student_group", { fallback: __("Student Group / Class Arm / Level") }) || __("Student Group / Class Arm / Level"));
		frm.set_df_property("course", "label", frappe.eduedge?.term?.("course", { fallback: __("Course / Subject") }) || __("Course / Subject"));
		frm.set_df_property("instructor", "label", frappe.eduedge?.term?.("instructor", { fallback: __("Instructor") }) || __("Instructor"));
		frm.set_df_property("room", "label", frappe.eduedge?.term?.("room", { fallback: __("Room") }) || __("Room"));
		if (frm.doc.student_group) applyStudentGroupContext(frm);
		else setCourseScheduleQueries(frm);
	},
	student_group(frm) { applyStudentGroupContext(frm); },
	async schedule_date(frm) {
		frm.__eduedge_student_group_program = "";
		await frm.set_value({ student_group: null, course: null, instructor: null, room: null, eduedge_school_branch: null });
		setCourseScheduleQueries(frm);
	},
	async eduedge_school_branch(frm) {
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
