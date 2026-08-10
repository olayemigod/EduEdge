<template>
	<EdgeModal
		:open="open"
		title="Manage Assignment Capabilities"
		subtitle="Grant only the operational permissions that belong to this exact Subject responsibility."
		size="md"
		:busy="busy"
		@close="close"
	>
		<div class="eduedge-assignment-capability-dialog" data-eduedge-assignment-capability-dialog>
			<section class="eduedge-assignment-capability-source">
				<p class="edge-eyebrow">Exact Subject responsibility</p>
				<strong>{{ sourceTitle }}</strong>
				<small>{{ periodLabel }}</small>
			</section>

			<section class="eduedge-assignment-capability-note">
				<strong>Assignment capabilities are not Question Governance.</strong>
				<span>These permissions follow the exact Instructor, Branch, Class, Class Arm, Subject and effective dates of this assignment.</span>
				<small>Subject review and final approval remain controlled separately through Question Responsibility governance.</small>
			</section>

			<div class="eduedge-assignment-capability-grid">
				<label v-for="item in capabilityOptions" :key="item.fieldname" class="eduedge-assignment-capability-option">
					<input
						type="checkbox"
						:checked="Boolean(form[item.fieldname])"
						:disabled="busy"
						@change="setCapability(item.fieldname, $event.target.checked)"
					/>
					<span>
						<strong>{{ item.label }}</strong>
						<small>{{ item.description }}</small>
					</span>
				</label>
			</div>

			<section v-if="lastUpdateLabel" class="eduedge-assignment-capability-audit">
				<strong>Latest capability update</strong>
				<span>{{ lastUpdateLabel }}</span>
				<small v-if="item.capabilities_update_reason">{{ item.capabilities_update_reason }}</small>
			</section>

			<label class="eduedge-assignment-capability-reason">
				<span>Reason <b>*</b></span>
				<textarea
					:value="reason"
					rows="3"
					class="form-control"
					placeholder="Why are these operational capabilities being changed?"
					:disabled="busy"
					@input="reason = $event.target.value; error = ''"
				></textarea>
				<small v-if="reasonError" class="eduedge-assignment-capability-error">{{ reasonError }}</small>
			</label>

			<p v-if="error" class="eduedge-assignment-capability-error" role="alert">{{ error }}</p>
		</div>

		<template #footer>
			<button type="button" class="edge-button" :disabled="busy" @click="close">Cancel</button>
			<button type="button" class="edge-button edge-button--primary" :disabled="busy || !canSave" @click="save">
				{{ busy ? 'Saving capabilities...' : 'Save Capabilities' }}
			</button>
		</template>
	</EdgeModal>
</template>

<script>
const CAPABILITY_OPTIONS = [
	{
		fieldname: "can_view_subject_content",
		label: "View Subject Content",
		description: "Access the Subject content within this exact teaching responsibility.",
	},
	{
		fieldname: "can_manage_subject_topics",
		label: "Manage Subject Topics",
		description: "Create or maintain Topics within the exact assigned Subject context.",
	},
	{
		fieldname: "can_author_cbt",
		label: "Author CBT Questions",
		description: "Author CBT material for the exact assigned Subject context. Review and final approval remain separate.",
	},
	{
		fieldname: "can_create_assessment_plans",
		label: "Create Assessment Plans",
		description: "Create assessment plans only for the exact assigned Class and Subject context.",
	},
	{
		fieldname: "can_enter_marks",
		label: "Enter Marks",
		description: "Enter marks for Students covered by this exact assignment context.",
	},
];

function initialCapabilities(item) {
	const source = item?.capabilities || {};
	return Object.fromEntries(CAPABILITY_OPTIONS.map((option) => [option.fieldname, Number(source[option.fieldname] || 0)]));
}

function sameCapabilities(left, right) {
	return CAPABILITY_OPTIONS.every((option) => Number(left?.[option.fieldname] || 0) === Number(right?.[option.fieldname] || 0));
}

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
	name: "InstructorAssignmentCapabilityDialog",
	props: {
		item: { type: Object, required: true },
		onBusy: { type: Function, default: null },
		onComplete: { type: Function, default: null },
		onClosed: { type: Function, default: null },
	},
	data() {
		return {
			open: true,
			busy: false,
			form: initialCapabilities(this.item),
			original: initialCapabilities(this.item),
			reason: "",
			error: "",
		};
	},
	computed: {
		capabilityOptions() { return CAPABILITY_OPTIONS; },
		sourceTitle() { return this.item.assignment_title || "Instructor Assignment"; },
		periodLabel() { return `${this.item.valid_from || "No start restriction"} → ${this.item.valid_to || "Open ended"}`; },
		lastUpdateLabel() {
			const parts = [this.item.capabilities_updated_on, this.item.capabilities_updated_by].filter(Boolean);
			return parts.join(" · ");
		},
		reasonError() {
			const value = String(this.reason || "").trim();
			if (!value) return "Give a reason for changing these capabilities.";
			if (value.length < 3) return "Give a short reason of at least 3 characters.";
			return "";
		},
		hasChanges() { return !sameCapabilities(this.form, this.original); },
		canSave() { return Boolean(this.item.capability_version && this.hasChanges && !this.reasonError); },
	},
	methods: {
		setCapability(fieldname, checked) {
			const next = { ...this.form, [fieldname]: checked ? 1 : 0 };
			if (fieldname === "can_view_subject_content" && !checked) {
				for (const option of CAPABILITY_OPTIONS) next[option.fieldname] = 0;
			}
			if (fieldname !== "can_view_subject_content" && checked) next.can_view_subject_content = 1;
			this.form = next;
			this.error = "";
		},
		setBusy(value) {
			this.busy = Boolean(value);
			this.onBusy?.(this.busy ? this.item.name : "");
		},
		async save() {
			if (!this.canSave || this.busy) return;
			this.error = "";
			this.setBusy(true);
			let completed = false;
			try {
				const response = await frappe.call({
					method: "eduedge.api.instructor_assignment_capabilities.update_instructor_assignment_capabilities",
					type: "POST",
					args: {
						name: this.item.name,
						capabilities: JSON.stringify(this.form),
						reason: String(this.reason || "").trim(),
						expected_modified: this.item.capability_version,
					},
				});
				const result = response.message || {};
				frappe.show_alert({
					message: result.action === "already-configured" ? "Assignment capabilities already match" : "Assignment capabilities updated",
					indicator: "green",
				});
				await this.onComplete?.(result);
				completed = true;
			} catch (error) {
				this.error = serverErrorMessage(error, "Assignment capabilities could not be updated.");
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
.eduedge-assignment-capability-dialog { display: grid; gap: 1rem; }
.eduedge-assignment-capability-source, .eduedge-assignment-capability-note, .eduedge-assignment-capability-audit { border: 1px solid var(--edge-color-border, #d8e2ee); border-radius: .85rem; display: grid; gap: .35rem; padding: .9rem; }
.eduedge-assignment-capability-source { background: var(--edge-color-surface-subtle, #f7f9fc); }
.eduedge-assignment-capability-source p { margin: 0; }
.eduedge-assignment-capability-source small, .eduedge-assignment-capability-note small, .eduedge-assignment-capability-audit small, .eduedge-assignment-capability-option small { color: var(--edge-color-ink-500, #687a90); }
.eduedge-assignment-capability-grid { display: grid; gap: .65rem; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.eduedge-assignment-capability-option { align-items: flex-start; border: 1px solid var(--edge-color-border, #d8e2ee); border-radius: .75rem; display: flex; gap: .65rem; padding: .75rem; }
.eduedge-assignment-capability-option > span { display: grid; gap: .2rem; }
.eduedge-assignment-capability-option input { margin-top: .2rem; }
.eduedge-assignment-capability-reason { display: grid; gap: .4rem; }
.eduedge-assignment-capability-reason > span { font-size: .76rem; font-weight: 800; }
.eduedge-assignment-capability-error { color: var(--edge-color-danger-700, #b42318); font-size: .76rem; margin: 0; }
@media (max-width: 620px) { .eduedge-assignment-capability-grid { grid-template-columns: 1fr; } }
</style>
