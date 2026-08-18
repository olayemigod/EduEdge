<template>
	<div class="eduedge-multi-link-field">
		<div v-if="selectedOptions.length" class="eduedge-multi-link-field__selected">
			<button
				v-for="option in selectedOptions"
				:key="option.value"
				type="button"
				class="eduedge-multi-link-field__chip"
				:disabled="disabled"
				@click="remove(option.value)"
			>
				<span>{{ option.label || option.value }}</span>
				<span aria-hidden="true">×</span>
			</button>
		</div>
		<EdgeLinkField
			v-model="pending"
			:searcher="searchAvailable"
			:context="context"
			:placeholder="placeholder"
			:disabled="disabled"
			:open-on-focus="openOnFocus"
			@select="add"
			@clear="pending = ''"
		/>
		<small v-if="hint" class="eduedge-multi-link-field__hint">{{ hint }}</small>
	</div>
</template>

<script>
export default {
	name: "EduEdgeMultiLinkField",
	props: {
		modelValue: { type: Array, default: () => [] },
		searcher: { type: Function, required: true },
		context: { type: Object, default: () => ({}) },
		selectedOptions: { type: Array, default: () => [] },
		placeholder: { type: String, default: "Search and add" },
		hint: { type: String, default: "" },
		disabled: { type: Boolean, default: false },
		openOnFocus: { type: Boolean, default: true },
	},
	emits: ["update:modelValue", "change"],
	data() {
		return { pending: "" };
	},
	methods: {
		async searchAvailable(query, context) {
			const rows = await this.searcher(query, context);
			const selected = new Set(this.modelValue || []);
			return (rows || []).filter((row) => !selected.has(row.value));
		},
		add(option) {
			const value = option?.value;
			if (!value || (this.modelValue || []).includes(value)) {
				this.pending = "";
				return;
			}
			const next = [...(this.modelValue || []), value];
			this.pending = "";
			this.$emit("update:modelValue", next);
			this.$emit("change", next);
		},
		remove(value) {
			if (this.disabled) return;
			const next = (this.modelValue || []).filter((item) => item !== value);
			this.$emit("update:modelValue", next);
			this.$emit("change", next);
		},
	},
};
</script>

<style scoped>
.eduedge-multi-link-field { display:grid; gap:.5rem; }
.eduedge-multi-link-field__selected { display:flex; flex-wrap:wrap; gap:.4rem; }
.eduedge-multi-link-field__chip { display:inline-flex; align-items:center; gap:.4rem; max-width:100%; padding:.3rem .55rem; border:1px solid var(--border-color); border-radius:999px; background:var(--control-bg); color:var(--text-color); }
.eduedge-multi-link-field__chip span:first-child { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.eduedge-multi-link-field__hint { color:var(--text-muted); }
</style>
