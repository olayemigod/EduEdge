<template>
	<Teleport to="body">
		<div
			v-if="open"
			class="edge-modal-backdrop eduedge-modal-backdrop"
			data-eduedge-terminology-managed
			@mousedown.self="requestClose"
		>
			<section
				ref="dialog"
				class="edge-modal eduedge-compatible-modal"
				:class="`edge-modal--${size}`"
				role="dialog"
				aria-modal="true"
				:aria-labelledby="titleId"
				tabindex="-1"
				@keydown.esc.prevent="requestClose"
			>
				<header class="edge-modal__header">
					<div class="edge-modal__heading">
						<h2 :id="titleId">{{ title }}</h2>
						<p v-if="subtitle">{{ subtitle }}</p>
					</div>
					<button
						type="button"
						class="edge-modal__close"
						:disabled="busy"
						aria-label="Close dialog"
						@click="requestClose"
					>
						×
					</button>
				</header>
				<div class="edge-modal__body"><slot /></div>
				<footer v-if="$slots.footer" class="edge-modal__footer"><slot name="footer" /></footer>
			</section>
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
	data() {
		return { titleId: `eduedge-modal-title-${Math.random().toString(36).slice(2, 10)}` };
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
/* The canonical EdgeSuite classes above provide the visual contract. These
   guards keep the compatibility component correctly layered and centred even
   when a product site is temporarily serving an older shared stylesheet. */
.eduedge-modal-backdrop {
	align-items: center;
	background: rgb(15 23 42 / 42%);
	display: flex;
	inset: 0;
	justify-content: center;
	overflow-y: auto;
	padding: clamp(.75rem, 3vw, 2rem);
	position: fixed;
	z-index: 1100;
}
.eduedge-compatible-modal {
	background: var(--edge-color-surface, #fff);
	border: 1px solid var(--edge-color-border-strong, #cbd7e5);
	border-radius: var(--edge-radius-lg, 1rem);
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
	margin: auto;
	max-height: min(88vh, 54rem);
	overflow: hidden;
	width: min(100%, 42rem);
}
.eduedge-compatible-modal.edge-modal--sm { width: min(100%, 30rem); }
.eduedge-compatible-modal.edge-modal--lg { width: min(100%, 58rem); }
.eduedge-compatible-modal.edge-modal--xl { width: min(100%, 72rem); }
@media (max-width: 47.99rem) {
	.eduedge-modal-backdrop { align-items: flex-end; padding: 0; }
	.eduedge-compatible-modal {
		border-bottom: 0;
		border-left: 0;
		border-radius: 1rem 1rem 0 0;
		border-right: 0;
		margin: auto 0 0;
		max-height: 92vh;
		width: 100%;
	}
}
</style>
