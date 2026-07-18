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
							<p>
								When enabled, operational users see only branches covered by active assignments. Accounting readiness is shown here but does not silently create accounting records.
							</p>
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
							<p>Open a campus record to complete validated cost centres, income, receivable, payment, adjustment, and optional stock defaults.</p>
						</div>
						<button v-if="context.permissions.can_manage_accounting" type="button" class="edge-button" @click="openRoute('/app/eduedge-school-branch/new')">Add campus</button>
					</div>
					<EdgeEmptyState v-if="!context.branches.length" title="No enabled campuses" description="Create and enable a School Branch / Campus before assigning operational access." />
					<div v-else class="eduedge-table-wrap">
						<table class="table table-bordered eduedge-governance-table">
							<thead>
								<tr>
									<th>Campus</th>
									<th>Company</th>
									<th>Access Coverage</th>
									<th>Accounting</th>
									<th>Action</th>
								</tr>
							</thead>
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
									<td><button type="button" class="edge-button" @click="openBranch(branch)">{{ context.permissions.can_manage_accounting ? 'Configure' : 'View' }}</button></td>
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
						<button type="button" class="edge-button" @click="openRoute('/app/eduedge-user-branch-access')">Open native list</button>
					</div>
					<EdgeEmptyState v-if="!filteredAssignments.length" title="No matching branch assignments" description="Add a direct campus assignment or approved company HQ assignment." />
					<div v-else class="eduedge-table-wrap">
						<table class="table table-bordered eduedge-governance-table">
							<thead>
								<tr><th>User</th><th>Scope</th><th>Role</th><th>Controls</th><th>Status</th><th>Action</th></tr>
							</thead>
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
											<button v-if="context.permissions.can_manage_access" type="button" class="edge-button" :disabled="working" @click="toggleAssignment(assignment)">{{ assignment.enabled ? 'Disable' : 'Enable' }}</button>
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
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const BRANCH_ROLES = [
	"School Administrator",
	"Academic Administrator",
	"Bursar",
	"Teacher",
	"CBT Invigilator",
	"Student Safety Officer",
	"Transport Coordinator",
	"Admissions Officer",
	"Other",
];

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
			context: {
				user: {}, companies: [], selected_company: null, branches: [], assignments: [], activation_checks: [],
				settings: { enforcement_enabled: false, hq_all_branch_view_enabled: true },
				counts: { enabled_branches: 0, active_assignments: 0, covered_branches: 0, accounting_ready_branches: 0 },
				permissions: { can_manage_access: false, can_manage_accounting: false },
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
		openAssignmentDialog(assignment = null) {
			const dialog = new frappe.ui.Dialog({
				title: assignment ? __("Edit Branch Access") : __("Add Branch Access"),
				fields: [
					{ fieldname: "user", fieldtype: "Link", options: "User", label: __("User"), reqd: 1, get_query: () => ({ filters: { enabled: 1, user_type: "System User" } }) },
					{ fieldname: "branch_role", fieldtype: "Select", options: BRANCH_ROLES.join("\n"), label: __("Role in Branch"), reqd: 1 },
					{ fieldname: "hq_all_branch_access", fieldtype: "Check", label: __("HQ / All-Branch Access"), default: 0 },
					{ fieldname: "company", fieldtype: "Link", options: "Company", label: __("Company"), reqd: 1, get_query: () => ({ filters: { is_group: 0 } }) },
					{ fieldname: "school_branch", fieldtype: "Link", options: "EduEdge School Branch", label: __("School Branch / Campus"), get_query: () => ({ filters: { company: dialog.get_value("company"), enabled: 1 } }) },
					{ fieldname: "controls", fieldtype: "Section Break", label: __("Access Controls") },
					{ fieldname: "is_default_branch", fieldtype: "Check", label: __("Default Branch"), default: 0 },
					{ fieldname: "can_switch_branch", fieldtype: "Check", label: __("Can Switch Branch"), default: 1 },
					{ fieldname: "enabled", fieldtype: "Check", label: __("Enabled"), default: 1 },
					{ fieldname: "validity", fieldtype: "Section Break", label: __("Validity") },
					{ fieldname: "valid_from", fieldtype: "Date", label: __("Valid From") },
					{ fieldname: "valid_to", fieldtype: "Date", label: __("Valid To") },
				],
				primary_action_label: assignment ? __("Save Changes") : __("Create Assignment"),
				primary_action: async (values) => {
					dialog.disable_primary_action();
					try {
						await frappe.call("eduedge.api.branch_governance.save_branch_access", {
							payload: JSON.stringify({ ...(assignment ? { name: assignment.name } : {}), ...values }),
						});
						dialog.hide();
						await this.loadContext();
						frappe.show_alert({ message: __("Branch access saved"), indicator: "green" });
					} catch (error) {
						frappe.msgprint({ title: __("Unable to save branch access"), message: error?.message || __("The assignment could not be saved."), indicator: "red" });
					} finally { dialog.enable_primary_action(); }
				},
			});

			const applyScope = () => {
				const hq = Boolean(dialog.get_value("hq_all_branch_access"));
				dialog.set_df_property("school_branch", "hidden", hq);
				dialog.set_df_property("school_branch", "reqd", !hq);
				dialog.set_df_property("is_default_branch", "hidden", hq);
				if (hq) {
					dialog.set_value("school_branch", "");
					dialog.set_value("is_default_branch", 0);
					dialog.set_value("can_switch_branch", 1);
				}
			};
			dialog.fields_dict.hq_all_branch_access.df.onchange = applyScope;
			dialog.fields_dict.company.df.onchange = () => {
				if (!dialog.get_value("hq_all_branch_access")) dialog.set_value("school_branch", "");
			};
			if (assignment) {
				Promise.resolve(dialog.set_values({
					user: assignment.user,
					branch_role: assignment.branch_role,
					hq_all_branch_access: assignment.hq_all_branch_access,
					company: assignment.company,
					school_branch: assignment.school_branch,
					is_default_branch: assignment.is_default_branch,
					can_switch_branch: assignment.can_switch_branch,
					enabled: assignment.enabled,
					valid_from: assignment.valid_from,
					valid_to: assignment.valid_to,
				})).then(applyScope);
			} else {
				if (this.selectedCompany) dialog.set_value("company", this.selectedCompany);
				applyScope();
			}
			dialog.show();
		},
		async toggleAssignment(assignment) {
			const target = assignment.enabled ? 0 : 1;
			const verb = target ? "enable" : "disable";
			frappe.confirm(
				__(`Are you sure you want to ${verb} branch access for ${assignment.user_full_name || assignment.user}?`),
				async () => {
					this.working = true;
					try {
						await frappe.call("eduedge.api.branch_governance.set_branch_access_enabled", { name: assignment.name, enabled: target });
						await this.loadContext();
					} catch (error) {
						frappe.msgprint({ title: __("Unable to change assignment"), message: error?.message || __("The assignment could not be changed."), indicator: "red" });
					} finally { this.working = false; }
				}
			);
		},
		confirmEnforcementChange() {
			const target = !this.context.settings.enforcement_enabled;
			const title = target ? __("Enable User Branch Access enforcement?") : __("Disable User Branch Access enforcement?");
			const message = target
				? __("This immediately restricts operational users to active branch assignments. Continue only after testing non-administrator accounts.")
				: __("This restores legacy permission-based branch visibility. Existing assignments remain available but are not enforced.");
			frappe.confirm(`${title}<br><br>${message}`, () => this.changeEnforcement(target));
		},
		async changeEnforcement(target) {
			this.working = true;
			try {
				await frappe.call("eduedge.api.branch_governance.set_branch_enforcement", { enabled: target ? 1 : 0, confirmed: 1 });
				await this.loadContext();
				frappe.show_alert({ message: target ? __("Branch enforcement enabled") : __("Branch enforcement disabled"), indicator: target ? "green" : "orange" });
			} catch (error) {
				frappe.msgprint({ title: __("Enforcement change blocked"), message: error?.message || __("The enforcement setting could not be changed."), indicator: "red" });
			} finally { this.working = false; }
		},
	},
};
</script>

<style scoped>
.eduedge-governance-filters { display: grid; grid-template-columns: repeat(2, minmax(14rem, 1fr)); gap: 1rem; width: min(42rem, 100%); }
.eduedge-governance-filters label { display: grid; gap: 0.35rem; }
.eduedge-governance-panel { margin-top: var(--edge-space-5, 1.25rem); padding: var(--edge-space-5, 1.25rem); border: 1px solid var(--border-color); border-radius: var(--edge-radius-lg, 12px); background: var(--card-bg); }
.eduedge-enforcement-panel { border-width: 2px; }
.eduedge-panel-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; }
.eduedge-panel-heading h2 { margin: 0.25rem 0 0.5rem; }
.eduedge-panel-heading p { margin-bottom: 0; color: var(--text-muted); }
.eduedge-check-grid { display: grid; gap: 0.75rem; margin: 1rem 0; }
.eduedge-check-row { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: var(--edge-radius-md, 8px); }
.eduedge-table-wrap { overflow-x: auto; }
.eduedge-governance-table { min-width: 62rem; margin-bottom: 0; }
.eduedge-governance-table td { vertical-align: middle; }
.eduedge-missing-list { max-width: 22rem; margin-top: 0.35rem; color: var(--text-muted); font-size: 0.85rem; }
.eduedge-row-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
@media (max-width: 720px) {
	.eduedge-governance-filters { grid-template-columns: 1fr; }
	.eduedge-panel-heading { flex-direction: column; }
}
</style>
