<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="activeContext.company || ''"
		:branch-name="activeContext.branch_name || activeContext.institution_name || 'Institution Structure'"
		:menu-items="menuItems"
		active-route="/app/eduedge-institution-structure"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Academic Foundation"
					title="Institution Structure"
					subtitle="Manage the Company → Institution → Branch hierarchy and preview EduEdge-managed terminology."
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading institution structure..." :skeleton="true" />
			<EdgeErrorState v-else-if="error" title="Institution Structure could not load" :message="error" action-label="Try again" @retry="load" />
			<template v-else>
				<section class="eduedge-structure-guidance">
					<EdgeIcon name="building" size="md" />
					<div>
						<strong>Company owns Institutions; Institutions own Branches.</strong>
						<p>Institution Type belongs to the Institution. Every linked Branch inherits the same terminology automatically.</p>
					</div>
					<EdgeStatusBadge :label="activeContext.institution_type_name || 'Secondary School'" status="active" tone="info" />
				</section>

				<section v-if="activeContext.uses_secondary_fallback" class="eduedge-structure-warning">
					<strong>Secondary School fallback is active.</strong>
					<span>Create or select an Institution for normal operations. Company fallback is only used when no Institution or Branch context exists.</span>
				</section>

				<div class="eduedge-structure-grid">
					<section class="eduedge-structure-card">
						<p class="edge-eyebrow">1 · Company owner</p>
						<h2>Legal and accounting owner</h2>
						<label for="eduedge-structure-company">Company</label>
						<select id="eduedge-structure-company" v-model="selectedCompany" class="form-control" @change="companyChanged">
							<option value="">Select Company</option>
							<option v-for="company in setup.companies" :key="company.name" :value="company.name">{{ company.label }}</option>
						</select>
						<label for="eduedge-company-institution-type">Fallback Institution Type</label>
						<select id="eduedge-company-institution-type" v-model="companyDraft" class="form-control" :disabled="!selectedCompany || !setup.can_write_company || savingKey === 'company'" @change="previewType = companyDraft || setup.fallback_institution_type">
							<option value="">Use Secondary School fallback</option>
							<option v-for="type in setup.institution_types" :key="type.value" :value="type.value">{{ type.label }}</option>
						</select>
						<p class="eduedge-field-help">This does not replace an Institution. It applies only when no Institution or Branch is active.</p>
						<button type="button" class="edge-button edge-button--primary" :disabled="!selectedCompany || !setup.can_write_company || savingKey === 'company'" @click="saveCompany">
							{{ savingKey === 'company' ? 'Saving...' : 'Save Company Fallback' }}
						</button>
					</section>

					<section class="eduedge-structure-card">
						<div class="eduedge-card-heading">
							<div><p class="edge-eyebrow">2 · Institution</p><h2>{{ institutionDraft.name ? 'Edit Institution' : 'Create Institution' }}</h2></div>
							<button type="button" class="edge-button" @click="newInstitution">New</button>
						</div>
						<label for="eduedge-institution-select">Existing Institution</label>
						<select id="eduedge-institution-select" v-model="selectedInstitution" class="form-control" @change="institutionChanged">
							<option value="">Create new Institution</option>
							<option v-for="institution in companyInstitutions" :key="institution.name" :value="institution.name">{{ institution.institution_name }}</option>
						</select>
						<label>Institution Name</label>
						<input v-model="institutionDraft.institution_name" class="form-control" type="text" placeholder="Example: Royal Heritage Polytechnic" />
						<label>Institution Code</label>
						<input v-model="institutionDraft.institution_code" class="form-control" type="text" placeholder="Example: RHP" :disabled="Boolean(institutionDraft.name)" />
						<label>Institution Type</label>
						<select v-model="institutionDraft.institution_type" class="form-control" @change="previewType = institutionDraft.institution_type">
							<option value="">Select institution type</option>
							<option v-for="type in setup.institution_types" :key="type.value" :value="type.value">{{ type.label }}</option>
						</select>
						<label class="eduedge-check"><input v-model="institutionDraft.enabled" type="checkbox" /> Enabled</label>
						<label class="eduedge-check"><input v-model="institutionDraft.is_default" type="checkbox" /> Default for this Company</label>
						<button type="button" class="edge-button edge-button--primary" :disabled="!canSaveInstitution || savingKey === 'institution'" @click="saveInstitution">
							{{ savingKey === 'institution' ? 'Saving...' : 'Save Institution' }}
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

				<section class="eduedge-institutions-card">
					<div class="eduedge-card-heading">
						<div>
							<p class="edge-eyebrow">Institution hierarchy</p>
							<h2>{{ selectedCompanyRow?.label || 'Select a Company' }}</h2>
							<p>Each Institution may own several Branches or Campuses while retaining one seeded Institution Type.</p>
						</div>
						<EdgeStatusBadge :label="`${companyInstitutions.length} institutions`" status="active" tone="neutral" />
					</div>
					<EdgeEmptyState v-if="selectedCompany && !companyInstitutions.length" title="No Institutions found" message="Create the first Institution for this Company." />
					<div v-else class="eduedge-institution-list">
						<article v-for="institution in companyInstitutions" :key="institution.name" class="eduedge-institution-row">
							<div>
								<strong>{{ institution.institution_name }}</strong>
								<p>{{ typeLabel(institution.institution_type) }} · {{ branchesForInstitution(institution.name).length }} branches</p>
							</div>
							<EdgeStatusBadge v-if="institution.requires_review" label="Review migrated record" status="warning" tone="warning" />
							<button type="button" class="edge-button" @click="editInstitution(institution)">Edit</button>
						</article>
					</div>
				</section>

				<section class="eduedge-branches-card">
					<div class="eduedge-card-heading">
						<div>
							<p class="edge-eyebrow">3 · Branch or Campus</p>
							<h2>Assign Branches to Institutions</h2>
							<p>Institution Type is inherited and cannot be independently edited on a Branch.</p>
						</div>
						<EdgeStatusBadge :label="`${visibleBranches.length} branches`" status="active" tone="neutral" />
					</div>
					<EdgeEmptyState v-if="selectedCompany && !visibleBranches.length" title="No School Branches found" message="Create a School Branch for this Company before assigning it to an Institution." />
					<div v-else class="eduedge-branch-list">
						<div v-for="branch in visibleBranches" :key="branch.name" class="eduedge-branch-row">
							<div><strong>{{ branch.label }}</strong><p>{{ branch.institution_name || 'Institution not assigned' }}</p></div>
							<select v-model="branchDrafts[branch.name]" class="form-control" :disabled="!setup.can_write_branch || savingKey === branch.name">
								<option value="">Select Institution</option>
								<option v-for="institution in companyInstitutions" :key="institution.name" :value="institution.name">{{ institution.institution_name }}</option>
							</select>
							<button type="button" class="edge-button" :disabled="!branchDrafts[branch.name] || !setup.can_write_branch || savingKey === branch.name" @click="assignBranch(branch)">
								{{ savingKey === branch.name ? 'Saving...' : 'Assign' }}
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

const emptyInstitution = () => ({
	name: "", institution_name: "", institution_code: "", institution_type: "", enabled: true, is_default: false,
});

export default {
	name: "EduEdgeInstitutionStructure",
	data() {
		return {
			loading: true, error: "", saveError: "", savingKey: "",
			selectedCompany: "", companyDraft: "", selectedInstitution: "", previewType: "SECONDARY",
			institutionDraft: emptyInstitution(), branchDrafts: {},
			setup: {
				institution_types: [], companies: [], institutions: [], branches: [], active_context: {},
				fallback_institution_type: "SECONDARY", can_write_company: false,
				can_create_institution: false, can_write_institution: false, can_write_branch: false,
			},
			menuItems: EDUEDGE_MENU_ITEMS,
		};
	},
	computed: {
		activeContext() { return this.setup.active_context || {}; },
		selectedCompanyRow() { return this.setup.companies.find((row) => row.name === this.selectedCompany) || null; },
		companyInstitutions() { return this.setup.institutions.filter((row) => row.company === this.selectedCompany); },
		visibleBranches() { return this.setup.branches.filter((row) => row.company === this.selectedCompany); },
		previewDefinition() { return this.setup.institution_types.find((row) => row.value === this.previewType) || null; },
		previewTerms() {
			return Object.entries(this.previewDefinition?.terms || {})
				.map(([key, value]) => ({ key, ...value }))
				.sort((left, right) => Number(left.sequence || 0) - Number(right.sequence || 0));
		},
		canSaveInstitution() {
			const permitted = this.institutionDraft.name ? this.setup.can_write_institution : this.setup.can_create_institution;
			return Boolean(permitted && this.selectedCompany && this.institutionDraft.institution_name && this.institutionDraft.institution_code && this.institutionDraft.institution_type);
		},
	},
	mounted() { this.load(); },
	methods: {
		openRoute: openEduEdgeRoute,
		humanize(value) { return String(value || "").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); },
		typeLabel(value) { return this.setup.institution_types.find((row) => row.value === value)?.label || value; },
		branchesForInstitution(value) { return this.setup.branches.filter((row) => row.institution === value); },
		async load() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.institution_types.get_institution_type_setup");
				this.setup = response.message || this.setup;
				this.selectedCompany = this.setup.active_context?.company || this.setup.companies?.[0]?.name || "";
				this.branchDrafts = Object.fromEntries(this.setup.branches.map((row) => [row.name, row.institution || ""]));
				this.companyChanged();
				this.previewType = this.setup.active_context?.institution_type || this.companyDraft || this.setup.fallback_institution_type;
			} catch (error) {
				this.error = error?.message || "Institution Structure could not be loaded.";
			} finally { this.loading = false; }
		},
		companyChanged() {
			this.companyDraft = this.selectedCompanyRow?.configured_institution_type || "";
			this.previewType = this.companyDraft || this.selectedCompanyRow?.effective_institution_type || this.setup.fallback_institution_type;
			this.newInstitution();
		},
		newInstitution() {
			this.selectedInstitution = "";
			this.institutionDraft = emptyInstitution();
			this.saveError = "";
		},
		institutionChanged() {
			const row = this.companyInstitutions.find((item) => item.name === this.selectedInstitution);
			if (row) this.editInstitution(row);
			else this.newInstitution();
		},
		editInstitution(row) {
			this.selectedInstitution = row.name;
			this.institutionDraft = {
				name: row.name,
				institution_name: row.institution_name,
				institution_code: row.institution_code,
				institution_type: row.institution_type,
				enabled: Boolean(row.enabled),
				is_default: Boolean(row.is_default),
			};
			this.previewType = row.institution_type;
		},
		async saveCompany() {
			if (!this.selectedCompany || !this.setup.can_write_company) return;
			this.savingKey = "company";
			this.saveError = "";
			try {
				await frappe.call("eduedge.api.institution_types.save_company_institution_type", { company: this.selectedCompany, institution_type: this.companyDraft || undefined });
				frappe.show_alert({ message: __("Company fallback saved"), indicator: "green" });
				await this.load();
			} catch (error) { this.saveError = error?.message || "Company fallback could not be saved."; }
			finally { this.savingKey = ""; }
		},
		async saveInstitution() {
			if (!this.canSaveInstitution) return;
			this.savingKey = "institution";
			this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.institution_types.save_institution", {
					institution: this.institutionDraft.name || undefined,
					company: this.selectedCompany,
					institution_name: this.institutionDraft.institution_name,
					institution_code: this.institutionDraft.institution_code,
					institution_type: this.institutionDraft.institution_type,
					enabled: this.institutionDraft.enabled ? 1 : 0,
					is_default: this.institutionDraft.is_default ? 1 : 0,
				});
				if (response.message?.context && frappe.eduedge?.applyInstitutionContext) frappe.eduedge.applyInstitutionContext(response.message.context);
				frappe.show_alert({ message: __("Institution saved"), indicator: "green" });
				await this.load();
			} catch (error) { this.saveError = error?.message || "Institution could not be saved."; }
			finally { this.savingKey = ""; }
		},
		async assignBranch(branch) {
			const institution = this.branchDrafts[branch.name];
			if (!institution || !this.setup.can_write_branch) return;
			this.savingKey = branch.name;
			this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.institution_types.assign_branch_institution", { branch: branch.name, institution });
				if (response.message?.context?.branch === this.setup.active_context?.branch && frappe.eduedge?.applyInstitutionContext) frappe.eduedge.applyInstitutionContext(response.message.context);
				frappe.show_alert({ message: __("Branch assigned to Institution"), indicator: "green" });
				await this.load();
			} catch (error) { this.saveError = error?.message || "Branch Institution could not be assigned."; }
			finally { this.savingKey = ""; }
		},
	},
};
</script>

<style scoped>
.eduedge-structure-guidance, .eduedge-structure-warning { align-items: center; background: var(--edge-color-surface-soft, var(--control-bg)); border: 1px solid var(--edge-color-border, var(--border-color)); border-radius: var(--edge-radius-lg, 12px); display: flex; gap: 1rem; justify-content: space-between; margin-bottom: 1rem; padding: 1rem; }
.eduedge-structure-guidance p, .eduedge-structure-warning span, .eduedge-card-heading p, .eduedge-branch-row p, .eduedge-institution-row p { color: var(--text-muted); margin: .2rem 0 0; }
.eduedge-structure-warning { align-items: flex-start; border-color: var(--yellow-300, #f4d27a); flex-direction: column; }
.eduedge-structure-grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr)); }
.eduedge-structure-card, .eduedge-branches-card, .eduedge-institutions-card { background: var(--edge-color-surface, var(--card-bg)); border: 1px solid var(--edge-color-border, var(--border-color)); border-radius: var(--edge-radius-lg, 12px); display: grid; gap: .75rem; padding: 1rem; }
.eduedge-structure-card h2, .eduedge-branches-card h2, .eduedge-institutions-card h2 { margin: 0; }
.eduedge-structure-card label { font-weight: 650; }
.eduedge-check { align-items: center; display: flex; gap: .5rem; }
.eduedge-field-help { color: var(--text-muted); font-size: .82rem; margin: -.25rem 0 0; }
.eduedge-term-list { display: grid; gap: .25rem; max-height: 22rem; overflow: auto; }
.eduedge-term-row { align-items: center; border-bottom: 1px solid var(--edge-color-border, var(--border-color)); display: flex; gap: 1rem; justify-content: space-between; padding: .45rem 0; }
.eduedge-term-row span { color: var(--text-muted); }
.eduedge-branches-card, .eduedge-institutions-card { margin-top: 1rem; }
.eduedge-card-heading { align-items: flex-start; display: flex; gap: 1rem; justify-content: space-between; }
.eduedge-branch-list, .eduedge-institution-list { display: grid; gap: .65rem; }
.eduedge-branch-row, .eduedge-institution-row { align-items: center; background: var(--edge-color-surface-soft, var(--control-bg)); border-radius: .75rem; display: grid; gap: .75rem; grid-template-columns: minmax(12rem, 1fr) minmax(12rem, 18rem) auto; padding: .75rem; }
.eduedge-institution-row { grid-template-columns: minmax(12rem, 1fr) auto auto; }
.eduedge-structure-error { color: var(--red-600, #b42318); margin-top: 1rem; }
@media (max-width: 47.99rem) {
	.eduedge-structure-guidance, .eduedge-card-heading { align-items: stretch; flex-direction: column; }
	.eduedge-branch-row, .eduedge-institution-row { grid-template-columns: 1fr; }
}
</style>
