<template>
	<EdgeModalFallback
		:open="open"
		:title="title"
		:subtitle="subtitle"
		size="lg"
		:busy="busy"
		@close="$emit('close')"
	>
		<form class="edge-form-dialog" data-eduedge-terminology-managed @submit.prevent="$emit('submit')">
			<div v-if="loading" class="edge-modal-state">
				<span class="eduedge-form-spinner" aria-hidden="true"></span>
				<span>Loading form…</span>
			</div>
			<template v-else>
				<p v-if="error" class="edge-form-global-error" role="alert">{{ error }}</p>
				<div class="edge-form-grid">
					<label
						v-for="field in visibleFields"
						:key="field.fieldname"
						class="edge-form-field"
						:class="fieldClasses(field)"
					>
						<template v-if="fieldType(field) === 'Check'">
							<span class="edge-checkbox">
								<input
									type="checkbox"
									:checked="truthy(localValues[field.fieldname])"
									:disabled="busy || field.read_only"
									@change="setCheckValue(field, $event)"
								/>
								<span>{{ field.label || field.fieldname }}<strong v-if="isRequired(field)" class="edge-form-required"> *</strong></span>
							</span>
						</template>
						<template v-else>
							<span class="edge-form-field__label">
								{{ field.label || field.fieldname }}<strong v-if="isRequired(field)" class="edge-form-required"> *</strong>
							</span>
							<textarea
								v-if="isTextArea(field)"
								:value="localValues[field.fieldname] ?? ''"
								:rows="field.rows || 3"
								:placeholder="field.placeholder || ''"
								:disabled="busy || field.read_only"
								class="edge-form-control"
								:class="{ 'is-invalid': fieldErrors?.[field.fieldname] }"
								@input="setValue(field, $event.target.value)"
							></textarea>
							<select
								v-else-if="fieldType(field) === 'Select'"
								:value="localValues[field.fieldname] ?? ''"
								:disabled="busy || field.read_only"
								class="edge-form-control"
								:class="{ 'is-invalid': fieldErrors?.[field.fieldname] }"
								@change="setValue(field, $event.target.value)"
							>
								<option value="">{{ field.placeholder || 'Select' }}</option>
								<option v-for="option in normalizedOptions(field.options)" :key="`${field.fieldname}-${option.value}`" :value="option.value">{{ option.label }}</option>
							</select>
							<template v-else-if="fieldType(field) === 'Link'">
								<div class="eduedge-quick-link-control">
									<EdgeLinkField
										:model-value="localValues[field.fieldname] ?? ''"
										:selected-label="linkSelectedLabel(field)"
										:options="normalizedOptions(field.options)"
										:placeholder="field.placeholder || `Search ${field.label || ''}`"
										:disabled="busy || field.read_only"
										:readonly="Boolean(field.read_only)"
										:required="isRequired(field)"
										:error="fieldErrors?.[field.fieldname] || ''"
										:allow-clear="true"
										:open-on-focus="true"
										:debounce-ms="180"
										class="eduedge-quick-link-field"
										@update:model-value="setValue(field, $event)"
										@query-change="requestOptions(field, $event)"
									/>
									<small v-if="field.options_loading" class="eduedge-quick-link-loading">Loading options…</small>
								</div>
							</template>
							<input
								v-else
								:value="localValues[field.fieldname] ?? ''"
								:type="inputType(field)"
								:step="numberStep(field)"
								:placeholder="field.placeholder || ''"
								:disabled="busy || field.read_only"
								class="edge-form-control"
								:class="{ 'is-invalid': fieldErrors?.[field.fieldname] }"
								@input="setValue(field, $event.target.value)"
							/>
						</template>
						<small v-if="field.description || field.help">{{ field.description || field.help }}</small>
						<small v-if="fieldErrors?.[field.fieldname] && fieldType(field) !== 'Link'" class="edge-form-error">{{ fieldErrors[field.fieldname] }}</small>
					</label>
				</div>
			</template>
		</form>
		<template #footer>
			<button v-if="showFullForm" type="button" class="edge-button edge-modal__full-form" :disabled="busy" @click="$emit('open-full-form')">Open full form</button>
			<span class="edge-modal__footer-spacer"></span>
			<button type="button" class="edge-button" :disabled="busy" @click="$emit('close')">Cancel</button>
			<button type="button" class="edge-button edge-button--primary" :disabled="loading || busy" @click="$emit('submit')">{{ busy ? 'Saving…' : submitLabel }}</button>
		</template>
	</EdgeModalFallback>
</template>

<script>
import EdgeModalFallback from "./EdgeModalFallback.vue";

export default {
	name: "EdgeFormDialogFallback",
	components: { EdgeModalFallback },
	props: {
		open: { type: Boolean, default: false },
		title: { type: String, default: "" },
		subtitle: { type: String, default: "" },
		fields: { type: Array, default: () => [] },
		modelValue: { type: Object, default: () => ({}) },
		fieldErrors: { type: Object, default: () => ({}) },
		error: { type: String, default: "" },
		loading: { type: Boolean, default: false },
		busy: { type: Boolean, default: false },
		submitLabel: { type: String, default: "Save" },
		showFullForm: { type: Boolean, default: false },
	},
	emits: ["close", "update:model-value", "field-change", "search-options", "submit", "open-full-form"],
	data() { return { localValues: { ...(this.modelValue || {}) } }; },
	computed: {
		visibleFields() { return (this.fields || []).filter((field) => !field.hidden && this.conditionMatches(field.visible_when)); },
	},
	watch: {
		modelValue: { deep: true, immediate: true, handler(value) { this.localValues = { ...(value || {}) }; } },
	},
	methods: {
		fieldType(field) { return String(field?.type || field?.fieldtype || "Data"); },
		fieldClasses(field) {
			const type = this.fieldType(field).toLowerCase().replace(/\s+/g, "-");
			return [`edge-form-field--${type}`, { "edge-form-field--check": this.fieldType(field) === "Check" }];
		},
		conditionMatches(condition) {
			if (!condition || !condition.field) return true;
			const actual = this.localValues?.[condition.field];
			if (Object.prototype.hasOwnProperty.call(condition, "equals")) return String(actual ?? "") === String(condition.equals ?? "");
			if (Object.prototype.hasOwnProperty.call(condition, "not_equals")) return String(actual ?? "") !== String(condition.not_equals ?? "");
			if (Array.isArray(condition.in)) return condition.in.map(String).includes(String(actual ?? ""));
			if (condition.truthy) return Boolean(actual);
			if (condition.falsy) return !actual;
			return true;
		},
		isRequired(field) { return Boolean(field.required || field.reqd || (field.required_when && this.conditionMatches(field.required_when))); },
		isTextArea(field) { return ["Small Text", "Text", "Long Text", "Text Editor"].includes(this.fieldType(field)); },
		inputType(field) {
			return { Date: "date", Datetime: "datetime-local", Time: "time", Email: "email", Phone: "tel", Password: "password", Int: "number", Float: "number", Currency: "number" }[this.fieldType(field)] || "text";
		},
		numberStep(field) { return this.fieldType(field) === "Int" ? "1" : ["Float", "Currency"].includes(this.fieldType(field)) ? "any" : undefined; },
		truthy(value) { return value === true || value === 1 || value === "1" || String(value).toLowerCase() === "yes"; },
		normalizedOptions(options) {
			const source = Array.isArray(options) ? options : typeof options === "string" ? options.split("\n") : [];
			return source.filter((option) => option !== undefined && option !== null && option !== "").map((option) => typeof option === "object" ? { value: String(option.value ?? option.name ?? ""), label: String(option.label ?? option.value ?? option.name ?? ""), description: String(option.description ?? "") } : { value: String(option), label: String(option), description: "" });
		},
		linkSelectedLabel(field) {
			const value = String(this.localValues?.[field.fieldname] ?? "");
			if (!value) return "";
			const selected = this.normalizedOptions(field.options).find((option) => option.value === value);
			return selected?.label || value;
		},
		setCheckValue(field, event) { this.setValue(field, event.target.checked ? 1 : 0); },
		setValue(field, value) {
			this.localValues = { ...this.localValues, [field.fieldname]: value };
			const values = { ...this.localValues };
			this.$emit("update:model-value", values);
			this.$emit("field-change", { field, values });
		},
		requestOptions(field, query) {
			this.$emit("search-options", { field, query: query || "", values: { ...this.localValues } });
		},
	},
};
</script>

<style scoped>
.eduedge-form-spinner {
	animation: eduedge-form-spin .8s linear infinite;
	border: 2px solid var(--edge-color-border, #dce5ef);
	border-radius: 50%;
	border-top-color: var(--edge-color-brand-600, #0f64ab);
	height: 1.1rem;
	margin-right: .65rem;
	width: 1.1rem;
}
.eduedge-quick-link-control,
.eduedge-quick-link-field { min-width: 0; width: 100%; }
.eduedge-quick-link-loading {
	color: var(--edge-color-ink-500, #6b7d90);
	display: block;
	font-size: .68rem;
	margin-top: .25rem;
}
@keyframes eduedge-form-spin { to { transform: rotate(360deg); } }
</style>
