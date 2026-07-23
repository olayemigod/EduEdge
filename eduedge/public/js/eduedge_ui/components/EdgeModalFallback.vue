<template>
	<Teleport to="body">
		<div v-if="open" class="edge-modal edge-modal-fallback" data-eduedge-terminology-managed>
			<div class="edge-modal-fallback__backdrop" @mousedown.self="requestClose">
				<section
					ref="dialog"
					class="edge-modal-fallback__dialog"
					:class="`edge-modal-fallback__dialog--${size}`"
					role="dialog"
					aria-modal="true"
					:aria-labelledby="titleId"
					tabindex="-1"
					@keydown.esc.prevent="requestClose"
				>
					<header class="edge-modal-fallback__header">
						<div>
							<h2 :id="titleId">{{ title }}</h2>
							<p v-if="subtitle">{{ subtitle }}</p>
						</div>
						<button type="button" class="edge-modal-fallback__close" :disabled="busy" aria-label="Close dialog" @click="requestClose">×</button>
					</header>
					<div class="edge-modal-fallback__body"><slot /></div>
					<footer v-if="$slots.footer" class="edge-modal-fallback__footer"><slot name="footer" /></footer>
				</section>
			</div>
		</div>
	</Teleport>
</template>

<script>
export default {
	name: "EdgeModalFallback",
	props: {
		open: { type: Boolean, default: false },
		title: { type: String, default: "" },
		subtitle: { type: String, default: "" },
		size: { type: String, default: "md" },
		busy: { type: Boolean, default: false },
	},
	emits: ["close"],
	computed: {
		titleId() { return `eduedge-modal-title-${this._uid}`; },
	},
	watch: {
		open(value) {
			if (!value) return;
			this.$nextTick(() => this.$refs.dialog?.focus?.());
		},
	},
	methods: {
		requestClose() {
			if (!this.busy) this.$emit("close");
		},
	},
};
</script>

<style scoped>
.edge-modal-fallback { position: fixed; inset: 0; z-index: 1060; }
.edge-modal-fallback__backdrop { align-items: center; background: rgba(15, 23, 42, .52); display: flex; inset: 0; justify-content: center; overflow-y: auto; padding: 1.25rem; position: absolute; }
.edge-modal-fallback__dialog { background: var(--card-bg, #fff); border: 1px solid var(--border-color, #d8dee8); border-radius: var(--edge-radius-lg, 12px); box-shadow: 0 24px 64px rgba(15, 23, 42, .24); color: var(--text-color, #1f2937); display: flex; flex-direction: column; max-height: calc(100vh - 2.5rem); max-width: 48rem; outline: none; overflow: hidden; width: min(100%, 42rem); }
.edge-modal-fallback__dialog--sm { max-width: 28rem; }
.edge-modal-fallback__dialog--lg { max-width: 64rem; width: min(100%, 58rem); }
.edge-modal-fallback__header { align-items: flex-start; border-bottom: 1px solid var(--border-color, #d8dee8); display: flex; gap: 1rem; justify-content: space-between; padding: 1rem 1.25rem; }
.edge-modal-fallback__header h2 { font-size: 1.15rem; margin: 0; }
.edge-modal-fallback__header p { color: var(--text-muted, #667085); margin: .35rem 0 0; }
.edge-modal-fallback__close { background: transparent; border: 0; color: var(--text-muted, #667085); cursor: pointer; font-size: 1.5rem; line-height: 1; padding: .1rem .35rem; }
.edge-modal-fallback__close:disabled { cursor: not-allowed; opacity: .55; }
.edge-modal-fallback__body { overflow-y: auto; padding: 1.25rem; }
.edge-modal-fallback__footer { align-items: center; border-top: 1px solid var(--border-color, #d8dee8); display: flex; gap: .65rem; justify-content: flex-end; padding: .9rem 1.25rem; }
@media (max-width: 640px) { .edge-modal-fallback__backdrop { align-items: flex-end; padding: .5rem; } .edge-modal-fallback__dialog { max-height: calc(100vh - 1rem); width: 100%; } }
</style>
