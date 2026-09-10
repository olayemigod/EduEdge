function setupAcademicLevelQueries(frm) {
	frm.set_query("program", () => ({
		filters: {
			eduedge_institution: frm.doc.institution || "",
			eduedge_progression_mode: "Level Progression",
		},
	}));
	frm.set_query("next_level", () => ({
		filters: {
			institution: frm.doc.institution || "",
			program: frm.doc.program || "",
			enabled: 1,
			name: ["!=", frm.doc.name || ""],
		},
	}));
}

frappe.ui.form.on("EduEdge Academic Level", {
	setup(frm) {
		setupAcademicLevelQueries(frm);
	},

	refresh(frm) {
		setupAcademicLevelQueries(frm);
		if (!frm.is_new() && frm.doc.program) {
			frm.add_custom_button(__("Open Programme"), () => {
				frappe.set_route("Form", "Program", frm.doc.program);
			}, __("Academic Progression"));
			frm.add_custom_button(__("Student Progression"), () => {
				const params = new URLSearchParams({ program: frm.doc.program });
				window.location.href = `/app/eduedge-student-progression?${params.toString()}`;
			}, __("Academic Progression"));
		}
	},

	institution(frm) {
		const updates = {};
		if (frm.doc.program) updates.program = null;
		if (frm.doc.next_level) updates.next_level = null;
		const apply = Object.keys(updates).length ? frm.set_value(updates) : Promise.resolve();
		Promise.resolve(apply).finally(() => setupAcademicLevelQueries(frm));
	},

	program(frm) {
		if (frm.doc.next_level) frm.set_value("next_level", null);
		setupAcademicLevelQueries(frm);
	},

	is_terminal(frm) {
		if (frm.doc.is_terminal && frm.doc.next_level) frm.set_value("next_level", null);
	},
});
