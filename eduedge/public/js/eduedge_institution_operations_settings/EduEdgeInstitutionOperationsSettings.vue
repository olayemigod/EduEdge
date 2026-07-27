<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="selectedCompany || schoolIdentity.name || ''"
		branch-name="Institution Operations"
		:user-name="frappe.session.user_fullname || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-institution-operations-settings"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Administration"
					title="Institution Operations Settings"
					subtitle="Set a simple Company default and override it only where an Institution genuinely operates differently."
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading Institution Operations Settings..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error"
				title="Institution Operations Settings could not load"
				:message="error"
				action-label="Try again"
				@retry="loadContext"
			/>
			<template v-else>
				<EdgeFilterBar title="Settings context">
					<div class="eduedge-operations-filters">
						<label>
							<span>Settings level</span>
							<select :value="scope" class="form-control" @change="changeScope($event.target.value)">
								<option v-for="option in scopeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>
						<label>
							<span>Company</span>
							<select :value="selectedCompany" class="form-control" @change="changeCompany($event.target.value)">
								<option value="">Select Company</option>
								<option v-for="option in companyOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>
						<label v-if="isInstitutionScope">
							<span>Institution</span>
							<select :value="selectedInstitution" class="form-control" @change="changeInstitution($event.target.value)">
								<option value="">Select Institution</option>
								<option v-for="option in institutionOptions" :key="option.value" :value="option.value">
									{{ option.label }}
								</option>
							</select>
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" :disabled="loading || saving" @click="loadContext">Refresh</button>
					</template>
				</EdgeFilterBar>

				<EdgeEmptyState
					v-if="!selectedCompany || (isInstitutionScope && !selectedInstitution)"
					title="No available settings context"
					description="Select a permitted Company and Institution. Institution access follows the existing EduEdge permission and branch-isolation rules."
				/>
				<template v-else>
					<EdgeDashboardLayout min-column-width="12rem">
						<EdgeStatCard label="Institution Type" :value="effectivePolicy?.institution_type || 'Company default'" helper="Controls recommended workflow" />
						<EdgeStatCard label="Approval Mode" :value="effectivePolicy?.question_approval_mode || 'Not resolved'" :helper="approvalModeHelper" />
						<EdgeStatCard label="Bulk Approval" :value="effectivePolicy?.allow_bulk_question_approval ? 'Enabled' : 'Disabled'" :helper="bulkApprovalHelper" />
						<EdgeStatCard label="Effective Source" :value="effectivePolicy?.source || 'Not resolved'" helper="The resolver used by future Question Bank actions" />
					</EdgeDashboardLayout>

					<section class="eduedge-operations-panel">
						<div class="eduedge-operations-panel__heading">
							<div>
								<p class="edge-eyebrow">Question Governance</p>
								<h2>{{ scope }}</h2>
								<p>{{ scopeDescription }}</p>
							</div>
							<EdgeStatusBadge
								:label="canWrite ? 'Editable' : 'Read only'"
								:status="canWrite ? 'editable' : 'read-only'"
								:tone="canWrite ? 'success' : 'neutral'"
							/>
						</div>

						<div class="eduedge-operations-form">
							<label v-if="isInstitutionScope" class="eduedge-operations-check eduedge-operations-check--wide">
								<input
									type="checkbox"
									:checked="truthy(values.use_company_question_governance_defaults)"
									:disabled="!canWrite || saving"
									@change="setValue('use_company_question_governance_defaults', $event.target.checked ? 1 : 0)"
								/>
								<span>
									<strong>Use Company Question Governance Defaults</strong>
									<small>Recommended for small Institutions. Disable only when this Institution needs a different approval process.</small>
								</span>
							</label>

							<label>
								<span>Question Approval Mode</span>
								<select
									:value="values.question_approval_mode || 'Recommended'"
									class="form-control"
									:disabled="settingsDisabled"
									@change="setValue('question_approval_mode', $event.target.value)"
								>
									<option v-for="option in approvalModeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
								</select>
								<small>Simple uses one approval stage. Standard separates subject review from final approval.</small>
							</label>

							<label>
								<span>Maximum Questions per Bulk Action</span>
								<input
									:value="values.max_bulk_question_approval ?? 100"
									type="number"
									min="1"
									max="100"
									class="form-control"
									:disabled="settingsDisabled || !truthy(values.allow_bulk_question_approval)"
									@input="setValue('max_bulk_question_approval', Number($event.target.value || 0))"
								/>
								<small>EduEdge will never process more than 100 questions in one governed action.</small>
							</label>

							<label class="eduedge-operations-check">
								<input
									type="checkbox"
									:checked="truthy(values.allow_bulk_question_approval)"
									:disabled="settingsDisabled"
									@change="setValue('allow_bulk_question_approval', $event.target.checked ? 1 : 0)"
								/>
								<span>Allow Bulk Question Approval</span>
							</label>

							<label class="eduedge-operations-check">
								<input
									type="checkbox"
									:checked="truthy(values.require_separate_question_approver)"
									:disabled="settingsDisabled"
									@change="setValue('require_separate_question_approver', $event.target.checked ? 1 : 0)"
								/>
								<span>Require Different Author and Approver</span>
							</label>

							<label class="eduedge-operations-check">
								<input
									type="checkbox"
									:checked="truthy(values.allow_academic_admin_override)"
									:disabled="settingsDisabled"
									@change="setValue('allow_academic_admin_override', $event.target.checked ? 1 : 0)"
								/>
								<span>Allow Academic Administrator Override</span>
							</label>
						</div>

						<div class="eduedge-effective-policy">
							<strong>Effective behaviour</strong>
							<p>
								{{ effectivePolicySummary }}
							</p>
						</div>

						<p v-if="saveError" class="eduedge-operations-error" role="alert">{{ saveError }}</p>
						<EdgeActionBar :label="canWrite ? 'The saved policy becomes the source of truth for future Question Bank workflow and bulk actions.' : 'Your role can view this policy but cannot change it.'">
							<template #actions>
								<button type="button" class="edge-button" :disabled="saving" @click="resetValues">Reset</button>
								<button v-if="canWrite" type="button" class="edge-button edge-button--primary" :disabled="saving" @click="saveSettings">
									{{ saving ? 'Saving...' : 'Save Operations Settings' }}
								</button>
							</template>
						</EdgeActionBar>
					</section>

					<section class="eduedge-future-settings">
						<div>
							<p class="edge-eyebrow">Planned module settings</p>
							<h2>Added only when each module is implemented</h2>
							<p>This prevents inactive settings from confusing small Institutions while preserving one long-term operations screen.</p>
						</div>
						<div class="eduedge-future-settings__list">
							<span v-for="section in futureSections" :key="section">{{ section }}</span>
						</div>
					</section>
				</template>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

export default {
	name: "EduEdgeInstitutionOperationsSettings",
	data() {
		return {
			loading: true,
			saving: false,
			error: "",
			saveError: "",
			scope: "Institution Preference",
			scopeOptions: [],
			selectedCompany: "",
			companyOptions: [],
			selectedInstitution: "",
			institutionOptions: [],
			fields: [],
			values: {},
			originalValues: {},
			canWrite: false,
			effectivePolicy: null,
			futureSections: [],
			menuItems: EDUEDGE_MENU_ITEMS,
		};
	},
	computed: {
		schoolIdentity() { return frappe.boot?.eduedge_ui_identity?.school || {}; },
		isInstitutionScope() { return this.scope === "Institution Preference"; },
		inheritingCompany() {
			return this.isInstitutionScope && this.truthy(this.values.use_company_question_governance_defaults);
		},
		settingsDisabled() { return !this.canWrite || this.saving || this.inheritingCompany; },
		approvalModeOptions() {
			return this.fields.find((field) => field.fieldname === "question_approval_mode")?.options || [
				{ value: "Recommended", label: "Recommended" },
				{ value: "Simple", label: "Simple" },
				{ value: "Standard", label: "Standard" },
			];
		},
		scopeDescription() {
			return this.isInstitutionScope
				? "This Institution inherits its Company default unless you explicitly disable inheritance."
				: "These defaults apply to Institutions under the Company unless an Institution preference is enabled.";
		},
		approvalModeHelper() {
			const steps = this.effectivePolicy?.approval_steps;
			return steps ? `${steps} approval stage${steps === 1 ? "" : "s"}` : "Resolved from saved settings";
		},
		bulkApprovalHelper() {
			if (!this.effectivePolicy?.allow_bulk_question_approval) return "Individual actions only";
			return `Maximum ${this.effectivePolicy.max_bulk_question_approval || 100} questions`;
		},
		effectivePolicySummary() {
			if (!this.effectivePolicy) return "No effective policy is available for this context.";
			const mode = this.effectivePolicy.question_approval_mode;
			const bulk = this.effectivePolicy.allow_bulk_question_approval
				? `bulk actions up to ${this.effectivePolicy.max_bulk_question_approval} questions`
				: "individual approval actions only";
			const separation = this.effectivePolicy.require_separate_question_approver
				? "author and approver must be different"
				: "the same permitted user may author and approve";
			return `${mode} approval, ${bulk}, and ${separation}. Source: ${this.effectivePolicy.source}.`;
		},
	},
	mounted() { this.loadContext(); },
	methods: {
		openRoute: openEduEdgeRoute,
		truthy(value) { return value === true || value === 1 || value === "1"; },
		setValue(fieldname, value) {
			this.values = { ...this.values, [fieldname]: value };
			this.saveError = "";
		},
		async changeScope(scope) {
			this.scope = scope;
			await this.loadContext();
		},
		async changeCompany(company) {
			this.selectedCompany = company;
			this.selectedInstitution = "";
			await this.loadContext();
		},
		async changeInstitution(institution) {
			this.selectedInstitution = institution;
			await this.loadContext();
		},
		applyState(state) {
			this.scope = state.scope || this.scope;
			this.scopeOptions = state.scope_options || [];
			this.selectedCompany = state.company || "";
			this.companyOptions = state.company_options || [];
			this.selectedInstitution = state.institution || "";
			this.institutionOptions = state.institution_options || [];
			this.fields = state.fields || [];
			this.values = { ...(state.values || {}) };
			this.originalValues = { ...(state.values || {}) };
			this.canWrite = Boolean(state.can_write);
			this.effectivePolicy = state.effective_policy || null;
			this.futureSections = state.future_sections || [];
		},
		async loadContext() {
			this.loading = true;
			this.error = "";
			this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.institution_operations_settings.get_settings_context", {
					scope: this.scope || undefined,
					company: this.selectedCompany || undefined,
					institution: this.selectedInstitution || undefined,
				});
				this.applyState(response.message || {});
			} catch (error) {
				this.error = error?.message || "Institution Operations Settings could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		resetValues() {
			this.values = { ...this.originalValues };
			this.saveError = "";
		},
		async saveSettings() {
			if (!this.canWrite || this.saving) return;
			this.saving = true;
			this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.institution_operations_settings.save_settings", {
					scope: this.scope,
					company: this.selectedCompany,
					institution: this.selectedInstitution || undefined,
					values: JSON.stringify(this.values || {}),
				});
				this.applyState(response.message || {});
				frappe.show_alert({ message: __("Institution Operations Settings saved"), indicator: "green" });
			} catch (error) {
				this.saveError = error?.message || "Institution Operations Settings could not be saved.";
			} finally {
				this.saving = false;
			}
		},
	},
};
</script>

<style scoped>
.eduedge-operations-filters { display: grid; gap: .85rem; grid-template-columns: repeat(3, minmax(12rem, 1fr)); width: 100%; }
.eduedge-operations-filters label { display: grid; gap: .35rem; }
.eduedge-operations-filters span { color: var(--edge-color-ink-700, var(--text-color)); font-size: .78rem; font-weight: 680; }
.eduedge-operations-panel,
.eduedge-future-settings { background: var(--edge-color-surface, var(--card-bg)); border: 1px solid var(--edge-color-border, var(--border-color)); border-radius: var(--edge-radius-lg, 12px); margin-top: 1rem; padding: clamp(1rem, 2vw, 1.5rem); }
.eduedge-operations-panel__heading { align-items: flex-start; display: flex; gap: 1rem; justify-content: space-between; margin-bottom: 1.15rem; }
.eduedge-operations-panel__heading h2,
.eduedge-future-settings h2 { font-size: 1.1rem; margin: .15rem 0 .35rem; }
.eduedge-operations-panel__heading p,
.eduedge-future-settings p { color: var(--edge-color-ink-500, var(--text-muted)); margin: 0; }
.eduedge-operations-form { display: grid; gap: 1rem; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.eduedge-operations-form > label:not(.eduedge-operations-check) { display: grid; gap: .35rem; }
.eduedge-operations-form > label > span { font-size: .78rem; font-weight: 680; }
.eduedge-operations-form small { color: var(--edge-color-ink-500, var(--text-muted)); display: block; font-size: .69rem; font-weight: 400; line-height: 1.4; }
.eduedge-operations-check { align-items: center; border: 1px solid var(--edge-color-border, var(--border-color)); border-radius: .7rem; display: flex; gap: .65rem; min-height: 3.25rem; padding: .75rem; }
.eduedge-operations-check--wide { grid-column: 1 / -1; }
.eduedge-operations-check input { accent-color: var(--edge-color-brand-600, #0f64ab); flex: 0 0 auto; }
.eduedge-operations-check span { display: grid; gap: .2rem; }
.eduedge-effective-policy { background: var(--edge-color-brand-50, #edf5ff); border: 1px solid var(--edge-color-brand-100, #dcecff); border-radius: .75rem; margin-top: 1rem; padding: .85rem 1rem; }
.eduedge-effective-policy p { color: var(--edge-color-ink-700, var(--text-color)); margin: .3rem 0 0; }
.eduedge-operations-error { background: var(--red-50, #fff1f2); border: 1px solid var(--red-200, #fecdd3); border-radius: .65rem; color: var(--red-700, #b42318); margin: 1rem 0 0; padding: .75rem; }
.eduedge-future-settings { align-items: flex-start; display: grid; gap: 1rem; grid-template-columns: minmax(0, 1fr) minmax(18rem, 1fr); }
.eduedge-future-settings__list { display: flex; flex-wrap: wrap; gap: .45rem; }
.eduedge-future-settings__list span { background: var(--edge-color-surface-muted, var(--control-bg)); border: 1px solid var(--edge-color-border, var(--border-color)); border-radius: 999px; color: var(--edge-color-ink-600, var(--text-muted)); font-size: .72rem; padding: .35rem .6rem; }
@media (max-width: 840px) {
	.eduedge-operations-filters,
	.eduedge-operations-form,
	.eduedge-future-settings { grid-template-columns: 1fr; }
	.eduedge-operations-check--wide { grid-column: auto; }
}
</style>
