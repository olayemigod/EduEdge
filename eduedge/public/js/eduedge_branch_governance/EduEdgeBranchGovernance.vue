<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="context.selected_company || ''"
		branch-name="Governance"
		:user-name="context.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-branch-governance"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Branch Foundation"
					title="Branch Governance and Accounting"
					subtitle="Assign campus access, verify coverage, review accounting readiness, and activate enforcement safely."
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading branch governance..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error"
				title="Branch governance could not load"
				:message="error"
				action-label="Try again"
				@retry="loadContext"
			/>
			<template v-else>
				<EdgeFilterBar title="Governance scope">
					<div class="eduedge-governance-filters">
						<label>
							<span>Company</span>
							<select v-model="selectedCompany" class="form-control" @change="loadContext">
								<option value="">All Companies</option>
								<option v-for="company in context.companies" :key="company.name" :value="company.name">
									{{ company.company_name || company.name }}
								</option>
							</select>
						</label>
						<label>
							<span>Find assignment</span>
							<input v-model.trim="assignmentSearch" class="form-control" placeholder="User, role, branch, or company" />
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" @click="loadContext">Refresh</button>
						<button
							v-if="context.permissions.can_manage_access"
							type="button"
							class="edge-button edge-button--primary"
							@click="openAssignmentDialog()"
						>
							Add branch access
						</button>
					</template>
				</EdgeFilterBar>

				<EdgeDashboardLayout min-column-width="12rem">
					<EdgeStatCard label="Enabled Campuses" :value="context.counts.enabled_branches" helper="Within the selected company scope" />
					<EdgeStatCard label="Active Assignments" :value="context.counts.active_assignments" helper="Enabled and currently valid" />
					<EdgeStatCard label="Covered Campuses" :value="`${context.counts.covered_branches}/${context.counts.enabled_branches}`" helper="Direct or company HQ access" />
					<EdgeStatCard label="Accounting Ready" :value="`${context.counts.accounting_ready_branches}/${context.counts.enabled_branches}`" helper="Core branch defaults completed" />
					<EdgeStatCard label="Enforcement" :value="context.settings.enforcement_enabled ? 'Active' : 'Not Active'" helper="Backend operational access gate" />
				</EdgeDashboardLayout>

				<section class="eduedge-governance-panel eduedge-enforcement-panel">
					<div class="eduedge-panel-heading">
						<div>
							<p class="edge-eyebrow">Safe activation</p>
							<h2>User Branch Access Enforcement</h2>
							<p>When enabled, operational users see only branches covered by active assignments. Accounting readiness is shown here but does not silently create accounting records.</p>
						</div>
						<EdgeStatusBadge
							:label="context.settings.enforcement_enabled ? 'Enforcement active' : 'Legacy fallback active'"
							:status="context.settings.enforcement_enabled ? 'active' : 'legacy'"
							:tone="context.settings.enforcement_enabled ? 'success' : 'warning'"
						/>
					</div>
					<div class="eduedge-check-grid">
						<div v-for="check in context.activation_checks" :key="check.key" class="eduedge-check-row">
							<EdgeStatusBadge
								:label="check.passed ? 'Passed' : check.blocking ? 'Required' : 'Recommended'"
								:status="check.passed ? 'passed' : 'pending'"
								:tone="check.passed ? 'success' : check.blocking ? 'danger' : 'warning'"
							/>
							<span>{{ check.label }}</span>
						</div>
					</div>
					<EdgeActionBar label="Enable enforcement only after testing one-branch, multi-branch, no-switch, and HQ users.">
						<template #actions>
							<button type="button" class="edge-button" @click="openRoute('/app/eduedge-settings')">Open settings</button>
							<button
								v-if="context.permissions.can_manage_access"
								type="button"
								class="edge-button edge-button--primary"
								:disabled="working || (!context.settings.enforcement_enabled && !context.can_enable_enforcement)"
								@click="confirmEnforcementChange"
							>
								{{ context.settings.enforcement_enabled ? 'Disable enforcement' : 'Enable enforcement' }}
							</button>
						</template>
					</EdgeActionBar>
				</section>

				<section class="eduedge-governance-panel">
					<div class="eduedge-panel-heading">
						<div>
							<p class="edge-eyebrow">Campus configuration</p>
							<h2>Branch access and accounting coverage</h2>
							<p>Use quick editors for routine identity and assignment changes. Open the full branch form only for accounting defaults and advanced configuration.</p>
						</div>
						<div class="eduedge-row-actions" v-if="context.permissions.can_manage_accounting">
							<button type="button" class="edge-button" @click="openQuickEditor('instructor_branch_assignment')">Assign instructor</button>
							<button type="button" class="edge-button edge-button--primary" @click="openQuickEditor('school_branch')">Add campus</button>
						</div>
					</div>
					<EdgeEmptyState v-if="!context.branches.length" title="No enabled campuses" description="Create and enable a School Branch / Campus before assigning operational access." />
					<div v-else class="eduedge-table-wrap">
						<table class="table table-bordered eduedge-governance-table">
							<thead><tr><th>Campus</th><th>Company</th><th>Access Coverage</th><th>Accounting</th><th>Action</th></tr></thead>
							<tbody>
								<tr v-for="branch in context.branches" :key="branch.name">
									<td><strong>{{ branch.branch_name }}</strong><div class="text-muted">{{ branch.branch_code }} · {{ branch.branch_type }}</div></td>
									<td>{{ branch.company }}</td>
									<td>
										<EdgeStatusBadge :label="branch.access_covered ? 'Covered' : 'No active assignment'" :status="branch.access_covered ? 'covered' : 'uncovered'" :tone="branch.access_covered ? 'success' : 'danger'" />
										<div class="text-muted">{{ branch.direct_assignment_count }} direct{{ branch.covered_by_hq ? ' · HQ coverage' : '' }}</div>
									</td>
									<td>
										<EdgeStatusBadge :label="branch.accounting_ready ? 'Core defaults complete' : 'Defaults incomplete'" :status="branch.accounting_ready ? 'ready' : 'incomplete'" :tone="branch.accounting_ready ? 'success' : 'warning'" />
										<div v-if="branch.missing_accounting_labels.length" class="eduedge-missing-list">{{ branch.missing_accounting_labels.join(', ') }}</div>
									</td>
									<td>
										<button v-if="context.permissions.can_manage_accounting" type="button" class="edge-button" @click="openQuickEditor('school_branch', branch.name, { company: branch.company })">Quick edit</button>
										<button v-else type="button" class="edge-button" @click="openBranch(branch)">View</button>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>

				<section class="eduedge-governance-panel">
					<div class="eduedge-panel-heading">
						<div>
							<p class="edge-eyebrow">User assignments</p>
							<h2>Operational branch access</h2>
							<p>HQ access remains company-scoped. Disabled, expired, future-dated, or invalid assignments do not provide operational access.</p>
						</div>
						<button v-if="context.permissions.can_view_access_details" type="button" class="edge-button" @click="openRoute('/app/eduedge-user-branch-access')">Open native list</button>
					</div>
					<EdgeEmptyState v-if="!context.permissions.can_view_access_details" title="Assignment details restricted" description="Only System Manager and EduEdge Administrator can view or change named user assignments. Coverage summaries remain available." />
					<EdgeEmptyState v-else-if="!filteredAssignments.length" title="No matching branch assignments" description="Add a direct campus assignment or approved company HQ assignment." />
					<div v-else class="eduedge-table-wrap">
						<table class="table table-bordered eduedge-governance-table">
							<thead><tr><th>User</th><th>Scope</th><th>Role</th><th>Controls</th><th>Status</th><th>Action</th></tr></thead>
							<tbody>
								<tr v-for="assignment in filteredAssignments" :key="assignment.name">
									<td><strong>{{ assignment.user_full_name || assignment.user }}</strong><div class="text-muted">{{ assignment.user }}</div></td>
									<td><strong>{{ assignment.hq_all_branch_access ? 'All branches' : assignment.branch_name || assignment.school_branch }}</strong><div class="text-muted">{{ assignment.company }}</div></td>
									<td>{{ assignment.branch_role }}</td>
									<td>{{ assignment.is_default_branch ? 'Default · ' : '' }}{{ assignment.can_switch_branch ? 'Can switch' : 'No switching' }}</td>
									<td><EdgeStatusBadge :label="assignment.status" :status="assignment.status" :tone="assignmentTone(assignment.status)" /></td>
									<td>
										<div class="eduedge-row-actions">
											<button v-if="context.permissions.can_manage_access" type="button" class="edge-button" @click="openAssignmentDialog(assignment)">Edit</button>
											<button v-if="context.permissions.can_manage_access" type="button" class="edge-button" :disabled="working" @click="confirmAssignmentToggle(assignment)">{{ assignment.enabled ? 'Disable' : 'Enable' }}</button>
											<button v-else type="button" class="edge-button" @click="openAssignment(assignment)">View</button>
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
		:open="recordModal.open"
		:title="recordModal.title"
		:subtitle="recordModal.subtitle"
		:fields="recordModal.fields"
		:model-value="recordModal.values"
		:field-errors="recordModal.fieldErrors"
		:error="recordModal.error"
		:loading="recordModal.loading"
		:busy="recordModal.busy"
		:submit-label="recordModal.submitLabel"
		:show-full-form="Boolean(recordModal.fullFormRoute)"
		@update:model-value="updateModalValues"
		@field-change="onModalFieldChange"
		@search-options="onModalSearch"
		@submit="saveModalRecord"
		@open-full-form="openModalFullForm"
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
		<p class="eduedge-confirm-copy">Review the effect before continuing. This action uses the existing permission-aware EduEdge API.</p>
		<template #footer>
			<span class="edge-modal__footer-spacer"></span>
			<button type="button" class="edge-button" :disabled="confirmDialog.busy" @click="closeConfirm">Cancel</button>
			<button type="button" class="edge-button edge-button--primary" :disabled="confirmDialog.busy" @click="executeConfirm">
				{{ confirmDialog.busy ? 'Working…' : confirmDialog.confirmLabel }}
			</button>
		</template>
	</EdgeModal>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";
import {
	closeRecordModal,
	createRecordModalState,
	handleRecordModalFieldChange,
	openRecordFullForm,
	openRecordModal,
	saveRecordModal,
	searchRecordModalOptions,
	updateRecordModalValues,
} from "../eduedge_ui/modal_records";

function emptyConfirmDialog() {
	return { open: false, busy: false, title: "", message: "", confirmLabel: "Continue", action: null };
}

export default {
	name: "EduEdgeBranchGovernance",
	data() {
		return {
			loading: true,
			working: false,
			error: "",
			selectedCompany: "",
			assignmentSearch: "",
			menuItems: EDUEDGE_MENU_ITEMS,
			recordModal: createRecordModalState(),
			confirmDialog: emptyConfirmDialog(),
			context: {
				user: {}, companies: [], selected_company: null, branches: [], assignments: [], activation_checks: [],
				settings: { enforcement_enabled: false, hq_all_branch_view_enabled: true },
				counts: { enabled_branches: 0, active_assignments: 0, covered_branches: 0, accounting_ready_branches: 0 },
				permissions: { can_manage_access: false, can_view_access_details: false, can_manage_accounting: false },
				can_enable_enforcement: false,
			},
		};
	},
	computed: {
		filteredAssignments() {
			const needle = this.assignmentSearch.toLowerCase();
			if (!needle) return this.context.assignments;
			return this.context.assignments.filter((row) => [
				row.user, row.user_full_name, row.branch_role, row.company, row.school_branch, row.branch_name, row.status,
			].some((value) => String(value || "").toLowerCase().includes(needle)));
		},
	},
	mounted() { this.loadContext(); },
	methods: {
		openRoute: openEduEdgeRoute,
		assignmentTone(status) {
			if (status === "Active") return "success";
			if (["Expired", "User Disabled", "Branch Disabled"].includes(status)) return "danger";
			if (status === "Not Yet Active") return "warning";
			return "neutral";
		},
		async loadContext() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.branch_governance.get_governance_context", {
					company: this.selectedCompany || undefined,
				});
				this.context = response.message || this.context;
				this.selectedCompany = this.context.selected_company || this.selectedCompany;
			} catch (error) {
				this.error = error?.message || "Branch governance could not be loaded.";
			} finally { this.loading = false; }
		},
		openBranch(branch) { this.openRoute(`/app/eduedge-school-branch/${branch.name}`); },
		openAssignment(assignment) { this.openRoute(`/app/eduedge-user-branch-access/${assignment.name}`); },
		async openQuickEditor(resource, name = "", extraContext = {}) {
			await openRecordModal(this.recordModal, {
				resource,
				name,
				context: { company: this.selectedCompany || "", ...extraContext },
			});
		},
		openAssignmentDialog(assignment = null) {
			return this.openQuickEditor("user_branch_access", assignment?.name || "", {
				company: assignment?.company || this.selectedCompany || "",
				school_branch: assignment?.school_branch || "",
			});
		},
		updateModalValues(values) { updateRecordModalValues(this.recordModal, values); },
		onModalFieldChange(payload) { handleRecordModalFieldChange(this.recordModal, payload); },
		onModalSearch(payload) { return searchRecordModalOptions(this.recordModal, payload); },
		closeModal() { closeRecordModal(this.recordModal); },
		openModalFullForm() { openRecordFullForm(this.recordModal); },
		async saveModalRecord() {
			const result = await saveRecordModal(this.recordModal);
			if (!result) return;
			closeRecordModal(this.recordModal);
			frappe.show_alert({ message: __("EduEdge record saved"), indicator: "green" });
			await this.loadContext();
		},
		openConfirm({ title, message, confirmLabel, action }) {
			this.confirmDialog = { open: true, busy: false, title, message, confirmLabel, action };
		},
		closeConfirm() {
			if (this.confirmDialog.busy) return;
			this.confirmDialog = emptyConfirmDialog();
		},
		async executeConfirm() {
			if (!this.confirmDialog.action || this.confirmDialog.busy) return;
			this.confirmDialog.busy = true;
			try {
				await this.confirmDialog.action();
				this.confirmDialog = emptyConfirmDialog();
			} catch (error) {
				this.confirmDialog.busy = false;
				frappe.show_alert({ message: error?.message || __("The action could not be completed."), indicator: "red" });
			}
		},
		confirmAssignmentToggle(assignment) {
			const target = assignment.enabled ? 0 : 1;
			this.openConfirm({
				title: target ? __("Enable branch access?") : __("Disable branch access?"),
				message: __(`${target ? 'Enable' : 'Disable'} branch access for ${assignment.user_full_name || assignment.user}.`),
				confirmLabel: target ? __("Enable Access") : __("Disable Access"),
				action: async () => {
					await frappe.call("eduedge.api.branch_governance.set_branch_access_enabled", { name: assignment.name, enabled: target });
					await this.loadContext();
				},
			});
		},
		confirmEnforcementChange() {
			const target = !this.context.settings.enforcement_enabled;
			this.openConfirm({
				title: target ? __("Enable User Branch Access enforcement?") : __("Disable User Branch Access enforcement?"),
				message: target
					? __("This immediately restricts operational users to active branch assignments. Continue only after testing non-administrator accounts.")
					: __("This restores legacy permission-based branch visibility. Existing assignments remain available but are not enforced."),
				confirmLabel: target ? __("Enable Enforcement") : __("Disable Enforcement"),
				action: () => this.changeEnforcement(target),
			});
		},
		async changeEnforcement(target) {
			this.working = true;
			try {
				await frappe.call("eduedge.api.branch_governance.set_branch_enforcement", { enabled: target ? 1 : 0, confirmed: 1 });
				await this.loadContext();
				frappe.show_alert({ message: target ? __("Branch enforcement enabled") : __("Branch enforcement disabled"), indicator: target ? "green" : "orange" });
			} finally { this.working = false; }
		},
	},
};
</script>

<style scoped>
.eduedge-governance-filters { display: grid; grid-template-columns: repeat(2, minmax(14rem, 1fr)); gap: 1rem; width: min(42rem, 100%); }
.eduedge-governance-filters label { display: grid; gap: .35rem; }
.eduedge-governance-panel { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--edge-radius-lg, 12px); margin-top: var(--edge-space-5, 1.25rem); padding: var(--edge-space-5, 1.25rem); }
.eduedge-enforcement-panel { border-width: 2px; }
.eduedge-panel-heading { align-items: flex-start; display: flex; gap: 1rem; justify-content: space-between; margin-bottom: 1rem; }
.eduedge-panel-heading h2 { margin: .25rem 0 .5rem; }
.eduedge-panel-heading p { color: var(--text-muted); margin-bottom: 0; }
.eduedge-check-grid { display: grid; gap: .75rem; margin: 1rem 0; }
.eduedge-check-row { align-items: center; border: 1px solid var(--border-color); border-radius: var(--edge-radius-md, 8px); display: flex; gap: .75rem; padding: .75rem; }
.eduedge-table-wrap { overflow-x: auto; }
.eduedge-governance-table { margin-bottom: 0; min-width: 62rem; }
.eduedge-governance-table td { vertical-align: middle; }
.eduedge-missing-list { color: var(--text-muted); font-size: .85rem; margin-top: .35rem; max-width: 22rem; }
.eduedge-row-actions { display: flex; flex-wrap: wrap; gap: .5rem; }
.eduedge-confirm-copy { color: var(--edge-color-ink-700, var(--text-color)); line-height: 1.55; margin: 0; }
@media (max-width: 720px) {
	.eduedge-governance-filters { grid-template-columns: 1fr; }
	.eduedge-panel-heading { flex-direction: column; }
}
</style>
