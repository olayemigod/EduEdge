const TERMINAL_METRIC_BASES = new Set([
	"Current Term Raw Score",
	"Current Term Percentage",
	"Year-to-Date Cumulative Raw Score",
	"Year-to-Date Cumulative Percentage",
]);

const ANNUAL_METRIC_BASES = new Set([
	"Year-to-Date Cumulative Raw Score",
	"Year-to-Date Cumulative Percentage",
	"Annual Cumulative Raw Score",
	"Annual Cumulative Percentage",
	"Annual Average Percentage",
]);

function reconcileMetricSurfaces(frm, cdt, cdn) {
	const row = locals[cdt]?.[cdn];
	if (!row?.calculation_basis) return;

	const updates = [];
	if (row.show_on_terminal && !TERMINAL_METRIC_BASES.has(row.calculation_basis)) {
		updates.push(
			frappe.model.set_value(cdt, cdn, "show_on_terminal", 0)
		);
	}
	if (row.show_on_annual && !ANNUAL_METRIC_BASES.has(row.calculation_basis)) {
		updates.push(
			frappe.model.set_value(cdt, cdn, "show_on_annual", 0)
		);
	}
	if (!updates.length) return;

	Promise.all(updates).then(() => {
		frm.refresh_field("metrics");
		frappe.show_alert({
			message: __(
				"Metric visibility was adjusted because {0} is not available on every selected report surface.",
				[row.calculation_basis]
			),
			indicator: "orange",
		});
	});
}

function refreshComponentKeyOptions(frm) {
	const keys = (frm.doc.components || [])
		.map((row) => (row.component_key || "").trim().toLowerCase())
		.filter(Boolean);
	const df = frappe.meta.get_docfield("EduEdge Result Component Source", "component_key", frm.doc.name);
	if (df) df.options = ["", ...new Set(keys)].join("\n");
	frm.refresh_field("component_sources");
}

function setResultProfileQueries(frm) {
	frm.set_query("school_branch", () => ({
		filters: {
			institution: frm.doc.institution || "",
			enabled: 1,
		},
	}));
	frm.set_query("grading_scale", () => ({
		filters: {
			eduedge_institution: frm.doc.institution || "",
		},
	}));
	frm.set_query("assessment_group", "component_sources", () => ({
		filters: {
			eduedge_institution: frm.doc.institution || "",
		},
	}));
}

frappe.ui.form.on("EduEdge Result Profile", {
	setup(frm) {
		setResultProfileQueries(frm);
	},
	refresh(frm) {
		setResultProfileQueries(frm);
		refreshComponentKeyOptions(frm);
		if (frm.fields_dict.component_sources) {
			frm.fields_dict.component_sources.grid.wrapper.attr(
				"title",
				__("Assessment Groups are native Frappe Education sources; Result Components only control how they are composed on EduEdge reports.")
			);
		}
	},
	institution(frm) {
		if (frm.__eduedge_setting_institution) return;
		frm.__eduedge_setting_institution = true;
		Promise.resolve()
			.then(async () => {
				if (frm.doc.school_branch) await frm.set_value("school_branch", null);
				if (frm.doc.grading_scale) await frm.set_value("grading_scale", null);
				if ((frm.doc.component_sources || []).length) {
					frm.clear_table("component_sources");
					frm.refresh_field("component_sources");
				}
				setResultProfileQueries(frm);
			})
			.finally(() => {
				frm.__eduedge_setting_institution = false;
			});
	},
	components_add(frm) {
		refreshComponentKeyOptions(frm);
	},
	components_remove(frm) {
		refreshComponentKeyOptions(frm);
	},
	annual_aggregation_method(frm) {
		if (frm.doc.annual_aggregation_method === "Weighted Average") {
			frappe.show_alert({
				message: __("Configure each period weight on the Institution Academic Calendar."),
				indicator: "blue",
			});
		}
	},
});

frappe.ui.form.on("EduEdge Result Component", {
	component_key(frm) {
		refreshComponentKeyOptions(frm);
	},
});

frappe.ui.form.on("EduEdge Result Metric", {
	calculation_basis(frm, cdt, cdn) {
		reconcileMetricSurfaces(frm, cdt, cdn);
	},
	show_on_terminal(frm, cdt, cdn) {
		reconcileMetricSurfaces(frm, cdt, cdn);
	},
	show_on_annual(frm, cdt, cdn) {
		reconcileMetricSurfaces(frm, cdt, cdn);
	},
});
