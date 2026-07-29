<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="activeContext.institution_name || ''"
		:branch-name="activeContext.branch_name || programmePlural"
		:user-name="activeContext.user_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-programs"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Academic Catalogue"
					:title="programmePlural"
					:subtitle="`Maintain Institution-owned ${programmePlural.toLowerCase()} and open the full Frappe form for course rows and advanced curriculum setup.`"
					:action-label="canCreate ? `New ${programmeSingular}` : ''"
					@action="newProgramme"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loadedOnce" :message="`Loading ${programmePlural.toLowerCase()}...`" :skeleton="true" />
			<EdgeErrorState
				v-else-if="error && !loadedOnce"
				:title="`${programmePlural} could not load`"
				:message="error"
				action-label="Try again"
				@retry="load(true)"
			/>
			<template v-else>
				<EdgeFilterBar title="Catalogue filters">
					<div class="eduedge-programme-filter-grid">
						<label>
							<span>Institution</span>
							<select v-model="filters.institution" class="form-control" @change="institutionChanged">
								<option value="">All permitted Institutions</option>
								<option v-for="institution in data.institutions" :key="institution.name" :value="institution.name">
									{{ institution.institution_name }} · {{ institution.institution_type }}
								</option>
							</select>
						</label>
						<label>
							<span>{{ sectionPlural }}</span>
							<select v-model="filters.academic_section" class="form-control" @change="applyFilters">
								<option value="">All {{ sectionPlural.toLowerCase() }}</option>
								<option v-for="section in data.sections" :key="section.name" :value="section.name">
									{{ section.section_name }}
								</option>
							</select>
						</label>
						<label>
							<span>Department</span>
							<input
								v-model.trim="filters.department"
								list="eduedge-programme-departments"
								class="form-control"
								placeholder="All departments"
								@input="queueDepartmentSearch(filters.department, filters.institution)"
								@change="applyFilters"
							/>
						</label>
						<label>
							<span>Search</span>
							<input
								v-model.trim="filters.search"
								class="form-control"
								:placeholder="`Search ${programmePlural.toLowerCase()}`"
								@keyup.enter="applyFilters"
							/>
						</label>
					</div>
					<datalist id="eduedge-programme-departments">
						<option v-for="option in departmentOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
					</datalist>
					<template #actions>
						<button type="button" class="edge-button" @click="clearFilters">Clear</button>
						<button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="applyFilters">{{ loading ? "Loading..." : "Apply" }}</button>
					</template>
				</EdgeFilterBar>

				<EdgeDashboardLayout min-column-width="12rem">
					<EdgeStatCard label="Matching Catalogue" :value="data.summary.total_programmes" :helper="`${data.summary.visible_programmes} on this page`" />
					<EdgeStatCard label="Course Rows" :value="data.summary.course_rows" helper="Across visible records" />
					<EdgeStatCard label="Active Offerings" :value="data.summary.active_offerings" helper="Across visible records" tone="success" />
					<EdgeStatCard label="Needs Classification" :value="data.summary.unclassified_visible" helper="Visible legacy records without Institution" :tone="data.summary.unclassified_visible ? 'warning' : 'neutral'" />
				</EdgeDashboardLayout>

				<p v-if="error && loadedOnce" class="eduedge-programme-error">{{ error }}</p>

				<div class="eduedge-programme-layout">
					<section class="eduedge-programme-panel">
						<div class="eduedge-programme-panel-heading">
							<div><p class="edge-eyebrow">Catalogue</p><h2>{{ programmePlural }}</h2></div>
							<button type="button" class="edge-button" @click="openNativeList">Open native list</button>
						</div>

						<EdgeLoadingState v-if="loading" :message="`Refreshing ${programmePlural.toLowerCase()}...`" />
						<EdgeEmptyState v-else-if="!data.programmes.length" :title="`No ${programmePlural.toLowerCase()} found`" description="Change the filters or create the first record for this Institution." />
						<div v-else class="eduedge-programme-list">
							<article v-for="row in data.programmes" :key="row.name" class="eduedge-programme-row">
								<button type="button" class="eduedge-programme-main" @click="editProgramme(row)">
									<span class="eduedge-programme-title"><strong>{{ row.program_name || row.name }}</strong><small>{{ row.program_abbreviation || row.name }}</small></span>
									<span class="eduedge-programme-context">{{ institutionName(row.eduedge_institution) }}<small>{{ sectionName(row.eduedge_academic_section) || "No academic section" }}</small></span>
									<span class="eduedge-programme-context">{{ row.department || "No department" }}<small>{{ formatDate(row.modified) }}</small></span>
									<span class="eduedge-programme-counts">
										<EdgeStatusBadge :label="`${row.course_count} course row(s)`" status="courses" tone="neutral" />
										<EdgeStatusBadge :label="`${row.active_offering_count} active offering(s)`" status="offerings" :tone="row.active_offering_count ? 'success' : 'neutral'" />
									</span>
								</button>
								<button type="button" class="edge-button" @click="openFullForm(row.name)">Full form</button>
							</article>
						</div>

						<div class="eduedge-programme-paging">
							<button type="button" class="edge-button" :disabled="loading || data.paging.start <= 0" @click="previousPage">Previous</button>
							<span>{{ data.paging.start + (data.programmes.length ? 1 : 0) }}–{{ data.paging.start + data.programmes.length }} of {{ data.summary.total_programmes }}</span>
							<button type="button" class="edge-button" :disabled="loading || !data.paging.has_more" @click="nextPage">Next</button>
						</div>
					</section>

					<section class="eduedge-programme-panel eduedge-programme-editor">
						<div class="eduedge-programme-panel-heading">
							<div><p class="edge-eyebrow">{{ draft.name ? "Quick edit" : "Quick create" }}</p><h2>{{ draft.name ? draft.program_name || programmeSingular : `New ${programmeSingular}` }}</h2></div>
							<button type="button" class="edge-button" @click="newProgramme">Reset</button>
						</div>

						<EdgeEmptyState v-if="!canCreate && !canWrite" title="Read-only catalogue" description="Your current role can view these records but cannot create or edit them." />
						<template v-else>
							<label><span>{{ programmeSingular }} name</span><input v-model.trim="draft.program_name" class="form-control" /></label>
							<label><span>Abbreviation</span><input v-model.trim="draft.program_abbreviation" class="form-control" /></label>
							<label>
								<span>Institution</span>
								<select v-model="draft.eduedge_institution" class="form-control" @change="draftInstitutionChanged">
									<option value="">Select Institution</option>
									<option v-for="institution in data.institutions" :key="institution.name" :value="institution.name">{{ institution.institution_name }}</option>
								</select>
							</label>
							<label>
								<span>{{ sectionSingular }}</span>
								<select v-model="draft.eduedge_academic_section" class="form-control">
									<option value="">Not assigned</option>
									<option v-for="section in draftSections" :key="section.name" :value="section.name">{{ section.section_name }}</option>
								</select>
							</label>
							<label>
								<span>Department</span>
								<input
									v-model.trim="draft.department"
									list="eduedge-programme-departments"
									class="form-control"
									placeholder="Optional department"
									@input="queueDepartmentSearch(draft.department, draft.eduedge_institution)"
								/>
							</label>
							<p class="text-muted">Course rows, portal settings, and advanced fields remain in the full Program form.</p>
							<div class="eduedge-programme-editor-actions">
								<button type="button" class="edge-button edge-button--primary" :disabled="!canSave || saving" @click="saveProgramme">{{ saving ? "Saving..." : `Save ${programmeSingular}` }}</button>
								<button v-if="draft.name" type="button" class="edge-button" @click="openFullForm(draft.name)">Open full form</button>
							</div>
							<p v-if="saveError" class="eduedge-programme-error">{{ saveError }}</p>
						</template>
					</section>
				</div>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const emptyDraft = () => ({
	name: "",
	program_name: "",
	program_abbreviation: "",
	department: "",
	eduedge_institution: "",
	eduedge_academic_section: "",
});

export default {
	name: "EduEdgeProgrammes",
	data() {
		return {
			loading: true,
			loadedOnce: false,
			error: "",
			saving: false,
			saveError: "",
			departmentTimer: null,
			departmentOptions: [],
			menuItems: EDUEDGE_MENU_ITEMS,
			filters: { institution: "", academic_section: "", department: "", search: "" },
			draft: emptyDraft(),
			data: {
				active_context: {}, programmes: [], institutions: [], sections: [],
				summary: { total_programmes: 0, visible_programmes: 0, course_rows: 0, active_offerings: 0, unclassified_visible: 0 },
				paging: { start: 0, page_length: 25, has_more: false, next_start: 0 },
				permissions: { can_create: false, can_write: false },
			},
		};
	},
	computed: {
		activeContext() { return this.data.active_context || {}; },
		programmeSingular() { return this.term("programme", false, "Programme"); },
		programmePlural() { return this.term("programme", true, "Programmes"); },
		sectionSingular() { return this.term("academic_section", false, "Academic Section"); },
		sectionPlural() { return this.term("academic_section", true, "Academic Sections"); },
		canCreate() { return Boolean(this.data.permissions.can_create); },
		canWrite() { return Boolean(this.data.permissions.can_write); },
		canSave() {
			const permitted = this.draft.name ? this.canWrite : this.canCreate;
			return Boolean(permitted && this.draft.program_name && this.draft.eduedge_institution);
		},
		draftSections() { return this.data.sections.filter((section) => section.institution === this.draft.eduedge_institution); },
	},
	mounted() { this.load(true); },
	beforeUnmount() { if (this.departmentTimer) window.clearTimeout(this.departmentTimer); },
	methods: {
		openRoute: openEduEdgeRoute,
		term(key, plural = false, fallback = "") { return frappe.eduedge?.term?.(key, { plural, context: this.activeContext, fallback }) || fallback; },
		institutionName(name) { return this.data.institutions.find((row) => row.name === name)?.institution_name || name || "Unclassified Institution"; },
		sectionName(name) { return this.data.sections.find((row) => row.name === name)?.section_name || name || ""; },
		formatDate(value) { return value ? frappe.datetime.str_to_user(value) : "—"; },
		async load(resetStart = false) {
			if (resetStart) this.data.paging.start = 0;
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.programmes.get_programmes_page", {
					institution: this.filters.institution || undefined,
					academic_section: this.filters.academic_section || undefined,
					department: this.filters.department || undefined,
					search: this.filters.search || undefined,
					start: this.data.paging.start || 0,
					page_length: this.data.paging.page_length || 25,
				});
				this.data = response.message || this.data;
				this.filters = { ...this.filters, ...(this.data.filters || {}) };
				if (!this.draft.eduedge_institution) this.draft.eduedge_institution = this.filters.institution || this.activeContext.institution || "";
				await this.loadDepartments("", this.filters.institution || this.draft.eduedge_institution);
				this.loadedOnce = true;
			} catch (error) { this.error = error?.message || `${this.programmePlural} could not be loaded.`; }
			finally { this.loading = false; }
		},
		applyFilters() { this.load(true); },
		async institutionChanged() {
			this.filters.academic_section = "";
			this.filters.department = "";
			this.newProgramme();
			await this.loadDepartments("", this.filters.institution);
			await this.load(true);
		},
		async clearFilters() {
			this.filters = { institution: "", academic_section: "", department: "", search: "" };
			this.newProgramme();
			await this.loadDepartments("", "");
			await this.load(true);
		},
		previousPage() { this.data.paging.start = Math.max(0, this.data.paging.start - this.data.paging.page_length); this.load(false); },
		nextPage() { if (!this.data.paging.has_more) return; this.data.paging.start = this.data.paging.next_start; this.load(false); },
		newProgramme() {
			this.draft = { ...emptyDraft(), eduedge_institution: this.filters.institution || this.activeContext.institution || "" };
			this.saveError = "";
		},
		async editProgramme(row) {
			this.draft = { ...emptyDraft(), ...row };
			this.saveError = "";
			await this.loadDepartments("", this.draft.eduedge_institution);
		},
		async draftInstitutionChanged() {
			const valid = this.draftSections.some((section) => section.name === this.draft.eduedge_academic_section);
			if (!valid) this.draft.eduedge_academic_section = "";
			this.draft.department = "";
			await this.loadDepartments("", this.draft.eduedge_institution);
		},
		async saveProgramme() {
			if (!this.canSave) return;
			this.saving = true; this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.programmes.save_programme", {
					programme: this.draft.name || undefined,
					program_name: this.draft.program_name,
					program_abbreviation: this.draft.program_abbreviation || undefined,
					institution: this.draft.eduedge_institution,
					academic_section: this.draft.eduedge_academic_section || undefined,
					department: this.draft.department || undefined,
				});
				const saved = response.message || {};
				frappe.show_alert({ message: __(`${this.programmeSingular} saved`), indicator: "green" });
				await this.load(true);
				const row = this.data.programmes.find((item) => item.name === saved.name);
				if (row) await this.editProgramme(row); else this.newProgramme();
			} catch (error) { this.saveError = error?.message || `${this.programmeSingular} could not be saved.`; }
			finally { this.saving = false; }
		},
		queueDepartmentSearch(value, institution) {
			if (this.departmentTimer) window.clearTimeout(this.departmentTimer);
			this.departmentTimer = window.setTimeout(() => this.loadDepartments(value, institution), 250);
		},
		async loadDepartments(value, institution) {
			try {
				const response = await frappe.call("eduedge.api.programmes.search_departments", { txt: value || undefined, institution: institution || undefined });
				this.departmentOptions = response.message || [];
			} catch (_error) { this.departmentOptions = []; }
		},
		openFullForm(name) { if (name) frappe.set_route("Form", "Program", name); },
		openNativeList() { window.open("/app/program", "_blank", "noopener,noreferrer"); },
	},
};
</script>

<style scoped>
.eduedge-programme-filter-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(13rem,1fr)); gap:.75rem; width:100%; }
.eduedge-programme-filter-grid label,.eduedge-programme-editor label { display:grid; gap:.35rem; font-weight:600; }
.eduedge-programme-layout { display:grid; grid-template-columns:minmax(0,1.6fr) minmax(18rem,.8fr); gap:1rem; margin-top:1rem; }
.eduedge-programme-panel { display:grid; gap:1rem; align-content:start; padding:1rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.eduedge-programme-panel-heading { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; }
.eduedge-programme-panel-heading h2 { margin:0; }
.eduedge-programme-list { display:grid; gap:.75rem; }
.eduedge-programme-row { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:.75rem; align-items:center; padding:.75rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.eduedge-programme-main { display:grid; grid-template-columns:minmax(12rem,1.2fr) minmax(10rem,1fr) minmax(9rem,.9fr) minmax(12rem,auto); gap:.75rem; align-items:center; width:100%; padding:0; border:0; background:transparent; text-align:left; }
.eduedge-programme-title,.eduedge-programme-context { display:grid; gap:.2rem; }
.eduedge-programme-title small,.eduedge-programme-context small { color:var(--text-muted); }
.eduedge-programme-counts,.eduedge-programme-editor-actions { display:flex; flex-wrap:wrap; gap:.5rem; }
.eduedge-programme-paging { display:flex; justify-content:space-between; align-items:center; gap:.75rem; }
.eduedge-programme-error { margin:.75rem 0 0; color:var(--red-600,#b42318); }
@media (max-width:1100px) { .eduedge-programme-layout { grid-template-columns:1fr; } .eduedge-programme-main { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media (max-width:700px) { .eduedge-programme-row,.eduedge-programme-main { grid-template-columns:1fr; } .eduedge-programme-paging,.eduedge-programme-panel-heading { align-items:stretch; flex-direction:column; } }
</style>
