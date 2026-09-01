<template>
	<EdgeModal :open="open" title="End Instructor Assignment" subtitle="Close a current academic responsibility while preserving its history." size="md" :busy="busy" @close="close">
		<div class="eduedge-assignment-end-dialog" data-eduedge-assignment-end-dialog>
			<section class="eduedge-assignment-end-dialog__source">
				<p class="edge-eyebrow">Instructor responsibility</p>
				<strong>{{ sourceTitle }}</strong>
				<small>{{ periodLabel }}</small>
			</section>
			<section class="eduedge-assignment-end-dialog__notice">
				<strong>Close only this current responsibility.</strong>
				<span>The assignment remains available in academic history and earlier teaching records remain unchanged.</span>
				<small>Branch Eligibility is governed independently and is not changed by this action.</small>
			</section>
			<label class="eduedge-assignment-end-dialog__field">
				<span>End Date <b>*</b></span>
				<input :value="endDate" type="date" class="form-control" :min="today" :max="item.valid_to || undefined" :disabled="busy" @input="endDate = $event.target.value; error = ''" />
				<small>Final day on which this responsibility remains valid.</small>
				<small v-if="endDateError" class="eduedge-assignment-end-dialog__error">{{ endDateError }}</small>
			</label>
			<label class="eduedge-assignment-end-dialog__field">
				<span>Reason <b>*</b></span>
				<textarea :value="reason" rows="3" class="form-control" placeholder="Why is this responsibility ending?" :disabled="busy" @input="reason = $event.target.value; error = ''"></textarea>
				<small v-if="reasonError" class="eduedge-assignment-end-dialog__error">{{ reasonError }}</small>
			</label>
			<p v-if="error" class="eduedge-assignment-end-dialog__error" role="alert">{{ error }}</p>
		</div>
		<template #footer>
			<button type="button" class="edge-button" :disabled="busy" @click="close">Cancel</button>
			<button type="button" class="edge-button edge-button--primary" :disabled="busy || !canSubmit" @click="submit">{{ busy ? 'Ending assignment...' : 'End Assignment' }}</button>
		</template>
	</EdgeModal>
</template>

<script>
function todayValue() {
	return frappe.datetime?.get_today?.() || new Date().toISOString().slice(0, 10);
}

function serverErrorMessage(error, fallback) {
	if (error?.message) return error.message;
	return fallback;
}

export default {
	name: "InstructorAssignmentEndDialog",
	props: {
		item: { type: Object, required: true },
		onBusy: { type: Function, default: null },
		onComplete: { type: Function, default: null },
		onClosed: { type: Function, default: null },
	},
	data() {
		return { open: true, busy: false, endDate: todayValue(), reason: "", error: "" };
	},
	computed: {
		today() { return todayValue(); },
		sourceTitle() { return this.item.assignment_title || this.item.assignment_type || "Instructor Assignment"; },
		periodLabel() { return `${this.item.valid_from || "No start restriction"} → ${this.item.valid_to || "Open ended"}`; },
		endDateError() {
			if (!this.endDate) return "Select the final responsibility date.";
			if (this.endDate < this.today) return "End Date cannot be before today.";
			if (this.item.valid_to && this.endDate > this.item.valid_to) return "End Date cannot be after the assignment Valid To date.";
			return "";
		},
		reasonError() {
			const value = String(this.reason || "").trim();
			if (!value) return "Give a reason for ending this responsibility.";
			if (value.length < 3) return "Give a short reason of at least 3 characters.";
			return "";
		},
		canSubmit() { return !this.endDateError && !this.reasonError; },
	},
	methods: {
		setBusy(value) { this.busy = Boolean(value); this.onBusy?.(this.busy ? this.item.name : ""); },
		async submit() {
			if (!this.canSubmit || this.busy) return;
			this.error = "";
			this.setBusy(true);
			let completed = false;
			try {
				const response = await frappe.call({
					method: "eduedge.api.instructor_assignment_lifecycle.end_instructor_assignment",
					type: "POST",
					args: { name: this.item.name, end_date: this.endDate, reason: String(this.reason || "").trim() },
				});
				const result = response.message || {};
				frappe.show_alert({ message: result.action === "already-ended" ? "Instructor Assignment was already ended" : "Instructor Assignment ended", indicator: "green" });
				await this.onComplete?.(result);
				completed = true;
			} catch (error) {
				this.error = serverErrorMessage(error, "Instructor Assignment could not be ended.");
			} finally {
				this.setBusy(false);
			}
			if (completed) this.close();
		},
		close() { if (this.busy) return; this.open = false; this.onClosed?.(); },
	},
};
</script>

<style scoped>
.eduedge-assignment-end-dialog{display:grid;gap:1rem;color:var(--edge-color-ink-950,#122033)}
.eduedge-assignment-end-dialog__source,.eduedge-assignment-end-dialog__notice{border:1px solid var(--edge-color-border,#d8e2ee);border-radius:.85rem;display:grid;gap:.35rem;padding:.9rem}
.eduedge-assignment-end-dialog__source{background:var(--edge-color-surface-muted,var(--edge-color-surface,#fff))}
.eduedge-assignment-end-dialog__notice{background:var(--edge-color-surface,transparent)}
.eduedge-assignment-end-dialog__source p{margin:0}
.eduedge-assignment-end-dialog__source small,.eduedge-assignment-end-dialog__notice small,.eduedge-assignment-end-dialog__field small{color:var(--edge-color-ink-500,#687a90)}
.eduedge-assignment-end-dialog__field{display:grid;gap:.4rem}
.eduedge-assignment-end-dialog__field>span{font-size:.76rem;font-weight:800}
.eduedge-assignment-end-dialog__field .form-control{background:var(--edge-color-control-surface,var(--edge-color-surface,#fff));border-color:var(--edge-color-control-border,var(--edge-color-border,#d8e2ee));color:var(--edge-color-control-text,var(--edge-color-ink-950,#122033))}
.eduedge-assignment-end-dialog__field .form-control::placeholder{color:var(--edge-color-ink-400,#8998a8);opacity:1}
.eduedge-assignment-end-dialog__error{color:var(--edge-color-danger-text,var(--edge-color-danger,#b42318));font-size:.76rem;margin:0}
</style>
