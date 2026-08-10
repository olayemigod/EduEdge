<template>
	<EdgeModal
		:open="open"
		title="Replace / Handover Instructor Assignment"
		subtitle="Preserve the outgoing responsibility as history and create one exact successor responsibility."
		size="lg"
		:busy="busy"
		@close="close"
	>
		<div class="eduedge-replacement-dialog" data-eduedge-terminology-managed>
			<section class="eduedge-replacement-source">
				<p class="edge-eyebrow eduedge-replacement-kicker">Outgoing responsibility</p>
				<strong class="eduedge-replacement-source__title">{{ item.assignment_title || item.assignment_type || item.name }}</strong>
				<small class="eduedge-replacement-help">
					Handover Date is the outgoing Instructor's final responsibility day. The incoming Instructor starts the following day. The original assignment remains as history.
				</small>
			</section>

			<div class="eduedge-replacement-fields">
				<label class="eduedge-replacement-field">
					<span class="eduedge-replacement-label">Replacement Instructor <b>*</b></span>
					<EdgeLinkField
						:model-value="form.replacement_instructor"
						:selected-label="replacementInstructorLabel"
						:options="instructorOptions"
						placeholder="Search active Instructor"
						:disabled="busy"
						:required="true"
						:error="fieldErrors.replacement_instructor || ''"
						:allow-clear="true"
						:open-on-focus="true"
						@update:model-value="setField('replacement_instructor', $event)"
					/>
					<small class="eduedge-replacement-help">Only active Instructors already available to your permissions are shown.</small>
				</label>

				<label class="eduedge-replacement-field">
					<span class="eduedge-replacement-label">Handover Date <b>*</b></span>
					<input
						:value="form.handover_date"
						type="date"
						class="form-control eduedge-replacement-control"
						:min="today"
						:max="item.valid_to || undefined"
						:disabled="busy"
						@input="setField('handover_date', $event.target.value)"
					/>
					<small class="eduedge-replacement-help">Final day of the outgoing responsibility. The successor starts the next calendar day.</small>
					<small v-if="fieldErrors.handover_date" class="eduedge-replacement-error">{{ fieldErrors.handover_date }}</small>
				</label>

				<label class="eduedge-replacement-field eduedge-replacement-field--wide">
					<span class="eduedge-replacement-label">Reason <b>*</b></span>
					<textarea
						:value="form.reason"
						rows="3"
						class="form-control eduedge-replacement-control"
						placeholder="Why is this responsibility being handed over?"
						:disabled="busy"
						@input="setField('reason', $event.target.value)"
					></textarea>
					<small v-if="fieldErrors.reason" class="eduedge-replacement-error">{{ fieldErrors.reason }}</small>
				</label>
			</div>

			<section class="eduedge-replacement-preview" :class="{ 'eduedge-replacement-preview--ready': previewPlan && !conflictCount }">
				<div class="eduedge-replacement-preview__heading">
					<div>
						<p class="edge-eyebrow eduedge-replacement-kicker">Server preview</p>
						<h3>{{ previewPlan ? 'Handover plan' : 'Preview required' }}</h3>
					</div>
					<EdgeStatusBadge
						v-if="previewPlan"
						:label="conflictCount ? `${conflictCount} conflict(s)` : 'Ready to confirm'"
						:status="conflictCount ? 'conflict' : 'ready'"
						:tone="conflictCount ? 'danger' : 'success'"
					/>
				</div>

				<p v-if="!previewPlan && !previewError" class="eduedge-replacement-help">Preview the current handover details before confirming. Changing any field after preview requires a fresh preview.</p>
				<p v-if="previewError" class="eduedge-replacement-error" role="alert">{{ previewError }}</p>

				<template v-if="previewPlan">
					<div v-if="conflictCount" class="eduedge-replacement-conflicts">
						<strong>Resolve these conflicts before replacing</strong>
						<ul>
							<li v-for="(conflict, index) in previewPlan.conflicts || []" :key="`${conflict.name || conflict.type || 'conflict'}-${index}`">
								{{ conflict.reason || conflict.type || conflict.name || 'Conflict' }}
							</li>
						</ul>
					</div>

					<div class="eduedge-replacement-plan-grid">
						<div class="eduedge-replacement-plan-card">
							<strong class="eduedge-replacement-plan-label">Outgoing responsibility</strong>
							<span>{{ previewPlan.source?.assignment_title || previewPlan.source?.name || item.name }}</span>
							<small>{{ previewPlan.source?.valid_from || 'No start restriction' }} → <b>{{ previewPlan.source?.final_valid_to || previewPlan.handover_date }}</b></small>
						</div>
						<div class="eduedge-replacement-plan-card">
							<strong class="eduedge-replacement-plan-label">Incoming responsibility</strong>
							<span>{{ previewPlan.successor?.instructor_name || previewPlan.successor?.instructor }} · {{ previewPlan.successor?.assignment_type }}</span>
							<small>{{ previewPlan.successor?.valid_from }} → {{ previewPlan.successor?.valid_to || 'Open ended' }}</small>
							<small>
								{{ previewPlan.successor?.school_branch }} · {{ previewPlan.successor?.program_offering }}
								<span v-if="previewPlan.successor?.student_group"> · {{ previewPlan.successor.student_group }}</span>
								<span v-if="previewPlan.successor?.course"> · {{ previewPlan.successor.course }}</span>
							</small>
						</div>
						<div class="eduedge-replacement-plan-card eduedge-replacement-plan-grid__wide">
							<strong class="eduedge-replacement-plan-label">Branch Eligibility impact</strong>
							<span>{{ branchImpactLabel(previewPlan.incoming_branch_eligibility) }}</span>
							<small v-if="previewPlan.incoming_branch_eligibility?.name">{{ previewPlan.incoming_branch_eligibility.name }}</small>
							<small>The outgoing Instructor's Branch Eligibility is not changed by Replace / Handover.</small>
						</div>
					</div>
				</template>
			</section>
		</div>

		<template #footer>
			<button type="button" class="edge-button eduedge-replacement-button eduedge-replacement-button--cancel" :disabled="busy" @click="close">Cancel</button>
			<button
				type="button"
				class="edge-button edge-button--primary eduedge-replacement-button eduedge-replacement-button--primary"
				:disabled="busy || (previewPlan && conflictCount > 0)"
				@click="primaryAction"
			>
				{{ busy ? busyLabel : previewPlan ? 'Confirm Replacement' : 'Preview Replacement' }}
			</button>
		</template>
	</EdgeModal>
</template>

<script>
function siteToday() {
	return frappe.datetime?.get_today?.() || new Date().toISOString().slice(0, 10);
}

function sameArgs(left, right) {
	return JSON.stringify(left || {}) === JSON.stringify(right || {});
}

export default {
	name: "InstructorAssignmentReplacementDialog",
	props: {
		item: { type: Object, required: true },
		instructors: { type: Array, default: () => [] },
		onBusy: { type: Function, default: null },
		onComplete: { type: Function, default: null },
		onClosed: { type: Function, default: null },
	},
	data() {
		return {
			open: true,
			busy: false,
			busyLabel: "Checking handover...",
			previewPlan: null,
			previewedArgs: null,
			previewError: "",
			fieldErrors: {},
			form: {
				replacement_instructor: "",
				handover_date: siteToday(),
				reason: "",
			},
		};
	},
	computed: {
		today() { return siteToday(); },
		instructorOptions() {
			return (this.instructors || [])
				.filter((row) => row?.name && row.name !== this.item.instructor && String(row.status || "Active") === "Active")
				.map((row) => ({
					value: row.name,
					label: row.instructor_name || row.name,
					description: [row.department, row.home_institution_name].filter(Boolean).join(" · "),
				}));
		},
		replacementInstructorLabel() {
			const selected = this.instructorOptions.find((row) => row.value === this.form.replacement_instructor);
			return selected?.label || this.form.replacement_instructor || "";
		},
		conflictCount() { return Number(this.previewPlan?.conflict_count || 0); },
	},
	methods: {
		setField(fieldname, value) {
			this.form = { ...this.form, [fieldname]: value };
			this.fieldErrors = { ...this.fieldErrors, [fieldname]: "" };
			this.invalidatePreview();
		},
		invalidatePreview() {
			this.previewPlan = null;
			this.previewedArgs = null;
			this.previewError = "";
		},
		args() {
			return {
				name: this.item.name,
				replacement_instructor: String(this.form.replacement_instructor || "").trim(),
				handover_date: String(this.form.handover_date || "").trim(),
				reason: String(this.form.reason || "").trim(),
			};
		},
		validate() {
			const args = this.args();
			const errors = {};
			if (!args.replacement_instructor) errors.replacement_instructor = "Select the incoming Instructor.";
			if (args.replacement_instructor === this.item.instructor) errors.replacement_instructor = "Replacement Instructor must be different from the outgoing Instructor.";
			if (!args.handover_date) errors.handover_date = "Select the Handover Date.";
			if (!args.reason) errors.reason = "Give a reason for the handover.";
			else if (args.reason.length < 3) errors.reason = "Give a short reason of at least 3 characters.";
			this.fieldErrors = errors;
			return !Object.keys(errors).length;
		},
		branchImpactLabel(branch) {
			const action = String(branch?.action || "");
			if (action === "existing") return "Existing Branch Eligibility already covers the successor period; no Branch change will be made.";
			if (action === "create") return "A Branch Eligibility period will be created for the incoming Instructor.";
			if (action === "extend") return "The incoming Instructor's existing Branch Eligibility will be extended only as required for this responsibility.";
			if (action === "enable") return "An exact disabled Branch Eligibility period will be re-enabled for the incoming Instructor.";
			return "Branch Eligibility impact is unavailable. Do not confirm until the preview is complete.";
		},
		setBusy(value, label) {
			this.busy = Boolean(value);
			this.busyLabel = label || "Working...";
			this.onBusy?.(this.busy ? this.item.name : "");
		},
		async primaryAction() {
			if (this.previewPlan) await this.confirmReplacement();
			else await this.previewReplacement();
		},
		async previewReplacement() {
			if (!this.validate()) return;
			this.previewError = "";
			this.setBusy(true, "Checking handover...");
			const currentArgs = this.args();
			try {
				const response = await frappe.call({
					method: "eduedge.api.instructor_assignment_replacement.preview_instructor_assignment_replacement",
					type: "POST",
					args: currentArgs,
				});
				this.previewPlan = response.message || null;
				this.previewedArgs = this.previewPlan ? currentArgs : null;
				if (this.previewPlan?.already_replaced) {
					this.previewError = "This responsibility already has a successor. Refresh the register to see the lifecycle relationship.";
					this.previewPlan = null;
					this.previewedArgs = null;
				}
			} catch (error) {
				this.previewPlan = null;
				this.previewedArgs = null;
				this.previewError = error?.message || "Replacement preview failed.";
			} finally {
				this.setBusy(false);
			}
		},
		async confirmReplacement() {
			if (!this.previewPlan || !this.validate() || this.conflictCount) return;
			const currentArgs = this.args();
			if (!sameArgs(currentArgs, this.previewedArgs)) {
				this.invalidatePreview();
				this.previewError = "Replacement details changed after preview. Preview the current values again before confirming.";
				return;
			}

			let completed = false;
			this.setBusy(true, "Replacing assignment...");
			try {
				const response = await frappe.call({
					method: "eduedge.api.instructor_assignment_replacement.replace_instructor_assignment",
					type: "POST",
					args: currentArgs,
				});
				const result = response.message || {};
				frappe.show_alert({
					message: result.action === "already-replaced" ? "Instructor Assignment was already replaced" : "Instructor Assignment replaced and handed over",
					indicator: "green",
				});
				await this.onComplete?.(result);
				completed = true;
			} catch (error) {
				this.previewPlan = null;
				this.previewedArgs = null;
				this.previewError = error?.message || "Instructor Assignment could not be replaced.";
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
.eduedge-replacement-dialog {
	display: grid;
	gap: 1rem;
	color: var(--edge-color-ink-900, #172033);
}
.eduedge-replacement-source,
.eduedge-replacement-preview {
	border: 1px solid var(--edge-color-border, #d8e2ee);
	border-radius: .85rem;
	display: grid;
	gap: .45rem;
	padding: 1rem;
}
.eduedge-replacement-source {
	background: linear-gradient(180deg, var(--edge-color-surface-subtle, #f7f9fc), var(--edge-color-surface, #fff));
}
.eduedge-replacement-kicker {
	font-size: .7rem;
	font-weight: 800;
	letter-spacing: .08em;
	margin: 0;
	text-transform: uppercase;
}
.eduedge-replacement-source__title {
	font-size: .98rem;
	line-height: 1.45;
}
.eduedge-replacement-fields {
	display: grid;
	gap: .9rem;
	grid-template-columns: repeat(2, minmax(0, 1fr));
}
.eduedge-replacement-field {
	display: grid;
	gap: .4rem;
	min-width: 0;
}
.eduedge-replacement-field--wide { grid-column: 1 / -1; }
.eduedge-replacement-label,
.eduedge-replacement-plan-label {
	color: var(--edge-color-ink-800, #253349);
	font-size: .78rem;
	font-weight: 800;
	letter-spacing: .015em;
}
.eduedge-replacement-label b { color: var(--edge-color-danger-600, #b42318); }
.eduedge-replacement-help,
.eduedge-replacement-plan-card small {
	color: var(--edge-color-ink-500, #6b7d90);
	font-size: .75rem;
	font-weight: 500;
	line-height: 1.45;
}
.eduedge-replacement-control,
:deep(.edge-link-field__input) {
	background: var(--edge-color-surface, #fff);
	border: 1px solid var(--edge-color-border-strong, #c8d4e2);
	border-radius: .65rem;
	box-shadow: none;
	min-height: 2.7rem;
	padding: .58rem .72rem;
	transition: border-color .16s ease, box-shadow .16s ease, background .16s ease;
}
.eduedge-replacement-control:focus,
:deep(.edge-link-field__input:focus) {
	border-color: var(--edge-color-brand-500, #2877c7);
	box-shadow: 0 0 0 3px rgb(40 119 199 / 14%);
	outline: none;
}
.eduedge-replacement-control:disabled,
:deep(.edge-link-field__input:disabled) {
	background: var(--edge-color-surface-subtle, #f4f7fb);
	cursor: not-allowed;
	opacity: .72;
}
.eduedge-replacement-preview--ready {
	border-color: var(--edge-color-success-300, #9dd9b1);
	box-shadow: inset 0 0 0 1px rgb(30 150 90 / 5%);
}
.eduedge-replacement-preview__heading {
	align-items: center;
	display: flex;
	gap: .75rem;
	justify-content: space-between;
}
.eduedge-replacement-preview__heading h3 { font-size: 1rem; margin: .15rem 0 0; }
.eduedge-replacement-plan-grid {
	display: grid;
	gap: .75rem;
	grid-template-columns: repeat(2, minmax(0, 1fr));
}
.eduedge-replacement-plan-card {
	background: var(--edge-color-surface-subtle, #f7f9fc);
	border: 1px solid var(--edge-color-border, #e0e7ef);
	border-radius: .65rem;
	display: grid;
	gap: .28rem;
	padding: .8rem;
}
.eduedge-replacement-plan-grid__wide { grid-column: 1 / -1; }
.eduedge-replacement-conflicts,
.eduedge-replacement-error {
	color: var(--edge-color-danger-600, #b42318);
	font-size: .78rem;
	font-weight: 600;
}
.eduedge-replacement-conflicts {
	background: var(--edge-color-danger-50, #fff5f4);
	border: 1px solid var(--edge-color-danger-200, #f7c8c3);
	border-radius: .65rem;
	padding: .75rem;
}
.eduedge-replacement-conflicts ul { margin: .4rem 0 0; padding-left: 1.25rem; }
.eduedge-replacement-button {
	align-items: center;
	border-radius: .65rem;
	display: inline-flex;
	font-size: .78rem;
	font-weight: 800;
	justify-content: center;
	min-height: 2.5rem;
	min-width: 8rem;
	padding: .55rem .9rem;
	transition: transform .14s ease, box-shadow .14s ease, border-color .14s ease;
}
.eduedge-replacement-button:not(:disabled):hover { transform: translateY(-1px); }
.eduedge-replacement-button--cancel {
	background: var(--edge-color-surface, #fff);
	border: 1px solid var(--edge-color-border-strong, #c8d4e2);
	color: var(--edge-color-ink-700, #34445a);
}
.eduedge-replacement-button--primary {
	box-shadow: 0 .25rem .7rem rgb(20 94 168 / 18%);
}
.eduedge-replacement-button:disabled { cursor: not-allowed; opacity: .58; transform: none; }
@media (max-width: 48rem) {
	.eduedge-replacement-fields,
	.eduedge-replacement-plan-grid { grid-template-columns: 1fr; }
	.eduedge-replacement-field--wide,
	.eduedge-replacement-plan-grid__wide { grid-column: auto; }
	.eduedge-replacement-preview__heading { align-items: flex-start; flex-direction: column; }
	.eduedge-replacement-button { flex: 1 1 0; min-width: 0; }
}
</style>
