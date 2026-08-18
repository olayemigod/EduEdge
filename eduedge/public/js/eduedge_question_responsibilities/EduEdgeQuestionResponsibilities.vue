<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="selectedInstitutionLabel"
		branch-name="Question Governance"
		:user-name="context.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-question-responsibilities"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="CBT Governance"
					title="Question Responsibilities"
					subtitle="Assign scoped authoring, subject-review, and final-approval authority without granting all-school access through a role alone."
					:action-label="context.permissions?.can_create && context.institution ? 'Add Responsibility' : null"
					@action="openAssignmentDialog()"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading Question Responsibilities..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error"
				title="Question Responsibilities could not load"
				:message="error"
				action-label="Try again"
				@retry="loadContext"
			/>
			<template v-else>
				<EdgeFilterBar title="Responsibility scope">
					<div class="eduedge-responsibility-filters">
						<label>
							<span>Institution</span>
							<select v-model="selectedInstitution" class="form-control" @change="changeInstitution">
								<option v-for="option in context.institution_options" :key="option.value" :value="option.value">
									{{ option.label }}
								</option>
							</select>
						</label>
						<label>
							<span>Find assignment</span>
							<input
								v-model.trim="searchText"
								class="form-control"
								placeholder="User, subject, or branch"
								@input="scheduleSearch"
							/>
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" :disabled="working" @click="loadContext">Refresh</button>
						<button
							v-if="context.permissions?.can_create && context.institution"
							type="button"
							class="edge-button edge-button--primary"
							@click="openAssignmentDialog()"
						>
							Add Responsibility
						</button>
					</template>
				</EdgeFilterBar>

				<EdgeDashboardLayout min-column-width="10rem">
					<EdgeStatCard label="Assignments" :value="context.counts.total || 0" helper="Saved within the selected Institution" />
					<EdgeStatCard label="Active" :value="context.counts.active || 0" helper="Enabled and currently valid" />
					<EdgeStatCard label="Authors" :value="context.counts.authors || 0" helper="May author questions in scope" />
					<EdgeStatCard label="Subject Reviewers" :value="context.counts.subject_reviewers || 0" helper="Standard workflow recommendation" />
					<EdgeStatCard label="Final Approvers" :value="context.counts.final_approvers || 0" helper="Final approval responsibility" />
				</EdgeDashboardLayout>

				<section class="eduedge-responsibility-panel eduedge-policy-panel">
					<div>
						<p class="edge-eyebrow">Effective Institution policy</p>
						<h2>{{ context.effective_policy?.question_approval_mode || 'Not resolved' }} approval</h2>
						<p>{{ policySummary }}</p>
					</div>
					<EdgeStatusBadge
						:label="context.effective_policy?.source || 'No policy'"
						:status="context.effective_policy?.source || 'No policy'"
						:tone="context.effective_policy ? 'success' : 'warning'"
					/>
				</section>

				<section class="eduedge-responsibility-panel">
					<div class="eduedge-responsibility-heading">
						<div>
							<p class="edge-eyebrow">Scoped authority</p>
							<h2>Subject responsibility assignments</h2>
							<p>Institution-wide assignments cover every permitted Branch. A Branch-specific assignment is narrower.</p>
						</div>
					</div>

					<EdgeEmptyState
						v-if="!context.assignments.length"
						title="No matching responsibilities"
						description="Assign a user to a Subject / Course before Standard subject review or scoped final approval is activated."
						:action-label="context.permissions?.can_create ? 'Add Responsibility' : null"
						@action="openAssignmentDialog()"
					/>

					<div v-else class="eduedge-responsibility-table-wrap">
						<table class="table table-bordered eduedge-responsibility-table">
							<thead>
								<tr><th>User</th><th>Subject / Course</th><th>Scope</th><th>Responsibilities</th><th>Validity</th><th>Status</th><th>Action</th></tr>
							</thead>
							<tbody>
								<tr v-for="assignment in context.assignments" :key="assignment.name">
									<td><strong>{{ assignment.user_full_name || assignment.user }}</strong><div class="text-muted">{{ assignment.user }}</div></td>
									<td><strong>{{ assignment.course_label || assignment.course }}</strong></td>
									<td><strong>{{ assignment.branch_label }}</strong><div class="text-muted">{{ selectedInstitutionLabel }}</div></td>
									<td>
										<div class="eduedge-responsibility-tags">
											<span v-if="truthy(assignment.can_author)">Author</span>
											<span v-if="truthy(assignment.can_subject_review)">Subject Reviewer</span>
											<span v-if="truthy(assignment.can_final_approve)">Final Approver</span>
										</div>
									</td>
									<td>{{ validityLabel(assignment) }}</td>
									<td><EdgeStatusBadge :label="assignment.status" :status="assignment.status" :tone="statusTone(assignment.status)" /></td>
									<td>
										<div class="eduedge-responsibility-actions">
											<button v-if="context.permissions?.can_write" type="button" class="edge-button" @click="openAssignmentDialog(assignment)">Edit</button>
											<button
												v-if="context.permissions?.can_write"
												type="button"
												class="edge-button"
												:disabled="working"
												@click="confirmToggle(assignment)"
											>
												{{ truthy(assignment.enabled) ? 'Disable' : 'Enable' }}
											</button>
										</div>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>

	<EdgeFormDialog
		:open="modal.open"
		:title="modal.title"
		:subtitle="modal.subtitle"
		:fields="modal.fields"
		:model-value="modal.values"
		:field-errors="modal.fieldErrors"
		:error="modal.error"
		:loading="modal.loading"
		:busy="modal.busy"
		:submit-label="modal.submitLabel"
		@update:model-value="updateModalValues"
		@field-change="onModalFieldChange"
		@search-options="searchModalOptions"
		@submit="saveAssignment"
		@close="closeModal"
	/>

	<EdgeModal
		:open="confirmDialog.open"
		:title="confirmDialog.title"
		:subtitle="confirmDialog.message"
		size="sm"
		:busy="confirmDialog.busy"
		@close="closeConfirm"
	>
		<p>This changes only the responsibility assignment. It does not add or remove Frappe roles.</p>
		<template #footer>
			<span class="edge-modal__footer-spacer"></span>
			<button type="button" class="edge-button" :disabled="confirmDialog.busy" @click="closeConfirm">Cancel</button>
			<button type="button" class="edge-button edge-button--primary" :disabled="confirmDialog.busy" @click="executeToggle">
				{{ confirmDialog.busy ? 'Working…' : confirmDialog.confirmLabel }}
			</button>
		</template>
	</EdgeModal>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

function emptyModal() {
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
	return { open: false, busy: false, title: "", message: "", confirmLabel: "Continue", assignment: null };
}

export default {
	name: "EduEdgeQuestionResponsibilities",
	data() {
		return {
			loading: true,
			working: false,
			error: "",
			selectedInstitution: "",
			searchText: "",
			searchTimer: null,
			menuItems: EDUEDGE_MENU_ITEMS,
			modal: emptyModal(),
			confirmDialog: emptyConfirm(),
			context: {
				institution: "",
				institution_options: [],
				branch_options: [],
				assignments: [],
				counts: { total: 0, active: 0, authors: 0, subject_reviewers: 0, final_approvers: 0 },
				effective_policy: null,
				permissions: {},
				user: {},
			},
		};
	},
	computed: {
		selectedInstitutionLabel() {
			return this.context.institution_options.find((row) => row.value === this.context.institution)?.label || this.context.institution || "";
		},
		policySummary() {
			const policy = this.context.effective_policy;
			if (!policy) return "Select a permitted Institution to resolve its question governance policy.";
			const workflow = policy.question_approval_mode === "Standard"
				? "Subject review and recommendation are required before final approval."
				: "A permitted final approver may approve after submission for review.";
			const separation = policy.require_separate_question_approver
				? "The author and final approver must be different users."
				: "The same scoped user may author and approve when other controls permit it.";
			return `${workflow} ${separation}`;
		},
	},
	mounted() {
		this.loadContext();
	},
	beforeUnmount() {
		if (this.searchTimer) window.clearTimeout(this.searchTimer);
	},
	methods: {
		openRoute: openEduEdgeRoute,
		truthy(value) { return value === true || value === 1 || value === "1"; },
		async loadContext() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.question_responsibilities.get_context", {
					institution: this.selectedInstitution || undefined,
					search: this.searchText || undefined,
				});
				const state = response.message || {};
				this.context = { ...this.context, ...state };
				this.selectedInstitution = state.institution || "";
			} catch (error) {
				this.error = error?.message || "Question Responsibilities could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		changeInstitution() {
			this.searchText = "";
			return this.loadContext();
		},
		scheduleSearch() {
			if (this.searchTimer) window.clearTimeout(this.searchTimer);
			this.searchTimer = window.setTimeout(() => this.loadContext(), 300);
		},
		assignmentFields() {
			return [
				{ fieldname: "user", type: "Link", label: "User", required: true, options: [] },
				{ fieldname: "institution", type: "Link", label: "Institution", required: true, options: this.context.institution_options, read_only: true, disabled: true },
				{ fieldname: "school_branch", type: "Link", label: "Branch / Campus", options: this.context.branch_options, description: "Leave blank for all permitted Branches under this Institution." },
				{ fieldname: "course", type: "Link", label: "Subject / Course", required: true, options: [] },
				{ fieldname: "can_author", type: "Check", label: "Question Author", default: 0 },
				{ fieldname: "can_subject_review", type: "Check", label: "Subject Reviewer", default: 0 },
				{ fieldname: "can_final_approve", type: "Check", label: "Final Approver", default: 0 },
				{ fieldname: "enabled", type: "Check", label: "Enabled", default: 1 },
				{ fieldname: "valid_from", type: "Date", label: "Valid From" },
				{ fieldname: "valid_to", type: "Date", label: "Valid To" },
				{ fieldname: "notes", type: "Small Text", label: "Internal Notes" },
			];
		},
		async openAssignmentDialog(assignment = null) {
			this.modal = {
				...emptyModal(),
				open: true,
				loading: Boolean(assignment),
				name: assignment?.name || "",
				title: assignment ? "Update Question Responsibility" : "Add Question Responsibility",
				subtitle: "Authority is limited by Institution, optional Branch, Subject / Course, validity dates, and current Frappe permissions.",
				submitLabel: assignment ? "Save Changes" : "Create Assignment",
				fields: this.assignmentFields(),
				values: {
					user: "",
					institution: this.context.institution || "",
					school_branch: "",
					course: "",
					can_author: 0,
					can_subject_review: 0,
					can_final_approve: 0,
					enabled: 1,
					valid_from: "",
					valid_to: "",
					notes: "",
				},
			};
			if (!assignment) return;
			try {
				const response = await frappe.call("eduedge.api.question_responsibilities.get_assignment", { name: assignment.name });
				const state = response.message || {};
				this.modal.values = { ...this.modal.values, ...(state.values || {}) };
				if (!state.can_write) this.modal.error = "You may view this assignment but cannot update it.";
			} catch (error) {
				this.modal.error = error?.message || "The responsibility assignment could not be loaded.";
			} finally {
				this.modal.loading = false;
			}
		},
		updateModalValues(values) {
			this.modal.values = { ...(values || {}) };
			this.modal.fieldErrors = {};
			this.modal.error = "";
		},
		onModalFieldChange({ field, values } = {}) {
			this.modal.values = { ...(values || this.modal.values || {}) };
			this.modal.fieldErrors = { ...(this.modal.fieldErrors || {}), [field?.fieldname]: "" };
			this.modal.error = "";
		},
		async searchModalOptions({ field, query = "", values = {} } = {}) {
			if (!field?.fieldname || !this.modal.open) return;
			const fieldname = field.fieldname;
			const token = `${Date.now()}-${Math.random()}`;
			this.modal.searchTokens = { ...(this.modal.searchTokens || {}), [fieldname]: token };
			this.modal.fields = this.modal.fields.map((item) => item.fieldname === fieldname ? { ...item, options_loading: true } : item);
			try {
				const response = await frappe.call("eduedge.api.question_responsibilities.search_options", {
					fieldname,
					txt: query || "",
					values: JSON.stringify(values || this.modal.values || {}),
				});
				if (this.modal.searchTokens?.[fieldname] !== token) return;
				this.modal.fields = this.modal.fields.map((item) => item.fieldname === fieldname
					? { ...item, options: response.message || [], options_loading: false }
					: item);
			} catch (error) {
				if (this.modal.searchTokens?.[fieldname] !== token) return;
				this.modal.fields = this.modal.fields.map((item) => item.fieldname === fieldname ? { ...item, options_loading: false } : item);
				this.modal.error = error?.message || `Options for ${field.label || fieldname} could not be loaded.`;
			}
		},
		validateModal() {
			const errors = {};
			for (const fieldname of ["user", "institution", "course"]) {
				if (!String(this.modal.values?.[fieldname] || "").trim()) errors[fieldname] = "This field is required.";
			}
			if (!["can_author", "can_subject_review", "can_final_approve"].some((fieldname) => this.truthy(this.modal.values?.[fieldname]))) {
				this.modal.error = "Select at least one Question responsibility.";
				return false;
			}
			this.modal.fieldErrors = errors;
			return !Object.keys(errors).length;
		},
		async saveAssignment() {
			if (this.modal.busy || !this.validateModal()) return;
			this.modal.busy = true;
			this.modal.error = "";
			try {
				await frappe.call("eduedge.api.question_responsibilities.save_assignment", {
					name: this.modal.name || undefined,
					values: JSON.stringify(this.modal.values || {}),
				});
				this.closeModal(true);
				await this.loadContext();
				frappe.show_alert({ message: __("Question responsibility saved."), indicator: "green" }, 5);
			} catch (error) {
				this.modal.error = error?.message || "The responsibility assignment could not be saved.";
			} finally {
				this.modal.busy = false;
			}
		},
		closeModal(force = false) {
			if (this.modal.busy && !force) return;
			this.modal = emptyModal();
		},
		confirmToggle(assignment) {
			const enable = !this.truthy(assignment.enabled);
			this.confirmDialog = {
				open: true,
				busy: false,
				title: `${enable ? "Enable" : "Disable"} Question Responsibility`,
				message: `${enable ? "Enable" : "Disable"} ${assignment.user_full_name || assignment.user} for ${assignment.course_label || assignment.course}?`,
				confirmLabel: enable ? "Enable" : "Disable",
				assignment,
			};
		},
		closeConfirm() {
			if (this.confirmDialog.busy) return;
			this.confirmDialog = emptyConfirm();
		},
		async executeToggle() {
			const assignment = this.confirmDialog.assignment;
			if (!assignment || this.confirmDialog.busy) return;
			this.confirmDialog.busy = true;
			this.working = true;
			try {
				await frappe.call("eduedge.api.question_responsibilities.set_enabled", {
					name: assignment.name,
					enabled: this.truthy(assignment.enabled) ? 0 : 1,
				});
				this.confirmDialog = emptyConfirm();
				await this.loadContext();
			} catch (error) {
				this.confirmDialog.message = error?.message || "The assignment status could not be changed.";
				this.confirmDialog.busy = false;
			} finally {
				this.working = false;
			}
		},
		validityLabel(assignment) {
			if (assignment.valid_from && assignment.valid_to) return `${assignment.valid_from} to ${assignment.valid_to}`;
			if (assignment.valid_from) return `From ${assignment.valid_from}`;
			if (assignment.valid_to) return `Until ${assignment.valid_to}`;
			return "No date limit";
		},
		statusTone(status) {
			if (status === "Active") return "success";
			if (status === "Scheduled") return "warning";
			if (status === "Expired" || status === "Disabled") return "danger";
			return "neutral";
		},
	},
};
</script>

<style scoped>
.eduedge-responsibility-filters {
	display: grid;
	gap: .8rem;
	grid-template-columns: repeat(2, minmax(14rem, 1fr));
	width: 100%;
}
.eduedge-responsibility-filters label { display: grid; gap: .35rem; }
.eduedge-responsibility-filters span { color: var(--edge-color-ink-700, var(--text-color)); font-size: .76rem; font-weight: 650; }
.eduedge-responsibility-panel {
	background: var(--edge-color-surface, var(--card-bg));
	border: 1px solid var(--edge-color-border, var(--border-color));
	border-radius: var(--edge-radius-lg, .8rem);
	margin-top: 1rem;
	overflow: hidden;
}
.eduedge-policy-panel,
.eduedge-responsibility-heading {
	align-items: flex-start;
	display: flex;
	gap: 1rem;
	justify-content: space-between;
	padding: 1rem 1.1rem;
}
.eduedge-policy-panel h2,
.eduedge-responsibility-heading h2 { margin: .15rem 0 .25rem; }
.eduedge-policy-panel p,
.eduedge-responsibility-heading p { color: var(--edge-color-ink-500, var(--text-muted)); margin: 0; }
.eduedge-responsibility-table-wrap { overflow-x: auto; }
.eduedge-responsibility-table { margin: 0; min-width: 68rem; }
.eduedge-responsibility-table th { background: var(--edge-color-surface-soft, var(--control-bg)); font-size: .72rem; text-transform: uppercase; }
.eduedge-responsibility-tags,
.eduedge-responsibility-actions { display: flex; flex-wrap: wrap; gap: .4rem; }
.eduedge-responsibility-tags span {
	background: var(--edge-color-brand-50, #edf5ff);
	border: 1px solid var(--edge-color-brand-100, #dcecff);
	border-radius: 999px;
	font-size: .72rem;
	padding: .2rem .55rem;
}
@media (max-width: 700px) {
	.eduedge-responsibility-filters { grid-template-columns: 1fr; }
	.eduedge-policy-panel,
	.eduedge-responsibility-heading { align-items: stretch; flex-direction: column; }
}
</style>