<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="selectedBranchLabel"
		branch-name="CBT Scheduling"
		:user-name="context.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-cbt-schedules"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Computer-Based Testing"
					title="CBT Schedules and Candidates"
					subtitle="Prepare examination sittings, confirm candidate eligibility, control check-in and release, and retain append-only intervention evidence."
					:action-label="canCreateSchedule ? 'Create Schedule' : null"
					@action="openScheduleDialog()"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading CBT schedules..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error"
				title="CBT schedules could not load"
				:message="error"
				action-label="Try again"
				@retry="loadContext"
			/>
			<template v-else>
				<EdgeFilterBar title="Schedule scope">
					<div class="eduedge-cbt-schedule-filters">
						<label>
							<span>Examination Scope</span>
							<select v-model="filters.exam_scope" class="form-control" @change="changeScope">
								<option value="School Examination">School Examination</option>
								<option v-if="context.can_manage_public" value="EduEdge Public Examination">EduEdge Public Examination</option>
							</select>
						</label>
						<label v-if="isSchoolScope">
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="changeBranch">
								<option v-for="branch in context.branch_options" :key="branch.value" :value="branch.value">
									{{ branch.label }}
								</option>
							</select>
						</label>
						<label>
							<span>Status</span>
							<select v-model="filters.status" class="form-control" @change="changeListFilter">
								<option value="">All statuses</option>
								<option v-for="status in scheduleStatuses" :key="status" :value="status">{{ status }}</option>
							</select>
						</label>
						<label>
							<span>Find schedule</span>
							<input v-model.trim="filters.search" class="form-control" placeholder="Title, code, template, or subject" @input="scheduleSearch" />
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" :disabled="working" @click="loadContext">Refresh</button>
						<button v-if="canCreateSchedule" type="button" class="edge-button edge-button--primary" @click="openScheduleDialog()">Create Schedule</button>
					</template>
				</EdgeFilterBar>

				<EdgeDashboardLayout min-column-width="10rem">
					<EdgeStatCard label="Schedules" :value="context.counts.schedules || 0" helper="Matching current scope" />
					<EdgeStatCard label="Ready" :value="context.counts.ready || 0" helper="Prepared for activation" />
					<EdgeStatCard label="Active" :value="context.counts.active || 0" helper="Current examination sittings" />
					<EdgeStatCard label="Candidates" :value="context.candidate_counts.total || 0" helper="Selected schedule" />
					<EdgeStatCard label="Checked In" :value="context.candidate_counts.checked_in || 0" helper="Selected schedule" />
					<EdgeStatCard label="Released" :value="context.candidate_counts.released || 0" helper="Selected schedule" />
				</EdgeDashboardLayout>

				<section class="eduedge-cbt-ops-panel">
					<div class="eduedge-cbt-ops-heading">
						<div>
							<p class="edge-eyebrow">Examination sittings</p>
							<h2>Schedules</h2>
							<p>Only records allowed by current role, Branch and public-examination authority are shown.</p>
						</div>
					</div>
					<EdgeEmptyState
						v-if="!context.schedules.length"
						title="No matching schedules"
						description="Create a schedule from an approved template and an active examination centre."
						:action-label="canCreateSchedule ? 'Create Schedule' : null"
						@action="openScheduleDialog()"
					/>
					<div v-else class="eduedge-cbt-table-wrap">
						<table class="table table-bordered eduedge-cbt-table">
							<thead>
								<tr><th>Schedule</th><th>Subject</th><th>Centre</th><th>Start</th><th>Status</th><th>Action</th></tr>
							</thead>
							<tbody>
								<tr v-for="schedule in context.schedules" :key="schedule.name" :class="{ 'is-selected': selectedScheduleName === schedule.name }">
									<td><strong>{{ schedule.schedule_title }}</strong><div class="text-muted">{{ schedule.schedule_code }} · {{ schedule.exam_template }}</div></td>
									<td>{{ schedule.course || 'Not set' }}</td>
									<td>{{ schedule.examination_centre || 'Not set' }}</td>
									<td>{{ dateTimeLabel(schedule.scheduled_start) }}</td>
									<td><EdgeStatusBadge :label="schedule.status" :status="schedule.status" :tone="statusTone(schedule.status)" /></td>
									<td><button type="button" class="edge-button" @click="selectSchedule(schedule.name)">Manage</button></td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>

				<section v-if="selectedSchedule" class="eduedge-cbt-ops-panel eduedge-cbt-selected-panel">
					<div class="eduedge-cbt-ops-heading">
						<div>
							<p class="edge-eyebrow">Selected schedule</p>
							<h2>{{ selectedSchedule.schedule_title }}</h2>
							<p>{{ selectedSchedule.schedule_code }} · {{ selectedSchedule.course }} · {{ dateTimeLabel(selectedSchedule.scheduled_start) }}</p>
						</div>
						<EdgeStatusBadge :label="selectedSchedule.status" :status="selectedSchedule.status" :tone="statusTone(selectedSchedule.status)" />
					</div>
					<div class="eduedge-cbt-action-row">
						<button v-if="canEditSelectedSchedule" type="button" class="edge-button" @click="openScheduleDialog(selectedSchedule)">Edit Schedule</button>
						<button type="button" class="edge-button" @click="openNativeSchedule">Open Full Record</button>
						<button
							v-for="action in scheduleActions"
							:key="action.status"
							type="button"
							class="edge-button"
							:class="{ 'edge-button--primary': action.primary }"
							:disabled="working"
							@click="confirmScheduleStatus(action.status)"
						>
							{{ action.label }}
						</button>
					</div>
					<div class="eduedge-cbt-detail-grid">
						<div><span>Template</span><strong>{{ selectedSchedule.exam_template }}</strong></div>
						<div><span>Centre</span><strong>{{ selectedSchedule.examination_centre }}</strong></div>
						<div><span>Duration</span><strong>{{ selectedSchedule.duration_minutes || 0 }} minutes</strong></div>
						<div><span>Scheduled End</span><strong>{{ dateTimeLabel(selectedSchedule.scheduled_end) }}</strong></div>
						<div><span>Candidate Start</span><strong>{{ selectedSchedule.candidate_start_mode }}</strong></div>
						<div><span>Primary Invigilator</span><strong>{{ selectedSchedule.primary_invigilator || 'Not assigned' }}</strong></div>
						<div><span>Student Group / Class</span><strong>{{ selectedSchedule.student_group || 'Manual assignment' }}</strong></div>
						<div><span>Navigation</span><strong>{{ selectedSchedule.navigation_policy || 'Not set' }}</strong></div>
						<div><span>Device Change</span><strong>{{ selectedSchedule.device_change_policy || 'Not set' }}</strong></div>
						<div><span>Attempt Review</span><strong>{{ selectedSchedule.attempt_review_policy || 'Not set' }}</strong></div>
					</div>
				</section>

				<section v-if="selectedSchedule" class="eduedge-cbt-ops-panel">
					<div class="eduedge-cbt-ops-heading">
						<div>
							<p class="edge-eyebrow">Eligibility and sitting control</p>
							<h2>Candidate Assignments</h2>
							<p>Candidate identity becomes immutable after eligibility is confirmed. Exceptions should be recorded as interventions.</p>
						</div>
						<div class="eduedge-cbt-heading-actions">
							<button v-if="canAssignCandidate" type="button" class="edge-button edge-button--primary" @click="openCandidateDialog()">Assign Candidate</button>
							<button v-if="canBulkAssign" type="button" class="edge-button" :disabled="working" @click="confirmBulkAssign">Assign Template Class</button>
						</div>
					</div>
					<EdgeEmptyState
						v-if="!context.candidates.length"
						title="No candidates assigned"
						description="Assign an eligible Student or use the template Student Group / Class."
						:action-label="canAssignCandidate ? 'Assign Candidate' : null"
						@action="openCandidateDialog()"
					/>
					<div v-else class="eduedge-cbt-table-wrap">
						<table class="table table-bordered eduedge-cbt-table">
							<thead><tr><th>Candidate</th><th>Eligibility</th><th>Access Window</th><th>Status</th><th>Actions</th></tr></thead>
							<tbody>
								<tr v-for="candidate in context.candidates" :key="candidate.name">
									<td><strong>{{ candidateLabel(candidate) }}</strong><div class="text-muted">{{ candidate.student || candidate.public_candidate_reference || candidate.name }}</div></td>
									<td>{{ candidate.eligibility_source || 'Manual' }}<div class="text-muted" v-if="candidate.approved_extra_time_minutes">+{{ candidate.approved_extra_time_minutes }} minutes</div></td>
									<td>{{ dateTimeLabel(candidate.access_start) }}<div class="text-muted">to {{ dateTimeLabel(candidate.access_end) }}</div></td>
									<td><EdgeStatusBadge :label="candidate.assignment_status" :status="candidate.assignment_status" :tone="statusTone(candidate.assignment_status)" /></td>
									<td>
										<div class="eduedge-cbt-row-actions">
											<button v-if="canEditCandidate(candidate)" type="button" class="edge-button" @click="openCandidateDialog(candidate)">Edit</button>
											<button
												v-for="action in candidateActions(candidate)"
												:key="action.status"
												type="button"
												class="edge-button"
												:disabled="working"
												@click="confirmCandidateStatus(candidate, action.status)"
											>
												{{ action.label }}
											</button>
											<button v-if="canRecordIntervention" type="button" class="edge-button" @click="openInterventionDialog(candidate)">Intervention</button>
										</div>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>

				<section v-if="selectedSchedule" class="eduedge-cbt-ops-panel">
					<div class="eduedge-cbt-ops-heading">
						<div>
							<p class="edge-eyebrow">Append-only audit</p>
							<h2>Intervention History</h2>
							<p>These entries document authorised exceptions. They do not edit candidate answers, marks or submitted academic records.</p>
						</div>
					</div>
					<EdgeEmptyState v-if="!context.interventions.length" title="No interventions recorded" description="Operational exceptions will appear here in newest-first order." />
					<div v-else class="eduedge-cbt-table-wrap">
						<table class="table table-bordered eduedge-cbt-table">
							<thead><tr><th>Candidate</th><th>Intervention</th><th>Reason</th><th>Outcome</th><th>Audit</th></tr></thead>
							<tbody>
								<tr v-for="item in context.interventions" :key="item.name">
									<td>{{ interventionCandidateLabel(item) }}</td>
									<td><strong>{{ item.intervention_type }}</strong><div v-if="item.additional_minutes" class="text-muted">{{ item.additional_minutes }} minutes</div></td>
									<td>{{ item.reason }}</td>
									<td><EdgeStatusBadge :label="item.outcome" :status="item.outcome" :tone="item.outcome === 'Applied' ? 'success' : 'danger'" /></td>
									<td>{{ item.acted_by }}<div class="text-muted">{{ dateTimeLabel(item.acted_on) }}</div></td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>

	<EdgeFormDialog
		:open="scheduleModal.open"
		:title="scheduleModal.title"
		:subtitle="scheduleModal.subtitle"
		:fields="scheduleModal.fields"
		:model-value="scheduleModal.values"
		:field-errors="scheduleModal.fieldErrors"
		:error="scheduleModal.error"
		:loading="scheduleModal.loading"
		:busy="scheduleModal.busy"
		:submit-label="scheduleModal.submitLabel"
		@update:model-value="updateScheduleValues"
		@field-change="onScheduleFieldChange"
		@search-options="searchScheduleOptions"
		@submit="saveSchedule"
		@close="closeScheduleModal"
	/>

	<EdgeFormDialog
		:open="candidateModal.open"
		:title="candidateModal.title"
		:subtitle="candidateModal.subtitle"
		:fields="candidateModal.fields"
		:model-value="candidateModal.values"
		:field-errors="candidateModal.fieldErrors"
		:error="candidateModal.error"
		:loading="candidateModal.loading"
		:busy="candidateModal.busy"
		:submit-label="candidateModal.submitLabel"
		@update:model-value="updateCandidateValues"
		@field-change="onCandidateFieldChange"
		@search-options="searchCandidateOptions"
		@submit="saveCandidate"
		@close="closeCandidateModal"
	/>

	<EdgeFormDialog
		:open="interventionModal.open"
		:title="interventionModal.title"
		:subtitle="interventionModal.subtitle"
		:fields="interventionModal.fields"
		:model-value="interventionModal.values"
		:field-errors="interventionModal.fieldErrors"
		:error="interventionModal.error"
		:loading="false"
		:busy="interventionModal.busy"
		submit-label="Record Intervention"
		@update:model-value="updateInterventionValues"
		@field-change="onInterventionFieldChange"
		@submit="recordIntervention"
		@close="closeInterventionModal"
	/>

	<EdgeModal
		:open="confirmDialog.open"
		:title="confirmDialog.title"
		:subtitle="confirmDialog.message"
		size="sm"
		:busy="confirmDialog.busy"
		@close="closeConfirm"
	>
		<p>{{ confirmDialog.detail }}</p>
		<template #footer>
			<span class="edge-modal__footer-spacer"></span>
			<button type="button" class="edge-button" :disabled="confirmDialog.busy" @click="closeConfirm">Cancel</button>
			<button type="button" class="edge-button edge-button--primary" :disabled="confirmDialog.busy" @click="executeConfirmedAction">
				{{ confirmDialog.busy ? 'Working…' : confirmDialog.confirmLabel }}
			</button>
		</template>
	</EdgeModal>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const API = "eduedge.api.cbt_schedule_operations";
const SCHEDULE_STATUSES = ["Draft", "Ready", "Active", "Suspended", "Completed", "Cancelled"];

function emptyDialog() {
	return {
		open: false,
		loading: false,
		busy: false,
		error: "",
		fieldErrors: {},
		name: "",
		title: "",
		subtitle: "",
		submitLabel: "Save",
		fields: [],
		values: {},
		searchTokens: {},
	};
}

function emptyConfirm() {
	return { open: false, busy: false, kind: "", title: "", message: "", detail: "", confirmLabel: "Continue", record: null, status: "" };
}

export default {
	name: "EduEdgeCBTSchedules",
	data() {
		return {
			loading: true,
			working: false,
			error: "",
			searchTimer: null,
			menuItems: EDUEDGE_MENU_ITEMS,
			filters: { exam_scope: "School Examination", branch: "", status: "", search: "" },
			selectedScheduleName: "",
			context: {
				branch_options: [],
				schedules: [],
				selected_schedule: null,
				candidates: [],
				interventions: [],
				counts: {},
				candidate_counts: {},
				permissions: { schedule: {}, candidate: {}, intervention: {} },
				can_manage_public: false,
				user: {},
			},
			scheduleModal: emptyDialog(),
			candidateModal: emptyDialog(),
			interventionModal: emptyDialog(),
			confirmDialog: emptyConfirm(),
		};
	},
	computed: {
		scheduleStatuses() { return SCHEDULE_STATUSES; },
		isSchoolScope() { return this.filters.exam_scope === "School Examination"; },
		selectedSchedule() { return this.context.selected_schedule || null; },
		selectedBranchLabel() {
			return this.context.branch_options.find((row) => row.value === this.filters.branch)?.label || this.filters.branch || "";
		},
		canCreateSchedule() { return Boolean(this.context.permissions?.schedule?.create); },
		canWriteSchedule() { return Boolean(this.context.permissions?.schedule?.write); },
		canCreateCandidate() { return Boolean(this.context.permissions?.candidate?.create); },
		canWriteCandidate() { return Boolean(this.context.permissions?.candidate?.write); },
		canRecordIntervention() { return Boolean(this.context.permissions?.intervention?.create); },
		canEditSelectedSchedule() {
			return this.canWriteSchedule && ["Draft", "Ready"].includes(this.selectedSchedule?.status);
		},
		canAssignCandidate() {
			return this.canCreateCandidate && ["Draft", "Ready"].includes(this.selectedSchedule?.status);
		},
		canBulkAssign() {
			return this.canAssignCandidate && this.isSchoolScope && Boolean(this.selectedSchedule?.student_group);
		},
		scheduleActions() {
			if (!this.canWriteSchedule || !this.selectedSchedule) return [];
			const status = this.selectedSchedule.status;
			const map = {
				Draft: [{ status: "Ready", label: "Mark Ready", primary: true }, { status: "Cancelled", label: "Cancel" }],
				Ready: [{ status: "Draft", label: "Return to Draft" }, { status: "Active", label: "Activate", primary: true }, { status: "Cancelled", label: "Cancel" }],
				Active: [{ status: "Suspended", label: "Suspend" }, { status: "Completed", label: "Complete", primary: true }, { status: "Cancelled", label: "Cancel" }],
				Suspended: [{ status: "Active", label: "Resume", primary: true }, { status: "Completed", label: "Complete" }, { status: "Cancelled", label: "Cancel" }],
			};
			return map[status] || [];
		},
	},
	mounted() { this.loadContext(); },
	beforeUnmount() { if (this.searchTimer) window.clearTimeout(this.searchTimer); },
	methods: {
		openRoute: openEduEdgeRoute,
		truthy(value) { return value === true || value === 1 || value === "1" || String(value).toLowerCase() === "yes"; },
		dateTimeLabel(value) {
			if (!value) return "Not set";
			try { return frappe.datetime.str_to_user(value); } catch (_error) { return String(value); }
		},
		toInputDateTime(value) {
			if (!value) return "";
			return String(value).replace(" ", "T").slice(0, 16);
		},
		candidateLabel(candidate) { return candidate.candidate_name || candidate.student_name || candidate.student || candidate.public_candidate_reference || candidate.name; },
		interventionCandidateLabel(item) {
			const candidate = this.context.candidates.find((row) => row.name === item.candidate_assignment);
			return candidate ? this.candidateLabel(candidate) : item.student || item.public_candidate_reference || item.candidate_assignment;
		},
		statusTone(status) {
			if (["Ready", "Eligible", "Checked In"].includes(status)) return "warning";
			if (["Active", "Released", "Completed", "Applied"].includes(status)) return "success";
			if (["Cancelled", "Withdrawn", "Disqualified", "Rejected"].includes(status)) return "danger";
			return "neutral";
		},
		async loadContext() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call(`${API}.get_context`, {
					exam_scope: this.filters.exam_scope,
					branch: this.filters.branch || undefined,
					status: this.filters.status || undefined,
					search: this.filters.search || undefined,
					schedule: this.selectedScheduleName || undefined,
				});
				const state = response.message || {};
				this.context = { ...this.context, ...state };
				this.filters.exam_scope = state.exam_scope || this.filters.exam_scope;
				this.filters.branch = state.branch || "";
				this.selectedScheduleName = state.selected_schedule?.name || "";
			} catch (error) {
				this.error = error?.message || "CBT schedules could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		changeScope() { this.filters.branch = ""; this.filters.status = ""; this.filters.search = ""; this.selectedScheduleName = ""; return this.loadContext(); },
		changeBranch() { this.filters.status = ""; this.filters.search = ""; this.selectedScheduleName = ""; return this.loadContext(); },
		changeListFilter() { this.selectedScheduleName = ""; return this.loadContext(); },
		scheduleSearch() {
			if (this.searchTimer) window.clearTimeout(this.searchTimer);
			this.searchTimer = window.setTimeout(() => { this.selectedScheduleName = ""; this.loadContext(); }, 300);
		},
		selectSchedule(name) { this.selectedScheduleName = name; return this.loadContext(); },
		openNativeSchedule() { if (this.selectedSchedule) this.openRoute(`/app/eduedge-cbt-exam-schedule/${this.selectedSchedule.name}`); },

		scheduleFields() {
			return [
				{ fieldname: "schedule_title", type: "Data", label: "Schedule Title", required: true },
				{ fieldname: "schedule_code", type: "Data", label: "Schedule Code", required: true },
				{ fieldname: "exam_scope", type: "Select", label: "Examination Scope", options: ["School Examination", "EduEdge Public Examination"], read_only: true },
				{ fieldname: "school_branch", type: "Link", label: "Branch / Campus", required: this.isSchoolScope, options: this.context.branch_options, read_only: this.isSchoolScope },
				{ fieldname: "exam_template", type: "Link", label: "Approved Exam Template", required: true, options: [] },
				{ fieldname: "course", type: "Link", label: "Subject / Course", required: true, options: [] },
				{ fieldname: "examination_centre", type: "Link", label: "Examination Centre", required: true, options: [] },
				{ fieldname: "scheduled_start", type: "Datetime", label: "Scheduled Start", required: true },
				{ fieldname: "check_in_opens_at", type: "Datetime", label: "Check-in Opens At" },
				{ fieldname: "require_candidate_check_in", type: "Check", label: "Require Candidate Check-in", default: 1 },
				{ fieldname: "candidate_start_mode", type: "Select", label: "Candidate Start Mode", required: true, options: ["Candidate Starts After Check-in", "Invigilator Releases Candidates", "Automatic Start at Scheduled Time"] },
				{ fieldname: "allow_late_entry", type: "Check", label: "Allow Late Entry", default: 0 },
				{ fieldname: "late_entry_grace_minutes", type: "Int", label: "Late Entry Grace (Minutes)", visible_when: { field: "allow_late_entry", truthy: true } },
				{ fieldname: "primary_invigilator", type: "Link", label: "Primary Invigilator", options: [] },
				{ fieldname: "allow_invigilator_time_extension", type: "Check", label: "Allow Invigilator Time Extension", default: 0 },
				{ fieldname: "maximum_time_extension_minutes", type: "Int", label: "Maximum Time Extension (Minutes)", visible_when: { field: "allow_invigilator_time_extension", truthy: true } },
				{ fieldname: "allow_invigilator_force_submit", type: "Check", label: "Allow Authorised Force Submission", default: 1 },
				{ fieldname: "duration_minutes", type: "Int", label: "Template Duration (Minutes)", read_only: true },
				{ fieldname: "maximum_attempts", type: "Int", label: "Maximum Attempts", read_only: true },
				{ fieldname: "pass_percentage", type: "Float", label: "Pass Percentage", read_only: true },
				{ fieldname: "navigation_policy", type: "Data", label: "Question Navigation", read_only: true },
				{ fieldname: "device_change_policy", type: "Data", label: "Device Change Policy", read_only: true },
				{ fieldname: "attempt_review_policy", type: "Data", label: "Attempt Review Policy", read_only: true },
				{ fieldname: "notes", type: "Small Text", label: "Internal Notes" },
			];
		},
		async openScheduleDialog(schedule = null) {
			const defaults = {
				schedule_title: "",
				schedule_code: "",
				exam_scope: this.filters.exam_scope,
				school_branch: this.filters.branch || "",
				exam_template: "",
				course: "",
				examination_centre: "",
				scheduled_start: "",
				check_in_opens_at: "",
				require_candidate_check_in: 1,
				candidate_start_mode: "Candidate Starts After Check-in",
				allow_late_entry: 0,
				late_entry_grace_minutes: 0,
				primary_invigilator: "",
				allow_invigilator_time_extension: 0,
				maximum_time_extension_minutes: 0,
				allow_invigilator_force_submit: 1,
				duration_minutes: 0,
				maximum_attempts: 1,
				pass_percentage: 0,
				navigation_policy: "",
				device_change_policy: "",
				attempt_review_policy: "",
				notes: "",
			};
			this.scheduleModal = {
				...emptyDialog(),
				open: true,
				loading: Boolean(schedule),
				name: schedule?.name || "",
				title: schedule ? "Update CBT Schedule" : "Create CBT Schedule",
				subtitle: "Template, Branch, Centre, timing and sitting policies remain server-validated. Activated schedules are immutable.",
				submitLabel: schedule ? "Save Changes" : "Create Schedule",
				fields: this.scheduleFields(),
				values: defaults,
			};
			if (!schedule) return;
			try {
				const response = await frappe.call(`${API}.get_schedule`, { name: schedule.name });
				const values = response.message?.values || {};
				this.scheduleModal.values = {
					...defaults,
					...values,
					scheduled_start: this.toInputDateTime(values.scheduled_start),
					check_in_opens_at: this.toInputDateTime(values.check_in_opens_at),
				};
				if (!response.message?.can_write) this.scheduleModal.error = "You may view this schedule but cannot update it.";
			} catch (error) {
				this.scheduleModal.error = error?.message || "The schedule could not be loaded.";
			} finally {
				this.scheduleModal.loading = false;
			}
		},
		updateScheduleValues(values) { this.scheduleModal.values = { ...(values || {}) }; this.scheduleModal.fieldErrors = {}; this.scheduleModal.error = ""; },
		async onScheduleFieldChange({ field, values } = {}) {
			this.scheduleModal.values = { ...(values || this.scheduleModal.values || {}) };
			this.scheduleModal.fieldErrors = { ...(this.scheduleModal.fieldErrors || {}), [field?.fieldname]: "" };
			this.scheduleModal.error = "";
			if (field?.fieldname === "exam_template" && this.scheduleModal.values.exam_template) {
				try {
					const response = await frappe.call(`${API}.get_template_context`, {
						template: this.scheduleModal.values.exam_template,
						school_branch: this.scheduleModal.values.school_branch || this.filters.branch || undefined,
					});
					const state = response.message || {};
					this.scheduleModal.values = {
						...this.scheduleModal.values,
						exam_scope: state.exam_scope || this.scheduleModal.values.exam_scope,
						school_branch: state.school_branch || this.scheduleModal.values.school_branch,
						course: state.course || "",
						examination_centre: state.default_examination_centre || "",
						...(state.snapshot || {}),
					};
				} catch (error) {
					this.scheduleModal.error = error?.message || "The template context could not be resolved.";
				}
			}
			if (field?.fieldname === "allow_late_entry" && !this.truthy(this.scheduleModal.values.allow_late_entry)) this.scheduleModal.values.late_entry_grace_minutes = 0;
			if (field?.fieldname === "allow_invigilator_time_extension" && !this.truthy(this.scheduleModal.values.allow_invigilator_time_extension)) this.scheduleModal.values.maximum_time_extension_minutes = 0;
		},
		async searchScheduleOptions(payload) { return this.searchDialogOptions("scheduleModal", payload); },
		async saveSchedule() {
			if (this.scheduleModal.busy) return;
			const required = ["schedule_title", "schedule_code", "exam_template", "course", "examination_centre", "scheduled_start"];
			const errors = {};
			for (const fieldname of required) if (!String(this.scheduleModal.values?.[fieldname] || "").trim()) errors[fieldname] = "This field is required.";
			if (this.isSchoolScope && !this.scheduleModal.values.school_branch) errors.school_branch = "This field is required.";
			this.scheduleModal.fieldErrors = errors;
			if (Object.keys(errors).length) return;
			this.scheduleModal.busy = true;
			try {
				const values = { ...this.scheduleModal.values, page_branch: this.filters.branch || "" };
				const response = await frappe.call(`${API}.save_schedule`, { name: this.scheduleModal.name || undefined, values: JSON.stringify(values) });
				this.selectedScheduleName = response.message?.name || this.scheduleModal.name;
				this.closeScheduleModal(true);
				await this.loadContext();
				frappe.show_alert({ message: __("CBT schedule saved."), indicator: "green" }, 5);
			} catch (error) {
				this.scheduleModal.error = error?.message || "The schedule could not be saved.";
			} finally {
				this.scheduleModal.busy = false;
			}
		},
		closeScheduleModal(force = false) { if (this.scheduleModal.busy && !force) return; this.scheduleModal = emptyDialog(); },

		candidateFields() {
			const isPublic = this.selectedSchedule?.exam_scope === "EduEdge Public Examination";
			return [
				{ fieldname: "exam_schedule", type: "Data", label: "Examination Schedule", required: true, read_only: true },
				{ fieldname: "student", type: "Link", label: "Student", required: !isPublic, options: [], visible_when: { field: "candidate_type", equals: "EduEdge Student" } },
				{ fieldname: "public_candidate_reference", type: "Data", label: "Public Candidate Reference", required: isPublic, visible_when: { field: "candidate_type", equals: "Public Candidate Reference" } },
				{ fieldname: "candidate_name", type: "Data", label: "Candidate Name", required: isPublic, visible_when: { field: "candidate_type", equals: "Public Candidate Reference" } },
				{ fieldname: "candidate_type", type: "Data", label: "Candidate Type", read_only: true },
				{ fieldname: "assignment_status", type: "Select", label: "Initial Status", options: ["Draft", "Eligible"], read_only: Boolean(this.candidateModal.name) },
				{ fieldname: "approved_extra_time_minutes", type: "Int", label: "Approved Extra Time (Minutes)" },
				{ fieldname: "notes", type: "Small Text", label: "Internal Notes" },
			];
		},
		async openCandidateDialog(candidate = null) {
			if (!this.selectedSchedule) return;
			const candidateType = this.selectedSchedule.exam_scope === "EduEdge Public Examination" ? "Public Candidate Reference" : "EduEdge Student";
			const defaults = {
				exam_schedule: this.selectedSchedule.name,
				candidate_type: candidateType,
				student: "",
				public_candidate_reference: "",
				candidate_name: "",
				assignment_status: "Eligible",
				approved_extra_time_minutes: 0,
				notes: "",
			};
			this.candidateModal = {
				...emptyDialog(),
				open: true,
				loading: Boolean(candidate),
				name: candidate?.name || "",
				title: candidate ? "Update Candidate Assignment" : "Assign Candidate",
				subtitle: "Student eligibility, Branch membership, duplicate prevention and access windows are enforced by the server.",
				submitLabel: candidate ? "Save Changes" : "Assign Candidate",
				fields: [],
				values: defaults,
			};
			this.candidateModal.fields = this.candidateFields();
			if (!candidate) return;
			try {
				const response = await frappe.call(`${API}.get_candidate`, { name: candidate.name });
				this.candidateModal.values = { ...defaults, ...(response.message?.values || {}) };
				if (!response.message?.can_write) this.candidateModal.error = "You may view this assignment but cannot update it.";
			} catch (error) {
				this.candidateModal.error = error?.message || "The candidate assignment could not be loaded.";
			} finally {
				this.candidateModal.loading = false;
			}
		},
		updateCandidateValues(values) { this.candidateModal.values = { ...(values || {}) }; this.candidateModal.fieldErrors = {}; this.candidateModal.error = ""; },
		onCandidateFieldChange({ field, values } = {}) { this.candidateModal.values = { ...(values || this.candidateModal.values || {}) }; this.candidateModal.fieldErrors = { ...(this.candidateModal.fieldErrors || {}), [field?.fieldname]: "" }; this.candidateModal.error = ""; },
		async searchCandidateOptions(payload) { return this.searchDialogOptions("candidateModal", payload); },
		async saveCandidate() {
			if (this.candidateModal.busy) return;
			const values = this.candidateModal.values || {};
			const errors = {};
			if (values.candidate_type === "EduEdge Student" && !values.student) errors.student = "This field is required.";
			if (values.candidate_type === "Public Candidate Reference") {
				if (!values.public_candidate_reference) errors.public_candidate_reference = "This field is required.";
				if (!values.candidate_name) errors.candidate_name = "This field is required.";
			}
			this.candidateModal.fieldErrors = errors;
			if (Object.keys(errors).length) return;
			this.candidateModal.busy = true;
			try {
				await frappe.call(`${API}.save_candidate`, { name: this.candidateModal.name || undefined, values: JSON.stringify(values) });
				this.closeCandidateModal(true);
				await this.loadContext();
				frappe.show_alert({ message: __("Candidate assignment saved."), indicator: "green" }, 5);
			} catch (error) {
				this.candidateModal.error = error?.message || "The candidate assignment could not be saved.";
			} finally {
				this.candidateModal.busy = false;
			}
		},
		closeCandidateModal(force = false) { if (this.candidateModal.busy && !force) return; this.candidateModal = emptyDialog(); },
		canEditCandidate(candidate) { return this.canWriteCandidate && candidate.assignment_status === "Draft"; },
		candidateActions(candidate) {
			if (!this.canWriteCandidate) return [];
			const map = {
				Draft: [{ status: "Eligible", label: "Confirm Eligible" }, { status: "Withdrawn", label: "Withdraw" }],
				Eligible: [{ status: "Checked In", label: "Check In" }, { status: "Withdrawn", label: "Withdraw" }, { status: "Disqualified", label: "Disqualify" }],
				"Checked In": [{ status: "Released", label: "Release" }, { status: "Withdrawn", label: "Withdraw" }, { status: "Disqualified", label: "Disqualify" }],
				Released: [{ status: "Completed", label: "Complete" }, { status: "Disqualified", label: "Disqualify" }],
			};
			return map[candidate.assignment_status] || [];
		},

		openInterventionDialog(candidate) {
			this.interventionModal = {
				...emptyDialog(),
				open: true,
				title: "Record CBT Intervention",
				subtitle: "The entry is append-only, requires a reason, and will be flagged for attempt review.",
				fields: [
					{ fieldname: "candidate_label", type: "Data", label: "Candidate", read_only: true },
					{ fieldname: "intervention_type", type: "Select", label: "Intervention Type", required: true, options: ["Device Change", "Time Extension", "Force Submission", "Attempt Unlock", "Attempt Suspension", "Reconnection Approval", "Manual Sync Resolution", "Candidate Reassignment", "Other"] },
					{ fieldname: "reason", type: "Small Text", label: "Reason", required: true },
					{ fieldname: "additional_minutes", type: "Int", label: "Additional Minutes", visible_when: { field: "intervention_type", equals: "Time Extension" } },
					{ fieldname: "previous_value", type: "Small Text", label: "Previous Value / State" },
					{ fieldname: "new_value", type: "Small Text", label: "New Value / State" },
					{ fieldname: "attempt_reference", type: "Data", label: "Attempt Reference" },
					{ fieldname: "outcome", type: "Select", label: "Outcome", required: true, options: ["Applied", "Rejected"] },
				],
				values: {
					candidate_assignment: candidate.name,
					candidate_label: this.candidateLabel(candidate),
					intervention_type: "",
					reason: "",
					additional_minutes: 0,
					previous_value: "",
					new_value: "",
					attempt_reference: "",
					outcome: "Applied",
				},
			};
		},
		updateInterventionValues(values) { this.interventionModal.values = { ...(values || {}) }; this.interventionModal.fieldErrors = {}; this.interventionModal.error = ""; },
		onInterventionFieldChange({ field, values } = {}) {
			this.interventionModal.values = { ...(values || this.interventionModal.values || {}) };
			this.interventionModal.fieldErrors = { ...(this.interventionModal.fieldErrors || {}), [field?.fieldname]: "" };
			this.interventionModal.error = "";
			if (field?.fieldname === "intervention_type" && this.interventionModal.values.intervention_type !== "Time Extension") this.interventionModal.values.additional_minutes = 0;
		},
		async recordIntervention() {
			if (this.interventionModal.busy) return;
			const values = this.interventionModal.values || {};
			const errors = {};
			if (!values.intervention_type) errors.intervention_type = "This field is required.";
			if (!String(values.reason || "").trim()) errors.reason = "This field is required.";
			if (values.intervention_type === "Time Extension" && Number(values.additional_minutes || 0) <= 0) errors.additional_minutes = "Enter additional minutes greater than zero.";
			this.interventionModal.fieldErrors = errors;
			if (Object.keys(errors).length) return;
			this.interventionModal.busy = true;
			try {
				await frappe.call(`${API}.record_intervention`, { values: JSON.stringify(values) });
				this.closeInterventionModal(true);
				await this.loadContext();
				frappe.show_alert({ message: __("CBT intervention recorded."), indicator: "green" }, 5);
			} catch (error) {
				this.interventionModal.error = error?.message || "The intervention could not be recorded.";
			} finally {
				this.interventionModal.busy = false;
			}
		},
		closeInterventionModal(force = false) { if (this.interventionModal.busy && !force) return; this.interventionModal = emptyDialog(); },

		async searchDialogOptions(dialogName, { field, query = "", values = {} } = {}) {
			const dialog = this[dialogName];
			if (!field?.fieldname || !dialog?.open) return;
			const fieldname = field.fieldname;
			const token = `${Date.now()}-${Math.random()}`;
			dialog.searchTokens = { ...(dialog.searchTokens || {}), [fieldname]: token };
			dialog.fields = dialog.fields.map((item) => item.fieldname === fieldname ? { ...item, options_loading: true } : item);
			try {
				const payload = { ...(values || dialog.values || {}), page_branch: this.filters.branch || "", exam_scope: values.exam_scope || this.filters.exam_scope };
				const response = await frappe.call(`${API}.search_options`, { fieldname, txt: query || "", values: JSON.stringify(payload) });
				if (dialog.searchTokens?.[fieldname] !== token) return;
				dialog.fields = dialog.fields.map((item) => item.fieldname === fieldname ? { ...item, options: response.message || [], options_loading: false } : item);
			} catch (error) {
				if (dialog.searchTokens?.[fieldname] !== token) return;
				dialog.fields = dialog.fields.map((item) => item.fieldname === fieldname ? { ...item, options_loading: false } : item);
				dialog.error = error?.message || `Options for ${field.label || fieldname} could not be loaded.`;
			}
		},

		confirmScheduleStatus(status) {
			this.confirmDialog = {
				...emptyConfirm(), open: true, kind: "schedule-status", record: this.selectedSchedule, status,
				title: `${status} CBT Schedule`, message: `${this.selectedSchedule.schedule_title} will move from ${this.selectedSchedule.status} to ${status}.`,
				detail: status === "Active" ? "Activation locks the template, timing, centre and policy snapshot." : "The server will enforce the permitted lifecycle transition.",
				confirmLabel: status,
			};
		},
		confirmCandidateStatus(candidate, status) {
			this.confirmDialog = {
				...emptyConfirm(), open: true, kind: "candidate-status", record: candidate, status,
				title: `${status} Candidate`, message: `${this.candidateLabel(candidate)} will move from ${candidate.assignment_status} to ${status}.`,
				detail: "Candidate identity and schedule eligibility remain server-authoritative.", confirmLabel: status,
			};
		},
		confirmBulkAssign() {
			this.confirmDialog = {
				...emptyConfirm(), open: true, kind: "bulk-assign", record: this.selectedSchedule,
				title: "Assign Template Class", message: `Assign active members of ${this.selectedSchedule.student_group} to ${this.selectedSchedule.schedule_title}.`,
				detail: "Existing candidate assignments will be skipped. New assignments will be created as Eligible.", confirmLabel: "Assign Class",
			};
		},
		closeConfirm() { if (this.confirmDialog.busy) return; this.confirmDialog = emptyConfirm(); },
		async executeConfirmedAction() {
			if (!this.confirmDialog.open || this.confirmDialog.busy) return;
			this.confirmDialog.busy = true;
			this.working = true;
			try {
				if (this.confirmDialog.kind === "schedule-status") {
					await frappe.call(`${API}.set_schedule_status`, { name: this.confirmDialog.record.name, status: this.confirmDialog.status });
				} else if (this.confirmDialog.kind === "candidate-status") {
					await frappe.call(`${API}.set_candidate_status`, { name: this.confirmDialog.record.name, status: this.confirmDialog.status });
				} else if (this.confirmDialog.kind === "bulk-assign") {
					const response = await frappe.call(`${API}.assign_template_student_group`, { schedule: this.confirmDialog.record.name });
					const result = response.message || {};
					frappe.show_alert({ message: __(`${(result.created || []).length} candidates assigned; ${(result.skipped || []).length} skipped.`), indicator: "green" }, 7);
				}
				this.confirmDialog = emptyConfirm();
				await this.loadContext();
			} catch (error) {
				this.confirmDialog.message = error?.message || "The requested action could not be completed.";
				this.confirmDialog.busy = false;
			} finally {
				this.working = false;
			}
		},
	},
};
</script>

<style scoped>
.eduedge-cbt-schedule-filters {
	display: grid;
	gap: .8rem;
	grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
	width: 100%;
}
.eduedge-cbt-schedule-filters label { display: grid; gap: .35rem; }
.eduedge-cbt-schedule-filters span { color: var(--edge-color-ink-600, #526579); font-size: .75rem; font-weight: 600; }
.eduedge-cbt-ops-panel {
	background: var(--edge-color-surface, #fff);
	border: 1px solid var(--edge-color-border, #dce5ef);
	border-radius: 1rem;
	margin-top: 1rem;
	padding: 1rem;
}
.eduedge-cbt-selected-panel { border-color: var(--edge-color-brand-300, #9cc5e7); }
.eduedge-cbt-ops-heading {
	align-items: flex-start;
	display: flex;
	gap: 1rem;
	justify-content: space-between;
	margin-bottom: 1rem;
}
.eduedge-cbt-ops-heading h2 { margin: .15rem 0 .3rem; }
.eduedge-cbt-ops-heading p { margin: 0; }
.eduedge-cbt-heading-actions,
.eduedge-cbt-action-row,
.eduedge-cbt-row-actions { display: flex; flex-wrap: wrap; gap: .45rem; }
.eduedge-cbt-action-row { border-top: 1px solid var(--edge-color-border, #dce5ef); padding-top: .85rem; }
.eduedge-cbt-table-wrap { overflow-x: auto; }
.eduedge-cbt-table { margin-bottom: 0; min-width: 56rem; }
.eduedge-cbt-table tr.is-selected td { background: var(--edge-color-surface-subtle, #f4f8fb); }
.eduedge-cbt-table td { vertical-align: middle; }
.eduedge-cbt-detail-grid {
	display: grid;
	gap: .7rem;
	grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
	margin-top: 1rem;
}
.eduedge-cbt-detail-grid > div {
	background: var(--edge-color-surface-subtle, #f4f8fb);
	border-radius: .65rem;
	display: grid;
	gap: .2rem;
	padding: .75rem;
}
.eduedge-cbt-detail-grid span { color: var(--edge-color-ink-500, #6b7d90); font-size: .72rem; }
.eduedge-cbt-detail-grid strong { overflow-wrap: anywhere; }
@media (max-width: 47.99rem) {
	.eduedge-cbt-ops-heading { align-items: stretch; flex-direction: column; }
	.eduedge-cbt-heading-actions { width: 100%; }
	.eduedge-cbt-heading-actions .edge-button { flex: 1; }
}
</style>
