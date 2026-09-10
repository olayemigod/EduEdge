<template>
	<EdgeModal
		:open="open"
		:title="dialogTitle"
		:subtitle="dialogSubtitle"
		size="md"
		:busy="busy"
		@close="close"
	>
		<div class="eduedge-assignment-governance" data-eduedge-assignment-governance-dialog>
			<section class="eduedge-assignment-governance__source">
				<p class="edge-eyebrow">Instructor responsibility</p>
				<strong>{{ sourceTitle }}</strong>
				<small>{{ periodLabel }}</small>
			</section>

			<section class="eduedge-assignment-governance__notice" :class="{ 'is-danger': mode === 'delete' }">
				<strong>{{ noticeTitle }}</strong>
				<span>{{ noticeText }}</span>
				<small>Branch Eligibility is independent and will not be shortened, deleted or widened by this action.</small>
			</section>

			<label class="eduedge-assignment-governance__field">
				<span>Reason <b>*</b></span>
				<textarea
					:value="reason"
					rows="3"
					class="form-control"
					:placeholder="reasonPlaceholder"
					:disabled="busy"
					@input="reason = $event.target.value; error = ''"
				></textarea>
				<small v-if="reasonError" class="eduedge-assignment-governance__error">{{ reasonError }}</small>
			</label>

			<label v-if="mode === 'delete'" class="eduedge-assignment-governance__field">
				<span>Type DELETE to confirm <b>*</b></span>
				<input
					:value="deleteConfirmation"
					type="text"
					class="form-control"
					placeholder="DELETE"
					autocomplete="off"
					:disabled="busy"
					@input="deleteConfirmation = $event.target.value; error = ''"
				/>
				<small>This confirmation is required because deletion removes the unused future assignment record itself.</small>
			</label>

			<p v-if="error" class="eduedge-assignment-governance__error" role="alert">{{ error }}</p>
		</div>

		<template #footer>
			<button type="button" class="edge-button" :disabled="busy" @click="close">Cancel</button>
			<button
				type="button"
				class="edge-button edge-button--primary"
				:class="{ 'eduedge-assignment-governance__delete': mode === 'delete' }"
				:disabled="busy || !canSubmit"
				@click="submit"
			>
				{{ busy ? busyLabel : actionLabel }}
			</button>
		</template>
	</EdgeModal>
</template>

<script>
const ACTIONS = {
	disable: {
		title: "Disable Future Assignment",
		subtitle: "Stop an upcoming responsibility before it starts without rewriting academic history.",
		noticeTitle: "Use Disable only for a responsibility that has not started.",
		noticeText: "Current and historical responsibilities must use lifecycle actions such as End, Replace or Transfer instead.",
		placeholder: "Why should this upcoming responsibility be disabled?",
		label: "Disable Assignment",
		busy: "Disabling assignment...",
		method: "eduedge.api.instructor_assignment_governance.disable_instructor_assignment",
	},
	reenable: {
		title: "Re-enable Future Assignment",
		subtitle: "Restore a disabled upcoming responsibility only after its academic context is valid again.",
		noticeTitle: "EduEdge will re-run the full assignment validations.",
		noticeText: "Instructor status, Branch Eligibility, curriculum membership, duplicate responsibility and primary responsibility rules must still pass.",
		placeholder: "Why should this upcoming responsibility be re-enabled?",
		label: "Re-enable Assignment",
		busy: "Re-enabling assignment...",
		method: "eduedge.api.instructor_assignment_governance.reenable_instructor_assignment",
	},
	delete: {
		title: "Delete Unused Future Assignment",
		subtitle: "Permanently remove only an unused future assignment that EduEdge proves has never started and has no history or references.",
		noticeTitle: "Deletion is intentionally narrow and irreversible.",
		noticeText: "Any lifecycle history, preparation provenance, external Link reference, started period or active status blocks deletion.",
		placeholder: "Why is this unused future assignment being deleted?",
		label: "Delete Unused Assignment",
		busy: "Checking and deleting...",
		method: "eduedge.api.instructor_assignment_governance.delete_unused_instructor_assignment",
	},
};

function serverErrorMessage(error, fallback) {
	if (error?.message) return error.message;
	const raw = error?.responseJSON?._server_messages;
	if (raw) {
		try {
			const messages = JSON.parse(raw);
			for (const item of messages) {
				try {
					const parsed = JSON.parse(item);
					if (parsed?.message) return parsed.message;
				} catch (ignored) {
					if (item) return String(item);
				}
			}
		} catch (ignored) {
			// Use the stable product fallback below.
		}
	}
	return fallback;
}

export default {
	name: "InstructorAssignmentGovernanceDialog",
	props: {
		item: { type: Object, required: true },
		mode: { type: String, required: true },
		onBusy: { type: Function, default: null },
		onComplete: { type: Function, default: null },
		onClosed: { type: Function, default: null },
	},
	data() {
		return {
			open: true,
			busy: false,
			reason: "",
			deleteConfirmation: "",
			error: "",
		};
	},
	computed: {
		config() { return ACTIONS[this.mode] || ACTIONS.disable; },
		dialogTitle() { return this.config.title; },
		dialogSubtitle() { return this.config.subtitle; },
		noticeTitle() { return this.config.noticeTitle; },
		noticeText() { return this.config.noticeText; },
		reasonPlaceholder() { return this.config.placeholder; },
		actionLabel() { return this.config.label; },
		busyLabel() { return this.config.busy; },
		sourceTitle() { return this.item.assignment_title || "Instructor Assignment"; },
		periodLabel() {
			return `${this.item.valid_from || "No start restriction"} → ${this.item.valid_to || "Open ended"}`;
		},
		reasonError() {
			const value = String(this.reason || "").trim();
			if (!value) return "Give a reason for this governance action.";
			if (value.length < 3) return "Give a short reason of at least 3 characters.";
			return "";
		},
		canSubmit() {
			if (this.reasonError) return false;
			if (this.mode === "delete" && this.deleteConfirmation !== "DELETE") return false;
			return true;
		},
	},
	methods: {
		setBusy(value) {
			this.busy = Boolean(value);
			this.onBusy?.(this.busy ? this.item.name : "");
		},
		async submit() {
			if (!this.canSubmit || this.busy) return;
			this.error = "";
			this.setBusy(true);
			let completed = false;
			try {
				const response = await frappe.call({
					method: this.config.method,
					type: "POST",
					args: {
						name: this.item.name,
						reason: String(this.reason || "").trim(),
					},
				});
				const result = response.message || {};
				const messages = {
					disabled: "Instructor Assignment disabled",
					"re-enabled": "Instructor Assignment re-enabled",
					"deleted-unused": "Unused Instructor Assignment deleted",
					"already-disabled": "Instructor Assignment is already disabled",
					"already-enabled": "Instructor Assignment is already enabled",
				};
				frappe.show_alert({ message: messages[result.action] || "Instructor Assignment updated", indicator: "green" });
				await this.onComplete?.(result);
				completed = true;
			} catch (error) {
				this.error = serverErrorMessage(error, "Instructor Assignment governance action could not be completed.");
			} finally {
				this.setBusy(false);
			}
			if (completed) this.close();
		},
		close() {
			if (this.busy) return;
			this.open = false;
			this.onClosed?.();
		},
	},
};
</script>

<style scoped>
.eduedge-assignment-governance { display: grid; gap: 1rem; }
.eduedge-assignment-governance__source, .eduedge-assignment-governance__notice { border: 1px solid var(--edge-color-border, #d8e2ee); border-radius: .85rem; display: grid; gap: .35rem; padding: .9rem; }
.eduedge-assignment-governance__source { background: var(--edge-color-surface-subtle, #f7f9fc); }
.eduedge-assignment-governance__source p { margin: 0; }
.eduedge-assignment-governance__source small, .eduedge-assignment-governance__notice small, .eduedge-assignment-governance__field small { color: var(--edge-color-ink-500, #687a90); }
.eduedge-assignment-governance__notice.is-danger { border-color: var(--edge-color-danger-300, #efb4b4); }
.eduedge-assignment-governance__field { display: grid; gap: .4rem; }
.eduedge-assignment-governance__field > span { font-size: .76rem; font-weight: 800; }
.eduedge-assignment-governance__error { color: var(--edge-color-danger-700, #b42318); font-size: .76rem; margin: 0; }
.eduedge-assignment-governance__delete { font-weight: 800; }
</style>
