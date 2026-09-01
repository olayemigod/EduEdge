<template>
	<EdgeModal
		:open="open"
		title="Transfer Instructor Assignment"
		subtitle="Close the current responsibility as history and move the same Instructor to one explicitly selected academic responsibility."
		size="lg"
		:busy="busy"
		@close="close"
	>
		<div class="eduedge-transfer-dialog" data-eduedge-terminology-managed>
			<section class="eduedge-transfer-source">
				<p class="edge-eyebrow eduedge-transfer-kicker">Current responsibility</p>
				<strong class="eduedge-transfer-source__title">{{ sourceTitle }}</strong>
				<small class="eduedge-transfer-help">
					Transfer Date is the current responsibility's final day. The same Instructor starts the destination responsibility on the following calendar day. The source assignment remains as history.
				</small>
			</section>

			<div class="eduedge-transfer-fields">
				<label class="eduedge-transfer-field">
					<span class="eduedge-transfer-label">Destination Branch / Campus <b>*</b></span>
					<EdgeLinkField
						:model-value="form.destination_branch"
						:selected-label="branchLabel(form.destination_branch)"
						:options="branchOptions"
						placeholder="Select destination Branch / Campus"
						:disabled="busy"
						:required="true"
						:error="fieldErrors.destination_branch || ''"
						:allow-clear="true"
						:open-on-focus="true"
						@update:model-value="setField('destination_branch', $event)"
					/>
					<small class="eduedge-transfer-help">Only Branches available to your current permissions are shown.</small>
				</label>

				<label class="eduedge-transfer-field">
					<span class="eduedge-transfer-label">Destination Class / Programme Offering <b>*</b></span>
					<EdgeLinkField
						:model-value="form.destination_program_offering"
						:selected-label="offeringLabel(form.destination_program_offering)"
						:options="offeringOptions"
						placeholder="Select destination Class"
						:disabled="busy || !form.destination_branch"
						:required="true"
						:error="fieldErrors.destination_program_offering || ''"
						:allow-clear="true"
						:open-on-focus="true"
						@update:model-value="setField('destination_program_offering', $event)"
					/>
					<small class="eduedge-transfer-help">Changing Branch clears the selected Class, Class Arm and Subject.</small>
				</label>

				<label v-if="requiresClassArm" class="eduedge-transfer-field">
					<span class="eduedge-transfer-label">Destination Class Arm <b>*</b></span>
					<EdgeLinkField
						:model-value="form.destination_student_group"
						:selected-label="groupLabel(form.destination_student_group)"
						:options="groupOptions"
						placeholder="Select destination Class Arm"
						:disabled="busy || !form.destination_program_offering"
						:required="true"
						:error="fieldErrors.destination_student_group || ''"
						:allow-clear="true"
						:open-on-focus="true"
						@update:model-value="setField('destination_student_group', $event)"
					/>
				</label>

				<label v-if="requiresCourse" class="eduedge-transfer-field">
					<span class="eduedge-transfer-label">Destination Subject / Course <b>*</b></span>
					<EdgeLinkField
						:model-value="form.destination_course"
						:selected-label="courseLabel(form.destination_course)"
						:options="courseOptions"
						placeholder="Select curriculum Subject"
						:disabled="busy || !form.destination_program_offering"
						:required="true"
						:error="fieldErrors.destination_course || ''"
						:allow-clear="true"
						:open-on-focus="true"
						@update:model-value="setField('destination_course', $event)"
					/>
					<small class="eduedge-transfer-help">Only Subjects already configured in the selected Class curriculum are shown. Transfer never changes curriculum.</small>
				</label>

				<label class="eduedge-transfer-field">
					<span class="eduedge-transfer-label">Transfer Date <b>*</b></span>
					<input
						:value="form.transfer_date"
						type="date"
						class="form-control eduedge-transfer-control"
						:min="today"
						:max="item.valid_to || undefined"
						:disabled="busy"
						@input="setField('transfer_date', $event.target.value)"
					/>
					<small class="eduedge-transfer-help">Final day of the current responsibility. The destination starts the next calendar day.</small>
					<small v-if="fieldErrors.transfer_date" class="eduedge-transfer-error">{{ fieldErrors.transfer_date }}</small>
				</label>

				<label class="eduedge-transfer-field eduedge-transfer-field--wide">
					<span class="eduedge-transfer-label">Reason <b>*</b></span>
					<textarea
						:value="form.reason"
						rows="3"
						class="form-control eduedge-transfer-control"
						placeholder="Why is this responsibility being transferred?"
						:disabled="busy"
						@input="setField('reason', $event.target.value)"
					></textarea>
					<small v-if="fieldErrors.reason" class="eduedge-transfer-error">{{ fieldErrors.reason }}</small>
				</label>
			</div>

			<section class="eduedge-transfer-preview" :class="{ 'eduedge-transfer-preview--ready': previewPlan && !conflictCount }">
				<div class="eduedge-transfer-preview__heading">
					<div>
						<p class="edge-eyebrow eduedge-transfer-kicker">Server preview</p>
						<h3>{{ previewPlan ? 'Transfer plan' : 'Preview required' }}</h3>
					</div>
					<EdgeStatusBadge
						v-if="previewPlan"
						:label="conflictCount ? `${conflictCount} conflict(s)` : 'Ready to confirm'"
						:status="conflictCount ? 'conflict' : 'ready'"
						:tone="conflictCount ? 'danger' : 'success'"
					/>
				</div>

				<p v-if="!previewPlan && !previewError" class="eduedge-transfer-help">Preview the current destination before confirming. Changing any field after preview requires a fresh server preview.</p>
				<p v-if="previewError" class="eduedge-transfer-error" role="alert">{{ previewError }}</p>

				<template v-if="previewPlan">
					<div v-if="conflictCount" class="eduedge-transfer-conflicts">
						<strong>Resolve these conflicts before transferring</strong>
						<ul>
							<li v-for="(conflict, index) in previewPlan.conflicts || []" :key="`${conflict.type || 'conflict'}-${index}`">
								{{ conflict.reason || conflictLabel(conflict) }}
							</li>
						</ul>
					</div>

					<div class="eduedge-transfer-plan-grid">
						<div class="eduedge-transfer-plan-card">
							<strong class="eduedge-transfer-plan-label">Current responsibility</strong>
							<span>{{ previewPlan.source?.assignment_title || sourceTitle }}</span>
							<small>{{ previewPlan.source?.valid_from || 'No start restriction' }} → <b>{{ previewPlan.source?.final_valid_to || previewPlan.transfer_date }}</b></small>
						</div>
						<div class="eduedge-transfer-plan-card">
							<strong class="eduedge-transfer-plan-label">Destination responsibility</strong>
							<span>{{ destinationTitle(previewPlan.destination) }}</span>
							<small>{{ previewPlan.destination?.valid_from }} → {{ previewPlan.destination?.valid_to || 'Open ended' }}</small>
						</div>
						<div class="eduedge-transfer-plan-card eduedge-transfer-plan-grid__wide">
							<strong class="eduedge-transfer-plan-label">Branch Eligibility impact</strong>
							<span>{{ branchImpactLabel(previewPlan.destination_branch_eligibility) }}</span>
							<small>{{ branchEligibilitySummary(previewPlan.destination_branch_eligibility) }}</small>
							<small>The source Branch Eligibility is not shortened or deleted by Transfer.</small>
						</div>
					</div>
				</template>
			</section>
		</div>

		<template #footer>
			<button type="button" class="edge-button eduedge-transfer-button eduedge-transfer-button--cancel" :disabled="busy" @click="close">Cancel</button>
			<button
				type="button"
				class="edge-button edge-button--primary eduedge-transfer-button eduedge-transfer-button--primary"
				:disabled="busy || (previewPlan && conflictCount > 0)"
				@click="primaryAction"
			>
				{{ busy ? busyLabel : previewPlan ? 'Confirm Transfer' : 'Preview Transfer' }}
			</button>
		</template>
	</EdgeModal>
</template>

<script>
const SUBJECT_REQUIRED_TYPES = new Set([
	"Subject Instructor",
	"Lecturer",
	"Tutor",
	"Practical Instructor",
	"Assistant Instructor",
]);

function siteToday() {
	return frappe.datetime?.get_today?.() || new Date().toISOString().slice(0, 10);
}

function addOneDay(value) {
	if (!value) return "";
	const date = new Date(`${value}T00:00:00Z`);
	if (Number.isNaN(date.getTime())) return "";
	date.setUTCDate(date.getUTCDate() + 1);
	return date.toISOString().slice(0, 10);
}

function sameArgs(left, right) {
	return JSON.stringify(left || {}) === JSON.stringify(right || {});
}

function cleanParts(parts) {
	return parts
		.map((value) => String(value || "").trim())
		.filter(Boolean)
		.filter((value, index, values) => values.indexOf(value) === index);
}

export default {
	name: "InstructorAssignmentTransferDialog",
	props: {
		item: { type: Object, required: true },
		displayContext: { type: Object, default: () => ({}) },
		onBusy: { type: Function, default: null },
		onComplete: { type: Function, default: null },
		onClosed: { type: Function, default: null },
	},
	data() {
		return {
			open: true,
			busy: false,
			busyLabel: "Checking transfer...",
			previewPlan: null,
			previewedArgs: null,
			previewError: "",
			fieldErrors: {},
			form: {
				destination_branch: this.item.school_branch || "",
				destination_program_offering: "",
				destination_student_group: "",
				destination_course: "",
				transfer_date: siteToday(),
				reason: "",
			},
		};
	},
	computed: {
		today() { return siteToday(); },
		requiresClassArm() { return this.item.assignment_scope === "Class Arm"; },
		requiresCourse() { return SUBJECT_REQUIRED_TYPES.has(this.item.assignment_type); },
		successorStart() { return addOneDay(this.form.transfer_date); },
		sourceTitle() {
			if (this.item.assignment_title) return this.item.assignment_title;
			return cleanParts([
				this.item.instructor_name || this.item.instructor || "Instructor",
				this.item.assignment_type || "Academic responsibility",
				this.offeringLabel(this.item.program_offering),
				this.groupLabel(this.item.student_group),
				this.courseLabel(this.item.course),
			]).join(" · ");
		},
		branchOptions() {
			return (this.displayContext?.allowed_branches || [])
				.filter((row) => row?.name)
				.map((row) => ({
					value: row.name,
					label: row.branch_name || "Branch / Campus",
					description: row.institution_name || "",
				}));
		},
		offeringOptions() {
			const branch = this.form.destination_branch;
			const successorStart = this.successorStart;
			return (this.displayContext?.offerings || [])
				.filter((row) => row?.name && row.school_branch === branch)
				.filter((row) => !successorStart || (!row.period_start_date || successorStart >= row.period_start_date))
				.filter((row) => !successorStart || (!row.period_end_date || successorStart <= row.period_end_date))
				.map((row) => ({
					value: row.name,
					label: row.offering_title || row.program || "Class / Programme Offering",
					description: cleanParts([row.academic_year, row.academic_term]).join(" · "),
				}));
		},
		selectedOffering() {
			return (this.displayContext?.offerings || []).find((row) => row.name === this.form.destination_program_offering) || null;
		},
		groupOptions() {
			if (!this.requiresClassArm || !this.selectedOffering) return [];
			const offering = this.selectedOffering;
			return (this.displayContext?.groups || [])
				.filter((row) => row?.name && !Number(row.disabled || 0))
				.filter((row) => row.eduedge_school_branch === offering.school_branch || row.school_branch === offering.school_branch)
				.filter((row) => !row.program || row.program === offering.program)
				.filter((row) => !row.academic_year || row.academic_year === offering.academic_year)
				.filter((row) => !row.academic_term || row.academic_term === offering.academic_term)
				.filter((row) => {
					const linkedOffering = row.eduedge_program_offering || row.program_offering || "";
					return !linkedOffering || linkedOffering === offering.name;
				})
				.map((row) => ({
					value: row.name,
					label: row.eduedge_display_name || row.student_group_name || "Class Arm",
					description: offering.offering_title || offering.program || "",
				}));
		},
		courseOptions() {
			if (!this.requiresCourse || !this.selectedOffering) return [];
			const configured = new Set(this.displayContext?.configured_course_map?.[this.selectedOffering.program] || []);
			return (this.displayContext?.courses || [])
				.filter((row) => row?.name && configured.has(row.name))
				.map((row) => ({
					value: row.name,
					label: row.course_name || "Subject / Course",
					description: this.selectedOffering.offering_title || this.selectedOffering.program || "",
				}));
		},
		conflictCount() { return Number(this.previewPlan?.conflict_count || 0); },
	},
	methods: {
		branchLabel(name) {
			if (!name) return "";
			const row = (this.displayContext?.allowed_branches || []).find((item) => item.name === name);
			return row?.branch_name || "Selected Branch / Campus";
		},
		offeringLabel(name) {
			if (!name) return "";
			const row = (this.displayContext?.offerings || []).find((item) => item.name === name);
			return row?.offering_title || row?.program || "Selected Class / Programme Offering";
		},
		groupLabel(name) {
			if (!name) return "";
			const row = (this.displayContext?.groups || []).find((item) => item.name === name);
			return row?.eduedge_display_name || row?.student_group_name || "Selected Class Arm";
		},
		courseLabel(name) {
			if (!name) return "";
			const row = (this.displayContext?.courses || []).find((item) => item.name === name);
			return row?.course_name || "Selected Subject / Course";
		},
		destinationTitle(destination) {
			return cleanParts([
				destination?.instructor_name || this.item.instructor_name || this.item.instructor || "Instructor",
				destination?.assignment_type || this.item.assignment_type,
				destination?.offering_title || this.offeringLabel(destination?.program_offering),
				destination?.student_group_name || this.groupLabel(destination?.student_group),
				destination?.course_name || this.courseLabel(destination?.course),
			]).join(" · ");
		},
		branchEligibilitySummary(branch) {
			if (!branch) return "Branch Eligibility details unavailable.";
			const start = branch.valid_from || "No start restriction";
			const end = branch.valid_to || "Open ended";
			return cleanParts([
				branch.instructor_name || this.item.instructor_name || this.item.instructor || "Instructor",
				branch.branch_name || this.branchLabel(branch.school_branch),
				`${start} → ${end}`,
			]).join(" · ");
		},
		conflictLabel(conflict) {
			if (conflict?.type === "transferring-instructor-overlap") return "Instructor already has an overlapping exact responsibility in the destination context.";
			if (conflict?.type === "primary-responsibility-overlap") return "Another Instructor already owns this primary responsibility in the destination period.";
			return "Transfer conflict";
		},
		setField(fieldname, value) {
			const next = { ...this.form, [fieldname]: value };
			if (fieldname === "destination_branch") {
				next.destination_program_offering = "";
				next.destination_student_group = "";
				next.destination_course = "";
			}
			if (fieldname === "destination_program_offering") {
				next.destination_student_group = "";
				next.destination_course = "";
			}
			this.form = next;
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
				destination_branch: String(this.form.destination_branch || "").trim(),
				destination_program_offering: String(this.form.destination_program_offering || "").trim(),
				destination_student_group: this.requiresClassArm ? String(this.form.destination_student_group || "").trim() : "",
				destination_course: this.requiresCourse ? String(this.form.destination_course || "").trim() : "",
				transfer_date: String(this.form.transfer_date || "").trim(),
				reason: String(this.form.reason || "").trim(),
			};
		},
		validate() {
			const args = this.args();
			const errors = {};
			if (!args.destination_branch) errors.destination_branch = "Select the destination Branch / Campus.";
			if (!args.destination_program_offering) errors.destination_program_offering = "Select the destination Class / Programme Offering.";
			if (this.requiresClassArm && !args.destination_student_group) errors.destination_student_group = "Select the destination Class Arm.";
			if (this.requiresCourse && !args.destination_course) errors.destination_course = "Select the destination Subject / Course.";
			if (!args.transfer_date) errors.transfer_date = "Select the Transfer Date.";
			if (!args.reason) errors.reason = "Give a reason for the transfer.";
			else if (args.reason.length < 3) errors.reason = "Give a short reason of at least 3 characters.";
			const sameDestination =
				args.destination_branch === String(this.item.school_branch || "")
				&& args.destination_program_offering === String(this.item.program_offering || "")
				&& args.destination_student_group === String(this.item.student_group || "")
				&& args.destination_course === String(this.item.course || "");
			if (sameDestination) errors.destination_program_offering = "Transfer destination must differ from the current academic responsibility.";
			this.fieldErrors = errors;
			return !Object.keys(errors).length;
		},
		branchImpactLabel(branch) {
			const action = String(branch?.action || "");
			if (action === "existing") return "Existing Branch Eligibility already covers the destination period; no Branch change will be made.";
			if (action === "create") return "A Branch Eligibility period will be created for the Instructor in the destination Branch.";
			if (action === "extend") return "Existing Branch Eligibility will be extended only as required for the destination responsibility.";
			if (action === "enable") return "An exact disabled Branch Eligibility period will be re-enabled for the destination responsibility.";
			return "Branch Eligibility impact is unavailable. Do not confirm until the preview is complete.";
		},
		setBusy(value, label) {
			this.busy = Boolean(value);
			this.busyLabel = label || "Working...";
			this.onBusy?.(this.busy ? this.item.name : "");
		},
		async primaryAction() {
			if (this.previewPlan) await this.confirmTransfer();
			else await this.previewTransfer();
		},
		async previewTransfer() {
			if (!this.validate()) return;
			this.previewError = "";
			this.setBusy(true, "Checking transfer...");
			const currentArgs = this.args();
			try {
				const response = await frappe.call({
					method: "eduedge.api.instructor_assignment_transfer.preview_instructor_assignment_transfer",
					type: "POST",
					args: currentArgs,
				});
				this.previewPlan = response.message || null;
				this.previewedArgs = this.previewPlan ? currentArgs : null;
				if (this.previewPlan?.already_transferred) {
					this.previewError = "This responsibility was already transferred. Refresh the register to see the lifecycle relationship.";
					this.previewPlan = null;
					this.previewedArgs = null;
				}
			} catch (error) {
				this.previewPlan = null;
				this.previewedArgs = null;
				this.previewError = error?.message || "Transfer preview failed.";
			} finally {
				this.setBusy(false);
			}
		},
		async confirmTransfer() {
			if (!this.previewPlan || !this.validate() || this.conflictCount) return;
			const currentArgs = this.args();
			if (!sameArgs(currentArgs, this.previewedArgs)) {
				this.invalidatePreview();
				this.previewError = "Transfer details changed after preview. Preview the current values again before confirming.";
				return;
			}

			let completed = false;
			this.setBusy(true, "Transferring assignment...");
			try {
				const response = await frappe.call({
					method: "eduedge.api.instructor_assignment_transfer.transfer_instructor_assignment",
					type: "POST",
					args: currentArgs,
				});
				const result = response.message || {};
				frappe.show_alert({
					message: result.action === "already-transferred" ? "Instructor Assignment was already transferred" : "Instructor Assignment transferred",
					indicator: "green",
				});
				await this.onComplete?.(result);
				completed = true;
			} catch (error) {
				this.previewPlan = null;
				this.previewedArgs = null;
				this.previewError = error?.message || "Instructor Assignment could not be transferred.";
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
.eduedge-transfer-dialog { display: grid; gap: 1rem; color: var(--edge-color-ink-900, #172033); }
.eduedge-transfer-source,
.eduedge-transfer-preview { border: 1px solid var(--edge-color-border, #d8e2ee); border-radius: .85rem; display: grid; gap: .45rem; padding: 1rem; }
.eduedge-transfer-source { background: linear-gradient(180deg, var(--edge-color-surface-subtle, #f7f9fc), var(--edge-color-surface, #fff)); }
.eduedge-transfer-kicker { font-size: .7rem; font-weight: 800; letter-spacing: .08em; margin: 0; text-transform: uppercase; }
.eduedge-transfer-source__title { font-size: .98rem; line-height: 1.45; }
.eduedge-transfer-fields { display: grid; gap: .9rem; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.eduedge-transfer-field { display: grid; gap: .4rem; min-width: 0; }
.eduedge-transfer-field--wide { grid-column: 1 / -1; }
.eduedge-transfer-label,
.eduedge-transfer-plan-label { color: var(--edge-color-ink-800, #253349); font-size: .78rem; font-weight: 800; letter-spacing: .015em; }
.eduedge-transfer-label b { color: var(--edge-color-danger-600, #b42318); }
.eduedge-transfer-help,
.eduedge-transfer-plan-card small { color: var(--edge-color-ink-500, #6b7d90); font-size: .75rem; font-weight: 500; line-height: 1.45; }
.eduedge-transfer-control { min-height: 2.35rem; }
.eduedge-transfer-control:focus { border-color: var(--edge-color-primary-500, #3b82f6); box-shadow: 0 0 0 3px rgba(59, 130, 246, .12); }
.eduedge-transfer-error { color: var(--edge-color-danger-700, #b42318); font-size: .76rem; font-weight: 600; }
.eduedge-transfer-preview--ready { border-color: var(--edge-color-success-300, #86d5a5); }
.eduedge-transfer-preview__heading { align-items: center; display: flex; gap: 1rem; justify-content: space-between; }
.eduedge-transfer-preview__heading h3 { font-size: .98rem; margin: .15rem 0 0; }
.eduedge-transfer-conflicts { background: var(--edge-color-danger-50, #fff5f4); border: 1px solid var(--edge-color-danger-200, #f4b4ad); border-radius: .7rem; color: var(--edge-color-danger-800, #912018); padding: .8rem; }
.eduedge-transfer-conflicts ul { margin: .45rem 0 0; padding-left: 1.1rem; }
.eduedge-transfer-plan-grid { display: grid; gap: .75rem; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.eduedge-transfer-plan-grid__wide { grid-column: 1 / -1; }
.eduedge-transfer-plan-card { background: var(--edge-color-surface-subtle, #f7f9fc); border-radius: .7rem; display: grid; gap: .3rem; padding: .8rem; }
.eduedge-transfer-plan-card span { font-size: .84rem; font-weight: 650; line-height: 1.45; }
.eduedge-transfer-button { min-width: 7.5rem; }
.eduedge-transfer-button--cancel { margin-right: .45rem; }
@media (max-width: 720px) {
	.eduedge-transfer-fields,
	.eduedge-transfer-plan-grid { grid-template-columns: 1fr; }
	.eduedge-transfer-field--wide,
	.eduedge-transfer-plan-grid__wide { grid-column: auto; }
}
</style>
