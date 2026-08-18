(() => {
	const DIALOG_VERSION = "1.0.0";
	const CONTEXT_METHOD = "eduedge.api.calendar_setup.get_calendar_dialog_context";
	const CREATE_METHOD = "eduedge.api.calendar_setup.create_calendar_from_foundation";

	function escapeHtml(value) {
		if (typeof frappe.utils?.escape_html === "function") {
			return frappe.utils.escape_html(String(value || ""));
		}
		return $("<div>").text(String(value || "")).html();
	}

	function formatDate(value) {
		if (!value) return __("Not set");
		return typeof frappe.datetime?.str_to_user === "function"
			? frappe.datetime.str_to_user(value)
			: String(value);
	}

	async function getContext(institution, academicYear = "") {
		const response = await frappe.call({
			method: CONTEXT_METHOD,
			args: {
				institution,
				academic_year: academicYear || undefined,
			},
		});
		return response.message || {};
	}

	function setPrimaryEnabled(dialog, enabled) {
		dialog.get_primary_btn()?.prop("disabled", !enabled);
	}

	function renderPreview(dialog, preview, academicTermLabel) {
		const wrapper = dialog.fields_dict.term_summary?.$wrapper;
		if (!wrapper) return;
		if (!preview) {
			wrapper.html(`<div class="text-muted">${__("Select an Academic Year to load its dates and Terms.")}</div>`);
			return;
		}
		const periods = preview.periods || [];
		if (preview.existing_calendar) {
			wrapper.html(
				`<div class="alert alert-warning mb-0">${__("A calendar already exists for this Institution and Academic Year: {0}", [escapeHtml(preview.existing_calendar)])}</div>`,
			);
			return;
		}
		if (!periods.length) {
			wrapper.html(
				`<div class="alert alert-warning mb-0">${__("No Academic Terms are configured for this Academic Year. Create the Terms before creating the Institution calendar.")}</div>`,
			);
			return;
		}
		const rows = periods
			.map(
				(period) => `
					<tr>
						<td><strong>${escapeHtml(period.academic_term)}</strong></td>
						<td>${escapeHtml(formatDate(period.start_date))}</td>
						<td>${escapeHtml(formatDate(period.end_date))}</td>
					</tr>`,
			)
			.join("");
		wrapper.html(`
			<div class="eduedge-calendar-dialog-preview">
				<div class="d-flex align-items-center justify-content-between mb-2">
					<strong>${escapeHtml(academicTermLabel || __("Academic Terms"))}</strong>
					<span class="text-muted">${periods.length} ${periods.length === 1 ? __("period") : __("periods")}</span>
				</div>
				<div class="table-responsive">
					<table class="table table-bordered table-sm mb-0">
						<thead><tr><th>${__("Term")}</th><th>${__("Start Date")}</th><th>${__("End Date")}</th></tr></thead>
						<tbody>${rows}</tbody>
					</table>
				</div>
			</div>
		`);
	}

	async function open(options = {}) {
		const institution = String(options.institution || "").trim();
		if (!institution) {
			frappe.show_alert({ message: __("Select an Institution first."), indicator: "orange" });
			return null;
		}

		let initial;
		try {
			initial = await getContext(institution);
		} catch (error) {
			frappe.show_alert({
				message: error?.message || __("Calendar setup could not be loaded."),
				indicator: "red",
			});
			return null;
		}

		const availableYears = (initial.academic_year_options || []).filter((row) => row.available);
		if (!availableYears.length) {
			frappe.msgprint({
				title: __("No Available Academic Year"),
				message: __("Every readable Academic Year already has an Institution calendar, or no Academic Year is configured."),
				indicator: "orange",
			});
			return null;
		}

		const dialog = new frappe.ui.Dialog({
			title: options.title || __("New Institution Academic Calendar"),
			size: "large",
			fields: [
				{
					fieldname: "institution_display",
					fieldtype: "Data",
					label: __("Institution"),
					read_only: 1,
					default: options.institutionLabel || initial.institution?.institution_name || institution,
				},
				{
					fieldname: "academic_year",
					fieldtype: "Select",
					label: options.academicYearLabel || __("Academic Year"),
					options: ["", ...availableYears.map((row) => row.value)].join("\n"),
					reqd: 1,
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "is_current",
					fieldtype: "Check",
					label: __("Set as Current Calendar"),
					default: initial.has_current_calendar ? 0 : 1,
				},
				{
					fieldname: "notes",
					fieldtype: "Small Text",
					label: __("Notes"),
				},
				{ fieldtype: "Section Break", label: __("Derived Calendar Dates") },
				{
					fieldname: "start_date",
					fieldtype: "Date",
					label: __("Start Date"),
					read_only: 1,
				},
				{
					fieldname: "end_date",
					fieldtype: "Date",
					label: __("End Date"),
					read_only: 1,
				},
				{ fieldtype: "Section Break", label: options.academicTermLabel || __("Academic Terms") },
				{
					fieldname: "term_summary",
					fieldtype: "HTML",
				},
			],
		});

		dialog.__eduedgeCalendarPreview = null;
		dialog.__eduedgeCalendarRequest = 0;
		renderPreview(dialog, null, options.academicTermLabel);
		setPrimaryEnabled(dialog, false);

		const loadPreview = async () => {
			const academicYear = String(dialog.get_value("academic_year") || "").trim();
			const requestId = ++dialog.__eduedgeCalendarRequest;
			dialog.__eduedgeCalendarPreview = null;
			await dialog.set_value("start_date", "");
			await dialog.set_value("end_date", "");
			setPrimaryEnabled(dialog, false);
			renderPreview(dialog, null, options.academicTermLabel);
			if (!academicYear) return;

			try {
				const context = await getContext(institution, academicYear);
				if (requestId !== dialog.__eduedgeCalendarRequest) return;
				const preview = context.preview || null;
				dialog.__eduedgeCalendarPreview = preview;
				await dialog.set_value("start_date", preview?.start_date || "");
				await dialog.set_value("end_date", preview?.end_date || "");
				renderPreview(dialog, preview, options.academicTermLabel);
				const periods = preview?.periods || [];
				const complete = Boolean(
					preview
					&& !preview.existing_calendar
					&& preview.start_date
					&& preview.end_date
					&& periods.length
					&& periods.every((row) => row.start_date && row.end_date),
				);
				setPrimaryEnabled(dialog, complete);
			} catch (error) {
				if (requestId !== dialog.__eduedgeCalendarRequest) return;
				dialog.fields_dict.term_summary?.$wrapper.html(
					`<div class="alert alert-danger mb-0">${escapeHtml(error?.message || __("Calendar dates and Terms could not be loaded."))}</div>`,
				);
			}
		};

		dialog.fields_dict.academic_year.$input
			.off("change.eduedgeAcademicFoundationCalendar")
			.on("change.eduedgeAcademicFoundationCalendar", () => {
				setTimeout(loadPreview, 0);
			});

		dialog.set_primary_action(__("Create Calendar"), async () => {
			const values = dialog.get_values();
			const preview = dialog.__eduedgeCalendarPreview;
			if (!values || !preview || preview.existing_calendar || !(preview.periods || []).length) return;
			dialog.get_primary_btn().prop("disabled", true);
			dialog.get_primary_btn().text(__("Creating..."));
			try {
				const response = await frappe.call({
					method: CREATE_METHOD,
					type: "POST",
					args: {
						institution,
						academic_year: values.academic_year,
						is_current: values.is_current ? 1 : 0,
						notes: values.notes || "",
					},
				});
				const calendar = response.message || {};
				dialog.hide();
				frappe.show_alert({ message: __("Institution Academic Calendar created"), indicator: "green" });
				if (typeof options.onCreated === "function") await options.onCreated(calendar);
			} catch (error) {
				frappe.show_alert({
					message: error?.message || __("The Institution Academic Calendar could not be created."),
					indicator: "red",
				});
				setPrimaryEnabled(dialog, true);
			} finally {
				dialog.get_primary_btn().text(__("Create Calendar"));
			}
		});

		dialog.show();
		return dialog;
	}

	window.EduEdgeAcademicCalendarDialog = {
		version: DIALOG_VERSION,
		open,
	};
})();
