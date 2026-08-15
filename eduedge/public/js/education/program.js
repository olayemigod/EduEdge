async function applyProgramTerminology(frm) {
	const requestId = (frm.__eduedgeTerminologyRequestId || 0) + 1;
	frm.__eduedgeTerminologyRequestId = requestId;
	let context = frappe.boot?.eduedge_institution_context || {};
	try {
		const response = await frappe.call("eduedge.api.programmes.get_programme_terminology", {
			institution: frm.doc.eduedge_institution || undefined,
		});
		if (frm.__eduedgeTerminologyRequestId !== requestId) return;
		context = response.message || context;
	} catch (_error) {
		if (frm.__eduedgeTerminologyRequestId !== requestId) return;
	}

	const term = (key, plural, fallback) =>
		frappe.eduedge?.term?.(key, { plural, context, fallback }) || fallback;
	const programme = term("programme", false, __("Program"));
	const department = term("department", false, __("Department"));
	const academicSection = term("academic_section", false, __("Academic Section"));
	const coursePlural = term("course", true, __("Courses"));

	frm.set_df_property("program_name", "label", `${programme} Name`);
	frm.set_df_property("program_abbreviation", "label", `${programme} Abbreviation`);
	frm.set_df_property("department", "label", department);
	if (frm.fields_dict.courses) frm.set_df_property("courses", "label", coursePlural);
	if (frm.fields_dict.eduedge_academic_section) {
		frm.set_df_property("eduedge_academic_section", "label", academicSection);
	}
	if (frm.fields_dict.eduedge_next_program) {
		frm.set_df_property("eduedge_next_program", "label", `Next ${programme}`);
	}
	if (frm.fields_dict.eduedge_terminal_program) {
		frm.set_df_property("eduedge_terminal_program", "label", `Terminal ${programme}`);
	}
	for (const fieldname of [
		"program_name", "program_abbreviation", "department", "courses", "eduedge_academic_section",
		"eduedge_next_program", "eduedge_terminal_program",
	]) {
		if (frm.fields_dict[fieldname]) frm.refresh_field(fieldname);
	}
}

function setupProgressionQueries(frm) {
	if (frm.fields_dict.eduedge_next_program) {
		frm.set_query("eduedge_next_program", () => ({
			filters: {
				eduedge_institution: frm.doc.eduedge_institution || "",
				name: ["!=", frm.doc.name || ""],
			},
		}));
	}
}

function addProgressionAction(frm) {
	if (frm.is_new() || !frm.doc.name) return;
	if (!frm.fields_dict.eduedge_progression_mode) return;
	frm.add_custom_button(__("Student Progression"), () => {
		const params = new URLSearchParams({ program: frm.doc.name });
		window.location.href = `/app/eduedge-student-progression?${params.toString()}`;
	}, __("Academic Progression"));
}

frappe.ui.form.on("Program", {
	setup(frm) {
		frm.set_query("eduedge_academic_section", () => ({
			query: "eduedge.api.academic_context.institution_scoped_query",
			filters: { institution: frm.doc.eduedge_institution },
		}));
		setupProgressionQueries(frm);
	},

	refresh(frm) {
		applyProgramTerminology(frm);
		setupProgressionQueries(frm);
		addProgressionAction(frm);
	},

	eduedge_institution(frm) {
		const updates = {};
		if (frm.doc.department) updates.department = null;
		if (frm.doc.eduedge_academic_section) updates.eduedge_academic_section = null;
		if (frm.doc.eduedge_next_program) updates.eduedge_next_program = null;
		const apply = Object.keys(updates).length ? frm.set_value(updates) : Promise.resolve();
		Promise.resolve(apply).finally(() => {
			setupProgressionQueries(frm);
			applyProgramTerminology(frm);
		});
	},

	eduedge_progression_mode(frm) {
		if (frm.doc.eduedge_progression_mode !== "Program Promotion" && frm.doc.eduedge_next_program) {
			frm.set_value("eduedge_next_program", null);
		}
	},

	eduedge_terminal_program(frm) {
		if (frm.doc.eduedge_terminal_program && frm.doc.eduedge_next_program) {
			frm.set_value("eduedge_next_program", null);
		}
	},
});
