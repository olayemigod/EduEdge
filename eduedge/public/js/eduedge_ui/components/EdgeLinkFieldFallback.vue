<template>
	<div
		ref="root"
		class="edge-link-field"
		:class="{
			'edge-link-field--open': open,
			'edge-link-field--disabled': disabled,
			'edge-link-field--invalid': Boolean(error),
		}"
	>
		<div class="edge-link-field__control">
			<input
				ref="input"
				:value="query"
				type="text"
				class="edge-link-field__input form-control"
				:placeholder="placeholder"
				:disabled="disabled"
				:readonly="readonly"
				:required="required"
				role="combobox"
				autocomplete="off"
				:aria-expanded="open ? 'true' : 'false'"
				:aria-controls="listboxId"
				:aria-invalid="error ? 'true' : 'false'"
				@focus="handleFocus"
				@input="handleInput"
				@keydown.down.prevent="moveActive(1)"
				@keydown.up.prevent="moveActive(-1)"
				@keydown.enter.prevent="selectActive"
				@keydown.esc.prevent="closeDropdown"
			/>
			<button
				v-if="allowClear && !disabled && !readonly && (modelValue || query)"
				type="button"
				class="edge-link-field__clear"
				aria-label="Clear selection"
				@mousedown.prevent
				@click="clearSelection"
			>
				×
			</button>
		</div>

		<small v-if="error" class="edge-link-field__error" role="alert">{{ error }}</small>

		<div v-if="open" :id="listboxId" class="edge-link-field__menu" role="listbox">
			<div v-if="loading" class="edge-link-field__state">Searching…</div>
			<template v-else-if="results.length">
				<button
					v-for="(option, index) in results"
					:key="`${option.value}-${index}`"
					type="button"
					class="edge-link-field__option"
					:class="{ 'edge-link-field__option--active': index === activeIndex }"
					role="option"
					:aria-selected="option.value === modelValue ? 'true' : 'false'"
					@mouseenter="activeIndex = index"
					@mousedown.prevent="selectOption(option)"
				>
					<strong>{{ option.label }}</strong>
					<small v-if="option.description">{{ option.description }}</small>
				</button>
			</template>
			<div v-else class="edge-link-field__state">No matching records</div>
		</div>
	</div>
</template>

<script>
let linkFieldSequence = 0;

export default {
	name: "EdgeLinkFieldFallback",
	props: {
		modelValue: { type: [String, Number], default: "" },
		selectedLabel: { type: String, default: "" },
		options: { type: Array, default: () => [] },
		searcher: { type: Function, default: null },
		context: { type: Object, default: () => ({}) },
		placeholder: { type: String, default: "Search" },
		disabled: { type: Boolean, default: false },
		readonly: { type: Boolean, default: false },
		required: { type: Boolean, default: false },
		error: { type: String, default: "" },
		allowClear: { type: Boolean, default: true },
		openOnFocus: { type: Boolean, default: false },
		debounceMs: { type: Number, default: 220 },
	},
	emits: ["update:model-value", "query-change", "select", "clear", "open", "close"],
	data() {
		linkFieldSequence += 1;
		return {
			listboxId: `eduedge-link-field-${linkFieldSequence}`,
			query: this.selectedLabel || String(this.modelValue || ""),
			results: [],
			open: false,
			loading: false,
			activeIndex: -1,
			searchTimer: null,
			requestSerial: 0,
		};
	},
	watch: {
		modelValue() {
			this.syncSelectedText();
		},
		selectedLabel() {
			this.syncSelectedText();
		},
		options: {
			deep: true,
			handler() {
				if (!this.searcher && this.open) this.applyLocalOptions(this.query);
			},
		},
		context: {
			deep: true,
			handler() {
				this.requestSerial += 1;
				this.results = [];
				this.activeIndex = -1;
				if (this.open) this.scheduleSearch(this.query, true);
			},
		},
	},
	mounted() {
		document.addEventListener("pointerdown", this.handleOutsidePointer, true);
	},
	beforeUnmount() {
		document.removeEventListener("pointerdown", this.handleOutsidePointer, true);
		if (this.searchTimer) window.clearTimeout(this.searchTimer);
		this.requestSerial += 1;
	},
	methods: {
		normaliseOptions(options) {
			return (Array.isArray(options) ? options : [])
				.filter((option) => option !== undefined && option !== null)
				.map((option) => {
					if (typeof option === "object") {
						const value = String(option.value ?? option.name ?? "");
						return {
							...option,
							value,
							label: String(option.label ?? option.title ?? value),
							description: String(option.description ?? option.subtitle ?? ""),
						};
					}
					const value = String(option);
					return { value, label: value, description: "" };
				})
				.filter((option) => option.value);
		},
		syncSelectedText() {
			const input = this.$refs.input;
			if (input && document.activeElement === input && this.open) return;
			this.query = this.selectedLabel || String(this.modelValue || "");
		},
		handleFocus() {
			if (this.disabled || this.readonly || !this.openOnFocus) return;
			this.openDropdown();
			this.scheduleSearch(this.modelValue ? "" : this.query, true);
		},
		handleInput(event) {
			if (this.disabled || this.readonly) return;
			this.query = event.target.value;
			if (this.modelValue) this.$emit("update:model-value", "");
			this.openDropdown();
			this.$emit("query-change", this.query);
			this.scheduleSearch(this.query);
		},
		openDropdown() {
			if (this.open) return;
			this.open = true;
			this.$emit("open");
		},
		closeDropdown() {
			if (!this.open) return;
			this.open = false;
			this.activeIndex = -1;
			this.$emit("close");
			this.syncSelectedText();
		},
		handleOutsidePointer(event) {
			if (!this.open || this.$refs.root?.contains(event.target)) return;
			this.closeDropdown();
		},
		scheduleSearch(query, immediate = false) {
			if (this.searchTimer) window.clearTimeout(this.searchTimer);
			if (immediate || this.debounceMs <= 0) {
				this.performSearch(query);
				return;
			}
			this.searchTimer = window.setTimeout(() => this.performSearch(query), this.debounceMs);
		},
		async performSearch(query) {
			const requestId = ++this.requestSerial;
			const cleaned = String(query || "").trim();
			if (typeof this.searcher !== "function") {
				this.applyLocalOptions(cleaned);
				return;
			}
			this.loading = true;
			try {
				const options = await this.searcher(cleaned, { ...(this.context || {}) });
				if (requestId !== this.requestSerial) return;
				this.results = this.normaliseOptions(options).slice(0, 50);
				this.activeIndex = this.results.length ? 0 : -1;
			} catch (error) {
				if (requestId !== this.requestSerial) return;
				console.error("EduEdge Link field search failed", error);
				this.results = [];
				this.activeIndex = -1;
			} finally {
				if (requestId === this.requestSerial) this.loading = false;
			}
		},
		applyLocalOptions(query) {
			const cleaned = String(query || "").trim().toLowerCase();
			const options = this.normaliseOptions(this.options);
			this.results = options
				.filter((option) => !cleaned || `${option.label} ${option.value} ${option.description}`.toLowerCase().includes(cleaned))
				.slice(0, 50);
			this.activeIndex = this.results.length ? 0 : -1;
		},
		moveActive(direction) {
			if (!this.open) {
				this.openDropdown();
				this.scheduleSearch(this.query, true);
				return;
			}
			if (!this.results.length) return;
			this.activeIndex = (this.activeIndex + direction + this.results.length) % this.results.length;
		},
		selectActive() {
			if (!this.open || this.activeIndex < 0) return;
			this.selectOption(this.results[this.activeIndex]);
		},
		selectOption(option) {
			if (!option || this.disabled || this.readonly) return;
			this.query = option.label || option.value;
			this.$emit("update:model-value", option.value);
			this.$emit("select", option);
			this.closeDropdown();
		},
		clearSelection() {
			if (this.disabled || this.readonly) return;
			this.requestSerial += 1;
			this.query = "";
			this.results = [];
			this.activeIndex = -1;
			this.$emit("update:model-value", "");
			this.$emit("clear");
			this.$emit("query-change", "");
			this.openDropdown();
			this.scheduleSearch("", true);
			this.$refs.input?.focus();
		},
	},
};
</script>

<style scoped>
.edge-link-field {
	position: relative;
	width: 100%;
}
.edge-link-field__control {
	position: relative;
}
.edge-link-field__input {
	padding-right: 2.25rem;
	width: 100%;
}
.edge-link-field__clear {
	align-items: center;
	background: transparent;
	border: 0;
	color: var(--edge-color-ink-500, #6b7d90);
	cursor: pointer;
	display: flex;
	font-size: 1.15rem;
	height: 2rem;
	justify-content: center;
	position: absolute;
	right: .25rem;
	top: 50%;
	transform: translateY(-50%);
	width: 2rem;
}
.edge-link-field__menu {
	background: var(--edge-color-surface, #fff);
	border: 1px solid var(--edge-color-border, #dce5ef);
	border-radius: .55rem;
	box-shadow: 0 .75rem 2rem rgba(15, 35, 55, .14);
	left: 0;
	margin-top: .3rem;
	max-height: 18rem;
	overflow-y: auto;
	position: absolute;
	right: 0;
	z-index: 1055;
}
.edge-link-field__option {
	background: transparent;
	border: 0;
	border-bottom: 1px solid var(--edge-color-border, #edf1f5);
	color: inherit;
	cursor: pointer;
	display: flex;
	flex-direction: column;
	gap: .15rem;
	padding: .7rem .8rem;
	text-align: left;
	width: 100%;
}
.edge-link-field__option:last-child { border-bottom: 0; }
.edge-link-field__option:hover,
.edge-link-field__option--active {
	background: var(--edge-color-surface-subtle, #f4f8fb);
}
.edge-link-field__option small,
.edge-link-field__state,
.edge-link-field__error {
	color: var(--edge-color-ink-500, #6b7d90);
	font-size: .75rem;
}
.edge-link-field__state { padding: .8rem; }
.edge-link-field__error {
	color: var(--edge-color-danger-600, #b42318);
	display: block;
	margin-top: .25rem;
}
.edge-link-field--invalid .edge-link-field__input {
	border-color: var(--edge-color-danger-500, #d92d20);
}
.edge-link-field--disabled { opacity: .68; }
</style>
