function emptyModalState() {
	return {
		open: false,
		loading: false,
		busy: false,
		error: "",
		fieldErrors: {},
		resource: "",
		name: "",
		title: "",
		subtitle: "",
		submitLabel: "Save",
		fields: [],
		values: {},
		context: {},
		fullFormRoute: "",
		canSave: false,
		searchTokens: {},
	};
}

function messageFromError(error, fallback) {
	return (
		error?.message ||
		error?._server_messages ||
		error?.exc_type ||
		fallback
	);
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

function fieldVisible(field, values) {
	return field?.hidden !== true && conditionMatches(field?.visible_when, values);
}

function fieldRequired(field, values) {
	if (field?.required || field?.reqd) return true;
	return Boolean(field?.required_when && conditionMatches(field.required_when, values));
}

function validateModal(modal) {
	const errors = {};
	for (const field of modal.fields || []) {
		if (!fieldVisible(field, modal.values)) continue;
		if (!fieldRequired(field, modal.values)) continue;
		const value = modal.values?.[field.fieldname];
		if (value === undefined || value === null || String(value).trim() === "") {
			errors[field.fieldname] = `${field.label || field.fieldname} is required.`;
		}
	}
	modal.fieldErrors = errors;
	return !Object.keys(errors).length;
}

export function createRecordModalState() {
	return emptyModalState();
}

export async function openRecordModal(modal, { resource, name = "", context = {} } = {}) {
	Object.assign(modal, emptyModalState(), {
		open: true,
		loading: true,
		resource,
		name,
		context: { ...(context || {}) },
	});
	try {
		const response = await frappe.call("eduedge.api.modal_records.get_modal_schema", {
			resource,
			name: name || undefined,
			context: JSON.stringify(context || {}),
		});
		const schema = response.message || {};
		modal.title = schema.title || "Edit record";
		modal.subtitle = schema.subtitle || "";
		modal.submitLabel = schema.submit_label || (name ? "Save Changes" : "Create");
		modal.fields = schema.fields || [];
		modal.values = { ...(schema.values || {}) };
		modal.fullFormRoute = schema.full_form_route || "";
		modal.canSave = schema.can_save !== false;
		if (!modal.canSave) modal.error = "You can view this record, but you are not permitted to save changes.";
	} catch (error) {
		modal.error = messageFromError(error, "The quick editor could not be loaded.");
	} finally {
		modal.loading = false;
	}
}

export function closeRecordModal(modal) {
	if (modal.busy) return;
	Object.assign(modal, emptyModalState());
}

export function updateRecordModalValues(modal, values) {
	modal.values = { ...(values || {}) };
	modal.fieldErrors = {};
	modal.error = "";
}

export function handleRecordModalFieldChange(modal, { field, values } = {}) {
	modal.values = { ...(values || modal.values || {}) };
	modal.fieldErrors = { ...(modal.fieldErrors || {}), [field?.fieldname]: "" };
	modal.error = "";
}

export async function searchRecordModalOptions(modal, { field, query = "", values = {} } = {}) {
	if (!field?.fieldname || modal.loading || !modal.open) return;
	const fieldname = field.fieldname;
	const token = `${Date.now()}-${Math.random()}`;
	modal.searchTokens = { ...(modal.searchTokens || {}), [fieldname]: token };
	modal.fields = (modal.fields || []).map((item) =>
		item.fieldname === fieldname ? { ...item, options_loading: true } : item
	);
	try {
		const response = await frappe.call("eduedge.api.modal_records.search_modal_options", {
			resource: modal.resource,
			fieldname,
			txt: query || "",
			values: JSON.stringify(values || modal.values || {}),
			context: JSON.stringify(modal.context || {}),
		});
		if (modal.searchTokens?.[fieldname] !== token) return;
		modal.fields = (modal.fields || []).map((item) =>
			item.fieldname === fieldname
				? { ...item, options: response.message || [], options_loading: false }
				: item
		);
	} catch (error) {
		if (modal.searchTokens?.[fieldname] !== token) return;
		modal.fields = (modal.fields || []).map((item) =>
			item.fieldname === fieldname ? { ...item, options_loading: false } : item
		);
		modal.error = messageFromError(error, `Options for ${field.label || fieldname} could not be loaded.`);
	}
}

export async function saveRecordModal(modal) {
	if (modal.busy || !modal.canSave || !validateModal(modal)) return null;
	modal.busy = true;
	modal.error = "";
	try {
		const response = await frappe.call("eduedge.api.modal_records.save_modal_record", {
			resource: modal.resource,
			name: modal.name || undefined,
			values: JSON.stringify(modal.values || {}),
			context: JSON.stringify(modal.context || {}),
		});
		return response.message || null;
	} catch (error) {
		modal.error = messageFromError(error, "The record could not be saved.");
		return null;
	} finally {
		modal.busy = false;
	}
}

export function openRecordFullForm(modal) {
	let route = modal.fullFormRoute || "";
	if (!route) return;
	if (!route.startsWith("/")) route = `/${route}`;
	window.open(route, "_blank", "noopener,noreferrer");
}
