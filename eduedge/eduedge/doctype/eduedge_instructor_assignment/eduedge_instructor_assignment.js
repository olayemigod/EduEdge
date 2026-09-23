const CLASS_SCOPE = "Class / Programme Offering";
const CLASS_ARM_SCOPE = "Class Arm";
const COURSE_REQUIRED_TYPES = new Set([
	"Subject Instructor",
	"Lecturer",
	"Tutor",
	"Practical Instructor",
	"Assistant Instructor",
]);
const CLASS_RESPONSIBILITY_TYPES = new Set([
	"Class Teacher",
	"Form Teacher",
	"Head of Class / Level",
]);
const IMMUTABLE_FIELDS = [
	"instructor",
	"assignment_type",
	"assignment_scope",
	"school_branch",
	"program_offering",
	"student_group",
	"course",
	"valid_from",
	"valid_to",
];

function clearFields(frm, fields) {
	const updates = {};
	for (const fieldname of fields) {
		if (frm.doc[fieldname]) updates[fieldname] = null;
	}
	if (Object.keys(updates).length) return frm.set_value(updates);
	return Promise.resolve();
}

function lockExistingResponsibility(frm) {
	const locked = !frm.is_new();
	for (const fieldname of IMMUTABLE_FIELDS) {
		frm.set_df_property(fieldname, "read_only", locked ? 1 : 0);
	}
}

function governedFilters(frm) {
	return {
		instructor: frm.doc.instructor || "",
		school_branch: frm.doc.school_branch || "",
		program_offering: frm.doc.program_offering || "",
	};
}

async function applyOfferingContext(frm) {
	if (!frm.doc.instructor || !frm.doc.school_branch || !frm.doc.program_offering) return;
	const response = await frappe.call({
		method: "eduedge.api.instructor_assignment_link_search.get_assignment_offering_context",
		args: {
			instructor: frm.doc.instructor,
			branch: frm.doc.school_branch,
			program_offering: frm.doc.program_offering,
		},
	});
	const row = response?.message || {};
	if (!row.school_branch) return;
	if (frm.doc.school_branch && frm.doc.school_branch !== row.school_branch) {
		await frm.set_value("program_offering", null);
		return;
	}
	const partial = row.branch_eligibility_full_period === false;
	frm.set_df_property(
		"valid_from",
		"description",
		partial
			? __("This Class only partially overlaps Branch Eligibility. Enter dates within the governed period.")
			: "",
	);
	frm.set_df_property(
		"valid_to",
		"description",
		partial
			? __("This Class only partially overlaps Branch Eligibility. Enter dates within the governed period.")
			: "",
	);
	await frm.set_value({
		school_branch: row.school_branch,
		institution: row.institution || null,
		academic_year: row.academic_year || null,
		academic_term: row.academic_term || null,
		valid_from: partial ? null : (row.period_start_date || null),
		valid_to: partial ? null : (row.period_end_date || null),
	});
}


frappe.ui.form.on("EduEdge Instructor Assignment", {
	setup(frm) {
		frm.set_query("instructor", () => ({
			query: "eduedge.api.instructor_assignment_link_search.instructor_assignment_instructor_query",
		}));
		frm.set_query("school_branch", () => ({
			query: "eduedge.api.instructor_assignment_link_search.instructor_assignment_branch_query",
			filters: { instructor: frm.doc.instructor || "" },
		}));
		frm.set_query("program_offering", () => ({
			query: "eduedge.api.instructor_assignment_link_search.instructor_assignment_offering_query",
			filters: governedFilters(frm),
		}));
		frm.set_query("student_group", () => ({
			query: "eduedge.api.instructor_assignment_link_search.instructor_assignment_class_arm_query",
			filters: governedFilters(frm),
		}));
		frm.set_query("course", () => ({
			query: "eduedge.api.instructor_assignment_link_search.instructor_assignment_course_query",
			filters: governedFilters(frm),
		}));
	},

	refresh(frm) {
		lockExistingResponsibility(frm);
		if (!frm.is_new()) {
			frm.set_intro(
				__("Responsibility identity is historical. Use EduEdge End, Replace, Transfer, Prepare, Disable or Re-enable actions instead of editing it in place."),
				"blue",
			);
		}
	},

	async instructor(frm) {
		if (!frm.is_new()) return;
		await clearFields(frm, [
			"school_branch",
			"program_offering",
			"student_group",
			"course",
			"institution",
			"academic_year",
			"academic_term",
			"valid_from",
			"valid_to",
		]);
	},

	async school_branch(frm) {
		if (!frm.is_new()) return;
		await clearFields(frm, [
			"program_offering",
			"student_group",
			"course",
			"institution",
			"academic_year",
			"academic_term",
			"valid_from",
			"valid_to",
		]);
	},

	async program_offering(frm) {
		if (!frm.is_new()) return;
		await clearFields(frm, ["student_group", "course", "valid_from", "valid_to"]);
		await applyOfferingContext(frm);
	},

	async assignment_scope(frm) {
		if (!frm.is_new()) return;
		if (frm.doc.assignment_scope === CLASS_SCOPE) {
			await frm.set_value("student_group", null);
		}
	},

	async assignment_type(frm) {
		if (!frm.is_new()) return;
		const type = frm.doc.assignment_type || "";
		if (CLASS_RESPONSIBILITY_TYPES.has(type)) {
			await frm.set_value("course", null);
		}
		if (["Class Teacher", "Form Teacher"].includes(type)) {
			await frm.set_value("assignment_scope", CLASS_ARM_SCOPE);
		}
		if (type === "Head of Class / Level") {
			await frm.set_value("assignment_scope", CLASS_SCOPE);
			await frm.set_value("student_group", null);
		}
		if (COURSE_REQUIRED_TYPES.has(type) && !frm.doc.course) {
			frm.set_df_property("course", "description", __("Select only a Subject / Course configured in the selected Class curriculum. Use the EduEdge Instructor Assignments planner to add a new Institution Subject to curriculum during assignment."));
		}
	},
});
