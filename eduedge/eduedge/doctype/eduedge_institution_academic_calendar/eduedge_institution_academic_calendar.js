async function getAcademicYearDefaults(academicYear) {
	if (!academicYear) return null;
	const response = await frappe.db.get_value(
		"Academic Year",
		academicYear,
		["year_start_date", "year_end_date"],
	);
	return response?.message || null;
}

async function getAcademicTerms(academicYear) {
	if (!academicYear) return [];
	return frappe.db.get_list("Academic Term", {
		filters: { academic_year: academicYear },
		fields: ["name", "term_start_date", "term_end_date"],
		order_by: "term_start_date asc, name asc",
		limit: 0,
	});
}

async function applyAcademicYearDefaults(frm) {
	if (!frm.doc.academic_year) {
		await frm.set_value("start_date", null);
		await frm.set_value("end_date", null);
		frm.clear_table("periods");
		frm.refresh_field("periods");
		return;
	}

	const [year, terms] = await Promise.all([
		getAcademicYearDefaults(frm.doc.academic_year),
		getAcademicTerms(frm.doc.academic_year),
	]);
	if (!year) return;

	await frm.set_value("start_date", year.year_start_date || null);
	await frm.set_value("end_date", year.year_end_date || null);
	frm.clear_table("periods");
	terms.forEach((term, index) => {
		const row = frm.add_child("periods");
		row.academic_term = term.name;
		row.start_date = term.term_start_date || null;
		row.end_date = term.term_end_date || null;
		row.sequence = (index + 1) * 10;
	});
	frm.refresh_field("periods");

	if (!terms.length) {
		frappe.show_alert({
			message: __("No Academic Terms are configured for the selected Academic Year."),
			indicator: "orange",
		});
	}
}

async function applyAcademicTermDefaults(cdt, cdn) {
	const row = frappe.get_doc(cdt, cdn);
	if (!row?.academic_term) return;
	const response = await frappe.db.get_value(
		"Academic Term",
		row.academic_term,
		["academic_year", "term_start_date", "term_end_date"],
	);
	const term = response?.message;
	if (!term) return;
	const parent = locals[row.parenttype]?.[row.parent];
	if (parent?.academic_year && term.academic_year !== parent.academic_year) {
		await frappe.model.set_value(cdt, cdn, "academic_term", null);
		frappe.throw(__("Select an Academic Term that belongs to the calendar Academic Year."));
	}
	await frappe.model.set_value(cdt, cdn, "start_date", term.term_start_date || null);
	await frappe.model.set_value(cdt, cdn, "end_date", term.term_end_date || null);
}

frappe.ui.form.on("EduEdge Institution Academic Calendar", {
	setup(frm) {
		frm.set_query("academic_term", "periods", () => ({
			filters: { academic_year: frm.doc.academic_year || "" },
		}));
	},
	refresh(frm) {
		const locked = !frm.is_new();
		frm.set_df_property("institution", "read_only", locked ? 1 : 0);
		frm.set_df_property("academic_year", "read_only", locked ? 1 : 0);
	},
	async academic_year(frm) {
		if (!frm.is_new()) return;
		try {
			await applyAcademicYearDefaults(frm);
		} catch (error) {
			frappe.show_alert({
				message: error?.message || __("Academic Year defaults could not be loaded."),
				indicator: "red",
			});
		}
	},
});

frappe.ui.form.on("EduEdge Academic Calendar Period", {
	async academic_term(frm, cdt, cdn) {
		try {
			await applyAcademicTermDefaults(cdt, cdn);
		} catch (error) {
			frappe.show_alert({
				message: error?.message || __("Academic Term dates could not be loaded."),
				indicator: "red",
			});
		}
	},
});
