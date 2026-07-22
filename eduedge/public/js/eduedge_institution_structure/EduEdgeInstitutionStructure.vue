<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="activeContext.company || ''"
		:branch-name="activeContext.branch_name || 'Institution Structure'"
		:menu-items="menuItems"
		active-route="/app/eduedge-institution-structure"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Academic Foundation"
					title="Institution Structure"
					subtitle="Apply EduEdge-managed academic terminology to the Company fallback and each School Branch."
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading institution structure..." :skeleton="true" />
			<EdgeErrorState v-else-if="error" title="Institution Structure could not load" :message="error" action-label="Try again" @retry="load" />
			<template v-else>
				<section class="eduedge-structure-guidance">
					<EdgeIcon name="building" size="md" />
					<div>
						<strong>Institution types and terminology are controlled by EduEdge.</strong>
						<p>The Company setting is optional. Every School Branch has an explicit institution type, and branch context takes precedence across EduEdge.</p>
					</div>
					<EdgeStatusBadge :label="activeContext.institution_type_name || 'Secondary School'" status="active" tone="info" />
				</section>

				<section v-if="activeContext.uses_secondary_fallback" class="eduedge-structure-warning">
					<strong>Secondary School fallback is active.</strong>
					<span>Set the Company Institution Type when this organisation is not a secondary school.</span>
				</section>

				<div class="eduedge-structure-grid">
					<section class="eduedge-structure-card">
						<p class="edge-eyebrow">Company fallback</p>
						<h2>Top-level institution owner</h2>
						<label for="eduedge-structure-company">Company</label>
						<select id="eduedge-structure-company" v-model="selectedCompany" class="form-control" @change="companyChanged">
							<option value="">Select Company</option>
							<option v-for="company in setup.companies" :key="company.name" :value="company.name">{{ company.label }}</option>
						</select>
						<label for="eduedge-company-institution-type">Institution Type</label>
						<select id="eduedge-company-institution-type" v-model="companyDraft" class="form-control" :disabled="!selectedCompany || !setup.can_write_company || savingKey === 'company'" @change="previewType = companyDraft || setup.fallback_institution_type">
							<option value="">Use Secondary School fallback</option>
							<option v-for="type in setup.institution_types" :key="type.value" :value="type.value">{{ type.label }}</option>
						</select>
						<p class="eduedge-field-help">This value applies only when no School Branch context is available.</p>
						<button type="button" class="edge-button edge-button--primary" :disabled="!selectedCompany || !setup.can_write_company || savingKey === 'company'" @click="saveCompany">
							{{ savingKey === 'company' ? 'Saving...' : 'Save Company Fallback' }}
						</button>
					</section>

					<section class="eduedge-structure-card">
						<p class="edge-eyebrow">Terminology preview</p>
						<h2>{{ previewDefinition?.label || 'Secondary School' }}</h2>
						<select v-model="previewType" class="form-control">
							<option v-for="type in setup.institution_types" :key="type.value" :value="type.value">{{ type.label }}</option>
						</select>
						<div class="eduedge-term-list">
							<div v-for="term in previewTerms" :key="term.key" class="eduedge-term-row">
								<span>{{ humanize(term.key) }}</span>
								<strong>{{ term.singular }}</strong>
							</div>
						</div>
					</section>
				</div>

				<section class="eduedge-branches-card">
					<div class="eduedge-card-heading">
						<div>
							<p class="edge-eyebrow">Branch-wide terminology</p>
							<h2>School Branch institution types</h2>
							<p>A Company may operate Primary, Secondary, Tertiary, and Training Centre branches under one legal identity.</p>
						</div>
						<EdgeStatusBadge :label="`${visibleBranches.length} branches`" status="active" tone="neutral" />
					</div>
					<EdgeEmptyState v-if="selectedCompany && !visibleBranches.length" title="No School Branches found" message="Create a School Branch for this Company before assigning branch terminology." />
					<div v-else class="eduedge-branch-list">
						<div v-for="branch in visibleBranches" :key="branch.name" class="eduedge-branch-row">
							<div><strong>{{ branch.label }}</strong><p>{{ branch.company }}</p></div>
							<select v-model="branchDrafts[branch.name]" class="form-control" :disabled="!setup.can_write_branch || savingKey === branch.name" @change="previewType = branchDrafts[branch.name]">
								<option value="">Select institution type</option>
								<option v-for="type in setup.institution_types" :key="type.value" :value="type.value">{{ type.label }}</option>
							</select>
							<button type="button" class="edge-button" :disabled="!branchDrafts[branch.name] || !setup.can_write_branch || savingKey === branch.name" @click="saveBranch(branch)">
								{{ savingKey === branch.name ? 'Saving...' : 'Save' }}
							</button>
						</div>
					</div>
				</section>

				<p v-if="saveError" class="eduedge-structure-error" role="alert">{{ saveError }}</p>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

export default {
	name: "EduEdgeInstitutionStructure",
	data() {
		return {
			loading: true,
			error: "",
			saveError: "",
			savingKey: "",
			selectedCompany: "",
			companyDraft: "",
			previewType: "SECONDARY",
			branchDrafts: {},
			setup: {
				institution_types: [], companies: [], branches: [],
				active_context: {}, fallback_institution_type: "SECONDARY",
				can_write_company: false, can_write_branch: false,
			},
			menuItems: EDUEDGE_MENU_ITEMS,
		};
	},
	computed: {
		activeContext() { return this.setup.active_context || {}; },
		selectedCompanyRow() { return this.setup.companies.find((row) => row.name === this.selectedCompany) || null; },
		visibleBranches() { return this.setup.branches.filter((row) => !this.selectedCompany || row.company === this.selectedCompany); },
		previewDefinition() { return this.setup.institution_types.find((row) => row.value === this.previewType) || null; },
		previewTerms() {
			return Object.entries(this.previewDefinition?.terms || {})
				.map(([key, value]) => ({ key, ...value }))
				.sort((left, right) => Number(left.sequence || 0) - Number(right.sequence || 0));
		},
	},
	mounted() { this.load(); },
	methods: {
		openRoute: openEduEdgeRoute,
		humanize(value) { return String(value || "").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); },
		async load() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.institution_types.get_institution_type_setup");
				this.setup = response.message || this.setup;
				this.selectedCompany = this.setup.active_context?.company || this.setup.companies?.[0]?.name || "";
				this.branchDrafts = Object.fromEntries(this.setup.branches.map((row) => [row.name, row.institution_type || ""]));
				this.companyChanged();
				this.previewType = this.setup.active_context?.institution_type || this.companyDraft || this.setup.fallback_institution_type;
			} catch (error) {
				this.error = error?.message || "Institution Structure could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		companyChanged() {
			this.companyDraft = this.selectedCompanyRow?.configured_institution_type || "";
			this.previewType = this.companyDraft || this.selectedCompanyRow?.effective_institution_type || this.setup.fallback_institution_type;
		},
		async saveCompany() {
			if (!this.selectedCompany || !this.setup.can_write_company) return;
			this.savingKey = "company";
			this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.institution_types.save_company_institution_type", { company: this.selectedCompany, institution_type: this.companyDraft || undefined });
				if (response.message?.context && frappe.eduedge?.applyInstitutionContext) frappe.eduedge.applyInstitutionContext(response.message.context);
				frappe.show_alert({ message: __("Company institution fallback saved"), indicator: "green" });
				await this.load();
			} catch (error) {
				this.saveError = error?.message || "Company institution type could not be saved.";
			} finally { this.savingKey = ""; }
		},
		async saveBranch(branch) {
			const institutionType = this.branchDrafts[branch.name];
			if (!institutionType || !this.setup.can_write_branch) return;
			this.savingKey = branch.name;
			this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.institution_types.save_branch_institution_type", { branch: branch.name, institution_type: institutionType });
				if (response.message?.context?.branch === this.setup.active_context?.branch && frappe.eduedge?.applyInstitutionContext) frappe.eduedge.applyInstitutionContext(response.message.context);
				frappe.show_alert({ message: __("Branch institution type saved"), indicator: "green" });
				await this.load();
			} catch (error) {
				this.saveError = error?.message || "Branch institution type could not be saved.";
			} finally { this.savingKey = ""; }
		},
	},
};
</script>

<style scoped>
.eduedge-structure-guidance, .eduedge-structure-warning { align-items: center; background: var(--edge-color-surface-soft, var(--control-bg)); border: 1px solid var(--edge-color-border, var(--border-color)); border-radius: var(--edge-radius-lg, 12px); display: flex; gap: 1rem; justify-content: space-between; margin-bottom: 1rem; padding: 1rem; }
.eduedge-structure-guidance p, .eduedge-structure-warning span, .eduedge-card-heading p, .eduedge-branch-row p { color: var(--text-muted); margin: .2rem 0 0; }
.eduedge-structure-warning { align-items: flex-start; border-color: var(--yellow-300, #f4d27a); flex-direction: column; }
.eduedge-structure-grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr)); }
.eduedge-structure-card, .eduedge-branches-card { background: var(--edge-color-surface, var(--card-bg)); border: 1px solid var(--edge-color-border, var(--border-color)); border-radius: var(--edge-radius-lg, 12px); display: grid; gap: .75rem; padding: 1rem; }
.eduedge-structure-card h2, .eduedge-branches-card h2 { margin: 0; }
.eduedge-structure-card label { font-weight: 650; }
.eduedge-field-help { color: var(--text-muted); font-size: .82rem; margin: -.25rem 0 0; }
.eduedge-term-list { display: grid; gap: .25rem; max-height: 22rem; overflow: auto; }
.eduedge-term-row { align-items: center; border-bottom: 1px solid var(--edge-color-border, var(--border-color)); display: flex; gap: 1rem; justify-content: space-between; padding: .45rem 0; }
.eduedge-term-row span { color: var(--text-muted); }
.eduedge-branches-card { margin-top: 1rem; }
.eduedge-card-heading { align-items: flex-start; display: flex; gap: 1rem; justify-content: space-between; }
.eduedge-branch-list { display: grid; gap: .65rem; }
.eduedge-branch-row { align-items: center; background: var(--edge-color-surface-soft, var(--control-bg)); border-radius: .75rem; display: grid; gap: .75rem; grid-template-columns: minmax(12rem, 1fr) minmax(12rem, 18rem) auto; padding: .75rem; }
.eduedge-structure-error { color: var(--red-600, #b42318); margin-top: 1rem; }
@media (max-width: 47.99rem) {
	.eduedge-structure-guidance, .eduedge-card-heading { align-items: stretch; flex-direction: column; }
	.eduedge-branch-row { grid-template-columns: 1fr; }
}
</style>
