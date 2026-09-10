<template>
	<EdgeModal
		:open="open"
		title="Prepare Next Term / Session"
		subtitle="Create a separate future responsibility from this assignment without reopening, shortening or otherwise changing the source history."
		size="lg"
		:busy="busy"
		@close="close"
	>
		<div class="eduedge-preparation-dialog" data-eduedge-terminology-managed>
			<section class="eduedge-preparation-source">
				<div class="eduedge-preparation-source__heading">
					<div>
						<p class="edge-eyebrow eduedge-preparation-kicker">Source responsibility</p>
						<strong class="eduedge-preparation-source__title">{{ sourceTitle }}</strong>
					</div>
					<EdgeStatusBadge
						v-if="item.lifecycle_status"
						:label="item.lifecycle_status"
						:status="String(item.lifecycle_status || '').toLowerCase()"
						:tone="item.lifecycle_status === 'Current' ? 'success' : 'neutral'"
					/>
				</div>
				<small class="eduedge-preparation-help">{{ sourcePeriodSummary }}</small>
				<small class="eduedge-preparation-help">The source assignment and its Branch Eligibility remain unchanged. Preparation creates one new future responsibility.</small>
			</section>

			<div class="eduedge-preparation-fields">
				<label class="eduedge-preparation-field">
					<span class="eduedge-preparation-label">Destination Branch / Campus <b>*</b></span>
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
					<small class="eduedge-preparation-help">Only Branches available to your current permissions are shown.</small>
				</label>

				<label class="eduedge-preparation-field">
					<span class="eduedge-preparation-label">Destination Class / Programme Offering <b>*</b></span>
					<EdgeLinkField
						:model-value="form.destination_program_offering"
						:selected-label="offeringLabel(form.destination_program_offering)"
						:options="offeringOptions"
						placeholder="Select a later academic period"
						:disabled="busy || !form.destination_branch || !sourcePeriodEnd"
						:required="true"
						:error="fieldErrors.destination_program_offering || ''"
						:allow-clear="true"
						:open-on-focus="true"
						@update:model-value="setField('destination_program_offering', $event)"
					/>
					<small class="eduedge-preparation-help">Only active Classes whose academic period starts after the source academic period are shown.</small>
					<small v-if="form.destination_branch && sourcePeriodEnd && !offeringOptions.length" class="eduedge-preparation-warning">No later eligible Class / Programme Offering is available in this Branch.</small>
				</label>

				<label v-if="requiresClassArm" class="eduedge-preparation-field">
					<span class="eduedge-preparation-label">Destination Class Arm <b>*</b></span>
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

				<label v-if="requiresCourse" class="eduedge-preparation-field">
					<span class="eduedge-preparation-label">Destination Subject / Course <b>*</b></span>
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
					<small class="eduedge-preparation-help">Only Subjects already configured in the selected Class curriculum are shown. Preparation never changes curriculum.</small>
				</label>

				<label class="eduedge-preparation-field">
					<span class="eduedge-preparation-label">Valid From <b>*</b></span>
					<input
						:value="form.valid_from"
						type="date"
						class="form-control eduedge-preparation-control"
						:min="selectedOffering?.period_start_date || undefined"
						:max="selectedOffering?.period_end_date || undefined"
						:disabled="busy || !selectedOffering"
						@input="setField('valid_from', $event.target.value)"
					/>
					<small class="eduedge-preparation-help">Defaults to the selected destination academic period start date.</small>
					<small v-if="fieldErrors.valid_from" class="eduedge-preparation-error">{{ fieldErrors.valid_from }}</small>
				</label>

				<label class="eduedge-preparation-field">
					<span class="eduedge-preparation-label">Valid To <b>*</b></span>
					<input
						:value="form.valid_to"
						type="date"
						class="form-control eduedge-preparation-control"
						:min="selectedOffering?.period_start_date || undefined"
						:max="selectedOffering?.period_end_date || undefined"
						:disabled="busy || !selectedOffering"
						@input="setField('valid_to', $event.target.value)"
					/>
					<small class="eduedge-preparation-help">Defaults to the selected destination academic period end date.</small>
					<small v-if="fieldErrors.valid_to" class="eduedge-preparation-error">{{ fieldErrors.valid_to }}</small>
				</label>

				<label class="eduedge-preparation-field eduedge-preparation-field--wide">
					<span class="eduedge-preparation-label">Preparation Reason <b>*</b></span>
					<textarea
						:value="form.reason"
						rows="3"
						class="form-control eduedge-preparation-control"
						placeholder="Why is this responsibility being prepared for the later academic period?"
						:disabled="busy"
						@input="setField('reason', $event.target.value)"
					></textarea>
					<small v-if="fieldErrors.reason" class="eduedge-preparation-error">{{ fieldErrors.reason }}</small>
				</label>
			</div>

			<section class="eduedge-preparation-preview" :class="{ 'eduedge-preparation-preview--ready': previewPlan && !conflictCount }">
				<div class="eduedge-preparation-preview__heading">
					<div>
						<p class="edge-eyebrow eduedge-preparation-kicker">Server preview</p>
						<h3>{{ previewPlan ? 'Preparation plan' : 'Preview required' }}</h3>
					</div>
					<EdgeStatusBadge
						v-if="previewPlan"
						:label="conflictCount ? `${conflictCount} conflict(s)` : 'Ready to confirm'"
						:status="conflictCount ? 'conflict' : 'ready'"
						:tone="conflictCount ? 'danger' : 'success'"
					/>
				</div>

				<p v-if="!previewPlan && !previewError" class="eduedge-preparation-help">Preview the future responsibility before confirming. Changing Branch, Class, Class Arm, Subject, dates or reason after preview requires a fresh server preview.</p>
				<p v-if="previewError" class="eduedge-preparation-error" role="alert">{{ previewError }}</p>

				<template v-if="previewPlan">
					<div v-if="conflictCount" class="eduedge-preparation-conflicts">
						<strong>Resolve these conflicts before preparing</strong>
						<ul>
							<li v-for="(conflict, index) in previewPlan.conflicts || []" :key="`${conflict.type || 'conflict'}-${index}`">
								{{ conflict.reason || conflictLabel(conflict) }}
							</li>
						</ul>
					</div>

					<div class="eduedge-preparation-plan-grid">
						<div class="eduedge-preparation-plan-card">
							<strong class="eduedge-preparation-plan-label">Source responsibility</strong>
							<span>{{ previewPlan.source?.assignment_title || sourceTitle }}</span>
							<small>{{ sourcePeriodSummary }}</small>
						</div>
						<div class="eduedge-preparation-plan-card">
							<strong class="eduedge-preparation-plan-label">Future responsibility</strong>
							<span>{{ destinationTitle(previewPlan.destination) }}</span>
							<small>{{ previewPlan.destination?.valid_from }} → {{ previewPlan.destination?.valid_to }}</small>
						</div>
						<div class="eduedge-preparation-plan-card eduedge-preparation-plan-grid__wide">
							<strong class="eduedge-preparation-plan-label">Branch Eligibility impact</strong>
							<span>{{ branchImpactLabel(previewPlan.destination_branch_eligibility) }}</span>
							<small>{{ branchEligibilitySummary(previewPlan.destination_branch_eligibility) }}</small>
							<small>The source Branch Eligibility is not shortened or deleted by preparation.</small>
						</div>
					</div>
				</template>
			</section>
		</div>

		<template #footer>
			<button type="button" class="edge-button eduedge-preparation-button" :disabled="busy" @click="close">Cancel</button>
			<button
				type="button"
				class="edge-button edge-button--primary eduedge-preparation-button"
				:disabled="busy || (previewPlan && conflictCount > 0)"
				@click="primaryAction"
			>
				{{ busy ? busyLabel : previewPlan ? 'Confirm Preparation' : 'Preview Preparation' }}
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

function sameArgs(left, right) {
	return JSON.stringify(left || {}) === JSON.stringify(right || {});
}

function cleanParts(parts) {
	return parts
		.map((value) => String(value || "").trim())
		.filter(Boolean)
		.filter((value, index, values) => values.indexOf(value) === index);
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
				} catch (e) {
					if (item) return String(item);
				}
			}
		} catch (e) {
			// Fall through to the stable product message below.
		}
	}
	return fallback;
}

export default {
	name: "InstructorAssignmentPreparationDialog",
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
			busyLabel: "Checking preparation...",
			previewPlan: null,
			previewedArgs: null,
			previewError: "",
			fieldErrors: {},
			form: {
				destination_branch: this.item.school_branch || "",
				destination_program_offering: "",
				destination_student_group: "",
				destination_course: "",
				valid_from: "",
				valid_to: "",
				reason: "",
			},
		};
	},
	computed: {
		requiresClassArm() { return this.item.assignment_scope === "Class Arm"; },
		requiresCourse() { return SUBJECT_REQUIRED_TYPES.has(this.item.assignment_type); },
		sourceOffering() {
			return (this.displayContext?.offerings || []).find((row) => row.name === this.item.program_offering) || null;
		},
		sourcePeriodEnd() {
			return String(this.item.preparation_source_period_end || this.sourceOffering?.period_end_date || "").slice(0, 10);
		},
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
		sourcePeriodSummary() {
			const offering = this.sourceOffering;
			const academicPeriod = cleanParts([
				offering?.academic_year,
				offering?.academic_term,
			]).join(" · ");
			const periodStart = offering?.period_start_date || this.item.valid_from || "No start restriction";
			const periodEnd = this.sourcePeriodEnd || "No bounded academic period";
			return cleanParts([
				academicPeriod,
				`${periodStart} → ${periodEnd}`,
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
			const sourceEnd = this.sourcePeriodEnd;
			if (!branch || !sourceEnd) return [];
			return (this.displayContext?.offerings || [])
				.filter((row) => row?.name && row.school_branch === branch)
				.filter((row) => row.name !== this.item.program_offering)
				.filter((row) => row.is_active === undefined || Number(row.is_active || 0))
				.filter((row) => row.period_start_date && row.period_end_date)
				.filter((row) => row.period_start_date > sourceEnd)
				.map((row) => ({
					value: row.name,
					label: row.offering_title || row.program || "Class / Programme Offering",
					description: cleanParts([
						row.academic_year,
						row.academic_term,
						`${row.period_start_date} → ${row.period_end_date}`,
					]).join(" · "),
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
				.filter((row) => !row.eduedge_institution || row.eduedge_institution === this.selectedOffering.institution)
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
			return "Preparation conflict";
		},
		setField(fieldname, value) {
			const next = { ...this.form, [fieldname]: value };
			if (fieldname === "destination_branch") {
				next.destination_program_offering = "";
				next.destination_student_group = "";
				next.destination_course = "";
				next.valid_from = "";
				next.valid_to = "";
			}
			if (fieldname === "destination_program_offering") {
				next.destination_student_group = "";
				next.destination_course = "";
				const offering = (this.displayContext?.offerings || []).find((row) => row.name === value);
				next.valid_from = offering?.period_start_date || "";
				next.valid_to = offering?.period_end_date || "";
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
				valid_from: String(this.form.valid_from || "").trim(),
				valid_to: String(this.form.valid_to || "").trim(),
				reason: String(this.form.reason || "").trim(),
			};
		},
		validate() {
			const args = this.args();
			const errors = {};
			if (!args.destination_branch) errors.destination_branch = "Select the destination Branch / Campus.";
			if (!args.destination_program_offering) errors.destination_program_offering = "Select a later Class / Programme Offering.";
			if (this.requiresClassArm && !args.destination_student_group) errors.destination_student_group = "Select the destination Class Arm.";
			if (this.requiresCourse && !args.destination_course) errors.destination_course = "Select the destination Subject / Course.";
			if (!args.valid_from) errors.valid_from = "Select the future responsibility start date.";
			if (!args.valid_to) errors.valid_to = "Select the future responsibility end date.";
			if (args.valid_from && args.valid_to && args.valid_to < args.valid_from) errors.valid_to = "Valid To cannot be earlier than Valid From.";
			const offering = this.selectedOffering;
			if (offering && args.valid_from && (args.valid_from < offering.period_start_date || args.valid_from > offering.period_end_date)) {
				errors.valid_from = "Valid From must fall inside the selected Class academic period.";
			}
			if (offering && args.valid_to && (args.valid_to < offering.period_start_date || args.valid_to > offering.period_end_date)) {
				errors.valid_to = "Valid To must fall inside the selected Class academic period.";
			}
			if (!args.reason) errors.reason = "Give a reason for the next-period preparation.";
			else if (args.reason.length < 3) errors.reason = "Give a short reason of at least 3 characters.";
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
			if (this.previewPlan) await this.confirmPreparation();
			else await this.previewPreparation();
		},
		async previewPreparation() {
			if (!this.validate()) return;
			this.previewError = "";
			this.setBusy(true, "Checking preparation...");
			const currentArgs = this.args();
			try {
				const response = await frappe.call({
					method: "eduedge.api.instructor_assignment_preparation.preview_instructor_assignment_preparation",
					type: "POST",
					args: currentArgs,
				});
				this.previewPlan = response.message || null;
				this.previewedArgs = this.previewPlan ? currentArgs : null;
				if (this.previewPlan?.already_prepared) {
					this.previewError = "This future responsibility has already been prepared from the source assignment. Refresh the register to review it instead of creating another copy.";
					this.previewPlan = null;
					this.previewedArgs = null;
				}
			} catch (error) {
				this.previewPlan = null;
				this.previewedArgs = null;
				this.previewError = serverErrorMessage(error, "Preparation preview failed.");
			} finally {
				this.setBusy(false);
			}
		},
		async confirmPreparation() {
			if (!this.previewPlan || !this.validate() || this.conflictCount) return;
			const currentArgs = this.args();
			if (!sameArgs(currentArgs, this.previewedArgs)) {
				this.invalidatePreview();
				this.previewError = "Preparation details changed after preview. Preview the current values again before confirming.";
				return;
			}

			let completed = false;
			this.setBusy(true, "Preparing future assignment...");
			try {
				const response = await frappe.call({
					method: "eduedge.api.instructor_assignment_preparation.prepare_instructor_assignment_for_next_period",
					type: "POST",
					args: currentArgs,
				});
				const result = response.message || {};
				frappe.show_alert({
					message: result.action === "already-prepared" ? "Future Instructor Assignment was already prepared" : "Future Instructor Assignment prepared",
					indicator: "green",
				});
				await this.onComplete?.(result);
				completed = true;
			} catch (error) {
				this.previewPlan = null;
				this.previewedArgs = null;
				this.previewError = serverErrorMessage(error, "Future Instructor Assignment could not be prepared.");
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
.eduedge-preparation-dialog { display: grid; gap: 1rem; color: var(--edge-color-ink-900, #172033); }
.eduedge-preparation-source,
.eduedge-preparation-preview { border: 1px solid var(--edge-color-border, #d8e2ee); border-radius: .85rem; display: grid; gap: .5rem; padding: 1rem; }
.eduedge-preparation-source { background: linear-gradient(180deg, var(--edge-color-surface-subtle, #f7f9fc), var(--edge-color-surface, #fff)); }
.eduedge-preparation-source__heading,
.eduedge-preparation-preview__heading { align-items: flex-start; display: flex; gap: .75rem; justify-content: space-between; }
.eduedge-preparation-source__heading > div,
.eduedge-preparation-preview__heading > div { display: grid; gap: .25rem; min-width: 0; }
.eduedge-preparation-kicker { font-size: .7rem; font-weight: 800; letter-spacing: .08em; margin: 0; text-transform: uppercase; }
.eduedge-preparation-source__title { font-size: .98rem; line-height: 1.45; }
.eduedge-preparation-fields { display: grid; gap: .9rem; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.eduedge-preparation-field { display: grid; gap: .4rem; min-width: 0; }
.eduedge-preparation-field--wide { grid-column: 1 / -1; }
.eduedge-preparation-label,
.eduedge-preparation-plan-label { color: var(--edge-color-ink-700, #334155); font-size: .78rem; font-weight: 750; }
.eduedge-preparation-label b { color: var(--red-500, #e24c4c); }
.eduedge-preparation-control { min-height: 2.45rem; }
.eduedge-preparation-help { color: var(--edge-color-ink-500, #64748b); font-size: .76rem; line-height: 1.45; }
.eduedge-preparation-warning { color: var(--orange-600, #b45309); font-size: .76rem; line-height: 1.45; }
.eduedge-preparation-error { color: var(--red-600, #dc2626); font-size: .78rem; line-height: 1.45; margin: 0; }
.eduedge-preparation-preview--ready { border-color: var(--green-300, #86d5a7); }
.eduedge-preparation-preview__heading h3 { font-size: 1rem; margin: 0; }
.eduedge-preparation-plan-grid { display: grid; gap: .75rem; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.eduedge-preparation-plan-grid__wide { grid-column: 1 / -1; }
.eduedge-preparation-plan-card { background: var(--edge-color-surface-subtle, #f7f9fc); border-radius: .7rem; display: grid; gap: .3rem; padding: .85rem; }
.eduedge-preparation-plan-card span { font-size: .84rem; line-height: 1.45; }
.eduedge-preparation-plan-card small { color: var(--edge-color-ink-500, #64748b); }
.eduedge-preparation-conflicts { background: var(--red-50, #fff5f5); border-radius: .7rem; color: var(--red-700, #b42318); display: grid; gap: .35rem; padding: .8rem; }
.eduedge-preparation-conflicts ul { margin: 0; padding-left: 1.1rem; }
.eduedge-preparation-button { min-width: 8rem; }
@media (max-width: 760px) {
	.eduedge-preparation-fields,
	.eduedge-preparation-plan-grid { grid-template-columns: 1fr; }
	.eduedge-preparation-field--wide,
	.eduedge-preparation-plan-grid__wide { grid-column: auto; }
	.eduedge-preparation-source__heading,
	.eduedge-preparation-preview__heading { align-items: stretch; flex-direction: column; }
}
</style>
