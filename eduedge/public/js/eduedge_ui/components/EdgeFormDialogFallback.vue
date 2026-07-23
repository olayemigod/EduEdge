<template>
	<EdgeModalFallback
		:open="open"
		:title="title"
		:subtitle="subtitle"
		size="lg"
		:busy="busy"
		@close="$emit('close')"
	>
		<div class="edge-form-dialog-fallback" data-eduedge-terminology-managed>
			<div v-if="loading" class="edge-form-dialog-fallback__loading">
				<span class="edge-form-dialog-fallback__spinner" aria-hidden="true"></span>
				<span>Loading form…</span>
			</div>
			<div v-else>
				<p v-if="error" class="edge-form-dialog-fallback__error" role="alert">{{ error }}</p>
				<div class="edge-form-dialog-fallback__grid">
					<label v-for="field in visibleFields" :key="field.fieldname" class="edge-form-dialog-fallback__field" :class="{ 'edge-form-dialog-fallback__field--check': fieldType(field) === 'Check' }">
						<template v-if="fieldType(field) === 'Check'">
							<input type="checkbox" :checked="truthy(localValues[field.fieldname])" :disabled="busy || field.read_only" @change="setCheckValue(field, $event)" />
							<span>{{ field.label || field.fieldname }}<strong v-if="isRequired(field)"> *</strong></span>
						</template>
						<template v-else>
							<span>{{ field.label || field.fieldname }}<strong v-if="isRequired(field)"> *</strong></span>
							<textarea
								v-if="isTextArea(field)"
								:value="localValues[field.fieldname] ?? ''"
								:rows="field.rows || 3"
								:placeholder="field.placeholder || ''"
								:disabled="busy || field.read_only"
								class="form-control"
								@input="setValue(field, $event.target.value)"
							></textarea>
							<select
								v-else-if="fieldType(field) === 'Select'"
								:value="localValues[field.fieldname] ?? ''"
								:disabled="busy || field.read_only"
								class="form-control"
								@change="setValue(field, $event.target.value)"
							>
								<option value="">{{ field.placeholder || 'Select' }}</option>
								<option v-for="option in normalizedOptions(field.options)" :key="`${field.fieldname}-${option.value}`" :value="option.value">{{ option.label }}</option>
							</select>
							<template v-else-if="fieldType(field) === 'Link'">
								<input
									:value="localValues[field.fieldname] ?? ''"
									:list="optionListId(field)"
									:placeholder="field.placeholder || `Search ${field.label || ''}`"
									:disabled="busy || field.read_only"
									class="form-control"
									@focus="requestOptions(field, $event.target.value)"
									@input="setValue(field, $event.target.value); requestOptions(field, $event.target.value)"
								/>
								<datalist :id="optionListId(field)">
									<option v-for="option in normalizedOptions(field.options)" :key="`${field.fieldname}-${option.value}`" :value="option.value">{{ option.label }}</option>
								</datalist>
								<small v-if="field.options_loading" class="edge-form-dialog-fallback__help">Loading options…</small>
							</template>
							<input
								v-else
								:value="localValues[field.fieldname] ?? ''"
								:type="inputType(field)"
								:step="numberStep(field)"
								:placeholder="field.placeholder || ''"
								:disabled="busy || field.read_only"
								class="form-control"
								@input="setValue(field, $event.target.value)"
							/>
						</template>
						<small v-if="field.description || field.help" class="edge-form-dialog-fallback__help">{{ field.description || field.help }}</small>
						<small v-if="fieldErrors?.[field.fieldname]" class="edge-form-dialog-fallback__field-error">{{ fieldErrors[field.fieldname] }}</small>
					</label>
				</div>
			</div>
		</div>
		<template #footer>
			<button v-if="showFullForm" type="button" class="edge-button" :disabled="busy" @click="$emit('open-full-form')">Open full form</button>
			<span class="edge-form-dialog-fallback__spacer"></span>
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
			return source.filter((option) => option !== undefined && option !== null && option !== "").map((option) => typeof option === "object" ? { value: String(option.value ?? option.name ?? ""), label: String(option.label ?? option.value ?? option.name ?? "") } : { value: String(option), label: String(option) });
		},
		optionListId(field) { return `eduedge-options-${String(field.fieldname || '').replace(/[^a-zA-Z0-9_-]/g, '-')}`; },
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
.edge-form-dialog-fallback { min-height: 5rem; }
.edge-form-dialog-fallback__loading { align-items: center; color: var(--text-muted, #667085); display: flex; gap: .65rem; justify-content: center; min-height: 8rem; }
.edge-form-dialog-fallback__spinner { animation: edge-form-spin .8s linear infinite; border: 2px solid var(--border-color, #d8dee8); border-radius: 50%; border-top-color: var(--primary, #2563eb); height: 1.1rem; width: 1.1rem; }
.edge-form-dialog-fallback__error { background: var(--red-50, #fff1f2); border: 1px solid var(--red-200, #fecdd3); border-radius: .65rem; color: var(--red-700, #b42318); margin: 0 0 1rem; padding: .75rem; }
.edge-form-dialog-fallback__grid { display: grid; gap: 1rem; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.edge-form-dialog-fallback__field { display: grid; gap: .35rem; min-width: 0; }
.edge-form-dialog-fallback__field--check { align-items: center; display: grid; gap: .55rem; grid-template-columns: auto 1fr; }
.edge-form-dialog-fallback__field--check small { grid-column: 1 / -1; }
.edge-form-dialog-fallback__field strong { color: var(--red-600, #d92d20); }
.edge-form-dialog-fallback__help { color: var(--text-muted, #667085); }
.edge-form-dialog-fallback__field-error { color: var(--red-600, #d92d20); }
.edge-form-dialog-fallback__spacer { flex: 1; }
@keyframes edge-form-spin { to { transform: rotate(360deg); } }
@media (max-width: 720px) { .edge-form-dialog-fallback__grid { grid-template-columns: 1fr; } }
</style>
