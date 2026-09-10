import { createApp, h, reactive } from "vue";

import EdgeFormDialogFallback from "./components/EdgeFormDialogFallback.vue";
import EdgeLinkFieldFallback from "./components/EdgeLinkFieldFallback.vue";

function emptyResourceModalState() {
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
		fullFormRoute: "",
		advancedNote: "",
		canSave: false,
		searchTokens: {},
	};
}

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
	return true;
}

function fieldVisible(field, values) {
	return field?.hidden !== true && conditionMatches(field?.visible_when, values);
}

function fieldRequired(field, values) {
	if (field?.required || field?.reqd) return true;
	return Boolean(field?.required_when && conditionMatches(field.required_when, values));
}

function emptyValue(value) {
	if (Array.isArray(value)) return value.length === 0;
	return value === undefined || value === null || String(value).trim() === "";
}

function validateResourceModal(modal) {
	const errors = {};
	for (const field of modal.fields || []) {
		if (!fieldVisible(field, modal.values) || !fieldRequired(field, modal.values)) continue;
		const value = modal.values?.[field.fieldname];
		if (emptyValue(value)) {
			errors[field.fieldname] = `${field.label || field.fieldname} is required.`;
		}
	}
	modal.fieldErrors = errors;
	return !Object.keys(errors).length;
}

export function createResourceModalState() {
	return emptyResourceModalState();
}

export async function openResourceModal(modal, { resource, name = "", context = {} } = {}) {
	Object.assign(modal, emptyResourceModalState(), {
		open: true,
		loading: true,
		resource,
		name,
	});
	try {
		const response = await frappe.call("eduedge.api.resource_center.get_resource_editor", {
			resource,
			name: name || undefined,
			context: JSON.stringify(context || {}),
		});
		const schema = response.message || {};
		modal.title = schema.title || "Edit record";
		modal.subtitle = [schema.subtitle, schema.advanced_note].filter(Boolean).join(" ");
		modal.submitLabel = schema.submit_label || (name ? "Save Changes" : "Create");
		modal.fields = schema.fields || [];
		modal.values = { ...(schema.values || {}) };
		modal.fullFormRoute = schema.full_form_route || "";
		modal.advancedNote = schema.advanced_note || "";
		modal.canSave = schema.can_save !== false;
		if (!modal.canSave) modal.error = "You can view this record, but you are not permitted to save changes.";
	} catch (error) {
		modal.error = errorMessage(error, "The resource editor could not be loaded.");
	} finally {
		modal.loading = false;
	}
}

function mountEdgeResourceDialog({ resource, name = "", context = {}, onSaved } = {}) {
	if (typeof document === "undefined") return Promise.resolve(null);

	return new Promise((resolve) => {
		const host = document.createElement("div");
		host.className = "eduedge-edge-form-dialog-host";
		document.body.appendChild(host);

		const modal = reactive(createResourceModalState());
		let app = null;
		let finished = false;

		const finish = (value = null) => {
			if (finished || modal.busy) return;
			finished = true;
			closeResourceModal(modal);
			queueMicrotask(() => {
				try {
					app?.unmount();
				} finally {
					host.remove();
					resolve(value);
				}
			});
		};

		const submit = async () => {
			const saved = await saveResourceModal(modal);
			if (!saved) return;
			try {
				await onSaved?.(saved);
			} finally {
				finish(saved);
			}
		};

		const Root = {
			name: "EduEdgeResourceDialogHost",
			render() {
				return h(EdgeFormDialogFallback, {
					open: modal.open,
					title: modal.title,
					subtitle: modal.subtitle,
					fields: modal.fields,
					modelValue: modal.values,
					fieldErrors: modal.fieldErrors,
					error: modal.error,
					loading: modal.loading,
					busy: modal.busy,
					submitLabel: modal.submitLabel,
					showFullForm: Boolean(modal.fullFormRoute),
					onClose: () => finish(null),
					"onUpdate:modelValue": (values) => updateResourceModalValues(modal, values),
					onFieldChange: (payload) => handleResourceFieldChange(modal, payload),
					onSearchOptions: (payload) => searchResourceOptions(modal, payload),
					onSubmit: submit,
					onOpenFullForm: () => openResourceFullForm(modal),
				});
			},
		};

		app = createApp(Root);
		app.component("EdgeLinkField", EdgeLinkFieldFallback);
		app.mount(host);

		openResourceModal(modal, { resource, name, context }).catch((error) => {
			modal.loading = false;
			modal.error = errorMessage(error, "The resource editor could not be loaded.");
		});
	});
}

export async function openNativeResourceDialog({ resource, name = "", context = {}, onSaved } = {}) {
	return mountEdgeResourceDialog({ resource, name, context, onSaved });
}

export function closeResourceModal(modal) {
	if (modal.busy) return;
	Object.assign(modal, emptyResourceModalState());
}

export function updateResourceModalValues(modal, values) {
	modal.values = { ...(values || {}) };
	modal.fieldErrors = {};
	modal.error = "";
}

export async function handleResourceFieldChange(modal, { field, values } = {}) {
	modal.values = { ...(values || modal.values || {}) };
	modal.fieldErrors = { ...(modal.fieldErrors || {}), [field?.fieldname]: "" };
	modal.error = "";

	for (const fieldname of field?.clear_fields || []) {
		if (fieldname === field?.fieldname) continue;
		if (!emptyValue(modal.values?.[fieldname])) {
			modal.values = { ...modal.values, [fieldname]: "" };
		}
		modal.fieldErrors = { ...(modal.fieldErrors || {}), [fieldname]: "" };
	}

	for (const fieldname of field?.refresh_fields || []) {
		const target = (modal.fields || []).find((item) => item.fieldname === fieldname);
		if (!target) continue;
		await searchResourceOptions(modal, {
			field: target,
			query: "",
			values: modal.values,
		});
	}
}

export async function searchResourceOptions(modal, { field, query = "", values = {} } = {}) {
	if (!field?.fieldname || modal.loading || !modal.open) return;
	const fieldname = field.fieldname;
	const token = `${Date.now()}-${Math.random()}`;
	modal.searchTokens = { ...(modal.searchTokens || {}), [fieldname]: token };
	modal.fields = (modal.fields || []).map((item) =>
		item.fieldname === fieldname ? { ...item, options_loading: true } : item
	);
	try {
		const response = await frappe.call("eduedge.api.resource_center.search_resource_options", {
			resource: modal.resource,
			fieldname,
			txt: query || "",
			values: JSON.stringify(values || modal.values || {}),
		});
		if (modal.searchTokens?.[fieldname] !== token) return;
		const options = response.message || [];
		modal.fields = (modal.fields || []).map((item) =>
			item.fieldname === fieldname
				? { ...item, options, options_loading: false }
				: item
		);
		if (emptyValue(modal.values?.[fieldname]) && options.length === 1) {
			modal.values = { ...modal.values, [fieldname]: options[0].value ?? options[0].name ?? "" };
		}
	} catch (error) {
		if (modal.searchTokens?.[fieldname] !== token) return;
		modal.fields = (modal.fields || []).map((item) =>
			item.fieldname === fieldname ? { ...item, options_loading: false } : item
		);
		modal.error = errorMessage(error, `Options for ${field.label || fieldname} could not be loaded.`);
	}
}

export async function saveResourceModal(modal) {
	if (modal.busy || !modal.canSave || !validateResourceModal(modal)) return null;
	modal.busy = true;
	modal.error = "";
	try {
		const response = await frappe.call("eduedge.api.resource_center.save_resource_record", {
			resource: modal.resource,
			name: modal.name || undefined,
			values: JSON.stringify(modal.values || {}),
		});
		return response.message || null;
	} catch (error) {
		modal.error = errorMessage(error, "The record could not be saved.");
		return null;
	} finally {
		modal.busy = false;
	}
}

export function openResourceFullForm(modal) {
	const route = String(modal.fullFormRoute || "").trim();
	if (!route) return;
	window.open(route.startsWith("/") ? route : `/${route}`, "_blank", "noopener,noreferrer");
}
