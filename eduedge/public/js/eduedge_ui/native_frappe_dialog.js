function errorMessage(error, fallback) {
	return error?.message || error?._server_messages || error?.exc_type || fallback;
}

function conditionMatches(condition, values = {}) {
	if (!condition || !condition.field) return true;
	const actual = values[condition.field];
	if (Object.prototype.hasOwnProperty.call(condition, "equals")) {
		return String(actual ?? "") === String(condition.equals ?? "");
	}
	if (Object.prototype.hasOwnProperty.call(condition, "not_equals")) {
		return String(actual ?? "") !== String(condition.not_equals ?? "");
	}
	if (Array.isArray(condition.in)) return condition.in.map(String).includes(String(actual ?? ""));
	if (condition.truthy) return Boolean(actual);
	if (condition.falsy) return !actual;
	return true;
}

function normalizeOptions(options) {
	const source = Array.isArray(options)
		? options
		: typeof options === "string"
			? options.split("\n")
			: [];
	return source
		.filter((option) => option !== undefined && option !== null && option !== "")
		.map((option) =>
			typeof option === "object"
				? {
					value: String(option.value ?? option.name ?? ""),
					label: String(option.label ?? option.value ?? option.name ?? ""),
					description: String(option.description ?? ""),
				}
				: { value: String(option), label: String(option), description: "" }
		)
		.filter((option) => option.value);
}

function fieldType(field) {
	return String(field?.type || field?.fieldtype || "Data");
}

function dialogValues(dialog, fields = []) {
	const values = {};
	for (const field of fields) {
		if (!field?.fieldname) continue;
		values[field.fieldname] = dialog.get_value(field.fieldname);
	}
	return values;
}

function setControlOptions(control, options) {
	if (!control) return;
	const normalized = normalizeOptions(options);
	if (typeof control.set_data === "function") {
		control.set_data(normalized);
		return;
	}
	control.df.options = normalized;
	control.refresh?.();
}

function toDialogField(field, state) {
	const sourceType = fieldType(field);
	const isLink = sourceType === "Link";
	const config = {
		fieldname: field.fieldname,
		label: field.label || field.fieldname,
		fieldtype: isLink ? "Autocomplete" : sourceType,
		reqd: Boolean(field.required || field.reqd),
		read_only: Boolean(field.read_only),
		hidden: Boolean(field.hidden),
		default: field.default,
		description: field.description || field.help || "",
		placeholder: field.placeholder || "",
	};
	if (sourceType === "Select") {
		config.options = normalizeOptions(field.options).map((option) => option.value).join("\n");
	} else if (isLink || sourceType === "Autocomplete") {
		config.options = normalizeOptions(field.options);
	} else if (field.options && typeof field.options === "string") {
		config.options = field.options;
	}
	config.onchange = async () => {
		if (!state.dialog) return;
		for (const fieldname of field.clear_fields || []) {
			if (fieldname !== field.fieldname) await state.dialog.set_value(fieldname, "");
		}
		state.refreshFieldStates();
		for (const fieldname of field.refresh_fields || []) {
			await state.refreshOptions(fieldname, "");
		}
	};
	return config;
}

function showLoadingDialog(title) {
	const dialog = new frappe.ui.Dialog({
		title: title || __("Loading form"),
		fields: [
			{
				fieldname: "loading_html",
				fieldtype: "HTML",
				options: '<div style="display:flex;align-items:center;justify-content:center;min-height:7rem;gap:.65rem"><span class="spinner-border spinner-border-sm" aria-hidden="true"></span><span>Loading form…</span></div>',
			},
		],
	});
	dialog.show();
	return dialog;
}

export async function openNativeSchemaDialog({
	loadingTitle = "Loading form",
	loadMethod,
	loadArgs = {},
	saveMethod,
	buildSaveArgs,
	searchMethod = "",
	buildSearchArgs,
	onSaved,
} = {}) {
	if (!frappe?.ui?.Dialog) {
		frappe.msgprint(__("Frappe dialog services are unavailable on this page."));
		return null;
	}

	const loadingDialog = showLoadingDialog(loadingTitle);
	let schema;
	try {
		const response = await frappe.call(loadMethod, loadArgs);
		schema = response.message || {};
	} catch (error) {
		loadingDialog.hide();
		frappe.msgprint({
			title: __("Form could not load"),
			message: errorMessage(error, __("The form definition could not be loaded.")),
			indicator: "red",
		});
		return null;
	}
	loadingDialog.hide();

	const schemaFields = Array.isArray(schema.fields) ? schema.fields : [];
	const state = {
		dialog: null,
		searchTimers: {},
		refreshFieldStates: () => {},
		refreshOptions: async () => {},
	};
	const dialogFields = schemaFields.map((field) => toDialogField(field, state));
	if (schema.subtitle || schema.advanced_note) {
		dialogFields.unshift({
			fieldname: "eduedge_dialog_guidance",
			fieldtype: "HTML",
			options: `<div class="text-muted" style="margin-bottom:.5rem">${frappe.utils.escape_html([schema.subtitle, schema.advanced_note].filter(Boolean).join(" "))}</div>`,
		});
	}

	const canSave = schema.can_save !== false;
	const fullFormRoute = String(schema.full_form_route || "").trim();
	const dialog = new frappe.ui.Dialog({
		title: schema.title || __("Edit record"),
		fields: dialogFields,
		primary_action_label: canSave ? schema.submit_label || __("Save") : undefined,
		primary_action: canSave
			? async () => {
				const values = dialog.get_values();
				if (!values) return;
				dialog.disable_primary_action();
				try {
					const response = await frappe.call(saveMethod, buildSaveArgs(values, schema));
					dialog.hide();
					await onSaved?.(response.message || null, schema);
				} catch (error) {
					frappe.msgprint({
						title: __("Record could not be saved"),
						message: errorMessage(error, __("The record could not be saved.")),
						indicator: "red",
					});
				} finally {
					dialog.enable_primary_action();
				}
			}
			: undefined,
		secondary_action_label: fullFormRoute ? __("Open full form") : undefined,
		secondary_action: fullFormRoute
			? () => window.open(fullFormRoute.startsWith("/") ? fullFormRoute : `/${fullFormRoute}`, "_blank", "noopener,noreferrer")
			: undefined,
	});
	state.dialog = dialog;

	state.refreshFieldStates = () => {
		const values = dialogValues(dialog, schemaFields);
		for (const field of schemaFields) {
			if (!field?.fieldname || !dialog.fields_dict[field.fieldname]) continue;
			const visible = !field.hidden && conditionMatches(field.visible_when, values);
			const required = Boolean(field.required || field.reqd || (field.required_when && conditionMatches(field.required_when, values)));
			dialog.set_df_property(field.fieldname, "hidden", !visible);
			dialog.set_df_property(field.fieldname, "reqd", required);
		}
	};

	state.refreshOptions = async (fieldname, query = "") => {
		if (!searchMethod || !buildSearchArgs) return;
		const field = schemaFields.find((item) => item.fieldname === fieldname);
		const control = dialog.fields_dict[fieldname];
		if (!field || !control) return;
		try {
			const response = await frappe.call(searchMethod, buildSearchArgs(field, query, dialogValues(dialog, schemaFields), schema));
			setControlOptions(control, response.message || []);
		} catch (error) {
			frappe.show_alert({ message: errorMessage(error, __(`Options for ${field.label || fieldname} could not be loaded.`)), indicator: "red" });
		}
	};

	await dialog.set_values(schema.values || {});
	for (const field of schemaFields) {
		if (!field?.fieldname) continue;
		if (["Link", "Autocomplete"].includes(fieldType(field))) {
			setControlOptions(dialog.fields_dict[field.fieldname], field.options || []);
			const input = dialog.fields_dict[field.fieldname]?.$input;
			if (input?.on && searchMethod) {
				input.off("input.eduedge-native-dialog").on("input.eduedge-native-dialog", () => {
					clearTimeout(state.searchTimers[field.fieldname]);
					state.searchTimers[field.fieldname] = setTimeout(
						() => state.refreshOptions(field.fieldname, input.val() || ""),
						250
					);
				});
			}
		}
	}
	state.refreshFieldStates();
	if (!canSave) {
		dialogFields.push({ fieldtype: "HTML", options: '<p class="text-muted">You can view this record, but your role cannot save changes.</p>' });
	}
	dialog.show();
	return dialog;
}
