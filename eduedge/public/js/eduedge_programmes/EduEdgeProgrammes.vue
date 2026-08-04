<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="activeContext.institution_name || ''"
		:branch-name="activeContext.branch_name || programmePlural"
		:menu-items="menuItems"
		active-route="/app/eduedge-programs"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Academic Catalogue"
					:title="programmePlural"
					:subtitle="`Maintain the native ${departmentSingular} → ${programmeSingular} structure. ${coursePlural} and advanced curriculum settings remain available in the native form.`"
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
									{{ institution.institution_name }} · {{ institution.institution_type_name || institution.institution_type }}
								</option>
							</select>
						</label>
						<label>
							<span>{{ departmentSingular }}</span>
							<select v-model="filters.department" class="form-control" @change="applyFilters">
								<option value="">All {{ departmentPlural.toLowerCase() }}</option>
								<option v-for="department in data.departments" :key="department.name" :value="department.name">
									{{ departmentLabel(department) }}
								</option>
							</select>
						</label>
						<label>
							<span>Search</span>
							<input v-model.trim="filters.search" class="form-control" :placeholder="`Search ${programmePlural.toLowerCase()}`" @keyup.enter="applyFilters" />
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" @click="openDepartmentTree">Open {{ departmentSingular }} tree</button>
						<button type="button" class="edge-button" @click="clearFilters">Clear</button>
						<button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="applyFilters">{{ loading ? "Loading..." : "Apply" }}</button>
					</template>
				</EdgeFilterBar>

				<EdgeDashboardLayout min-column-width="12rem">
					<EdgeStatCard label="Matching Catalogue" :value="data.summary.total_programmes" :helper="`${data.summary.visible_programmes} on this page`" />
					<EdgeStatCard :label="`${coursePlural} Rows`" :value="data.summary.course_rows" helper="Across visible records" />
					<EdgeStatCard :label="`Active ${offeringPlural}`" :value="data.summary.active_offerings" helper="Across visible records" tone="success" />
					<EdgeStatCard label="Needs Classification" :value="data.summary.unclassified_visible" :helper="`Missing Institution or ${departmentSingular}`" :tone="data.summary.unclassified_visible ? 'warning' : 'neutral'" />
				</EdgeDashboardLayout>

				<p v-if="error && loadedOnce" class="eduedge-programme-error">{{ error }}</p>
				<div class="eduedge-programme-layout">
					<section class="eduedge-programme-panel">
						<div class="eduedge-programme-panel-heading">
							<div><p class="edge-eyebrow">Catalogue</p><h2>{{ programmePlural }}</h2></div>
							<button type="button" class="edge-button" @click="openNativeList">Open native list</button>
						</div>
						<EdgeLoadingState v-if="loading" :message="`Refreshing ${programmePlural.toLowerCase()}...`" />
						<EdgeEmptyState v-else-if="!data.programmes.length" :title="`No ${programmePlural.toLowerCase()} found`" :description="`Create a ${departmentSingular} first, then create the ${programmeSingular} beneath it.`" />
						<div v-else class="eduedge-programme-list">
							<article v-for="row in data.programmes" :key="row.name" class="eduedge-programme-row">
								<button type="button" class="eduedge-programme-main" @click="editProgramme(row)">
									<span class="eduedge-programme-title"><strong>{{ row.program_name || row.name }}</strong><small>{{ row.program_abbreviation || row.name }}</small></span>
									<span class="eduedge-programme-context">{{ institutionName(row.eduedge_institution) }}<small>{{ departmentName(row.department) }}</small></span>
									<span class="eduedge-programme-counts">
										<EdgeStatusBadge :label="`${row.course_count} ${coursePlural.toLowerCase()} row(s)`" status="courses" tone="neutral" />
										<EdgeStatusBadge :label="`${row.active_offering_count} active ${offeringPlural.toLowerCase()}`" status="offerings" :tone="row.active_offering_count ? 'success' : 'neutral'" />
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
							<div><p class="edge-eyebrow">{{ draft.name ? "Quick edit" : "Quick create" }}</p><h2>{{ draft.name ? draft.program_name || editorProgrammeSingular : `New ${editorProgrammeSingular}` }}</h2></div>
							<button type="button" class="edge-button" @click="newProgramme">Reset</button>
						</div>
						<EdgeEmptyState v-if="!canCreate && !canWrite" title="Read-only catalogue" description="Your current role can view these records but cannot create or edit them." />
						<template v-else>
							<label><span>{{ editorProgrammeSingular }} name</span><input v-model.trim="draft.program_name" class="form-control" /></label>
							<label><span>Abbreviation</span><input v-model.trim="draft.program_abbreviation" class="form-control" /></label>
							<label>
								<span>Institution</span>
								<select v-model="draft.eduedge_institution" class="form-control" :disabled="Boolean(draft.name && draft.active_offering_count)" @change="draftInstitutionChanged">
									<option value="">Select Institution</option>
									<option v-for="institution in data.institutions" :key="institution.name" :value="institution.name">{{ institution.institution_name }}</option>
								</select>
							</label>
							<label>
								<span>{{ editorDepartmentSingular }}</span>
								<select v-model="draft.department" class="form-control" :disabled="Boolean(draft.name && draft.active_offering_count)">
									<option value="">Select {{ editorDepartmentSingular }}</option>
									<option v-for="department in draftDepartments" :key="department.name" :value="department.name">{{ departmentLabel(department) }}</option>
								</select>
							</label>
							<p class="text-muted">{{ editorExample }}</p>
							<div class="eduedge-programme-editor-actions">
								<button type="button" class="edge-button edge-button--primary" :disabled="!canSave || saving" @click="saveProgramme">{{ saving ? "Saving..." : `Save ${editorProgrammeSingular}` }}</button>
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

const emptyDraft = () => ({ name: "", program_name: "", program_abbreviation: "", department: "", eduedge_institution: "", active_offering_count: 0 });

export default {
	name: "EduEdgeProgrammes",
	data() {
		return {
			loading: true, loadedOnce: false, error: "", saving: false, saveError: "",
			menuItems: EDUEDGE_MENU_ITEMS,
			filters: { institution: "", department: "", search: "" },
			draft: emptyDraft(),
			data: {
				active_context: {}, programmes: [], institutions: [], departments: [],
				summary: { total_programmes: 0, visible_programmes: 0, course_rows: 0, active_offerings: 0, unclassified_visible: 0 },
				paging: { start: 0, page_length: 25, has_more: false, next_start: 0 },
				permissions: { can_create: false, can_write: false },
			},
		};
	},
	computed: {
		activeContext() { return this.data.active_context || {}; },
		mixedInstitutionView() {
			if (this.filters.institution) return false;
			return new Set((this.data.institutions || []).map((row) => row.institution_type).filter(Boolean)).size > 1;
		},
		pageContext() {
			return this.data.institutions.find((row) => row.name === this.filters.institution)?.context || this.activeContext;
		},
		draftContext() {
			return this.data.institutions.find((row) => row.name === this.draft.eduedge_institution)?.context || this.pageContext;
		},
		programmeSingular() { return this.mixedInstitutionView ? "Class / Programme" : this.term("programme", false, "Programme", this.pageContext); },
		programmePlural() { return this.mixedInstitutionView ? "Classes / Programmes" : this.term("programme", true, "Programmes", this.pageContext); },
		departmentSingular() { return this.mixedInstitutionView ? "School Section / Faculty / Department" : this.term("department", false, "Department", this.pageContext); },
		departmentPlural() { return this.mixedInstitutionView ? "School Sections / Faculties / Departments" : this.term("department", true, "Departments", this.pageContext); },
		coursePlural() { return this.mixedInstitutionView ? "Subjects / Courses / Modules" : this.term("course", true, "Courses", this.pageContext); },
		offeringPlural() { return this.mixedInstitutionView ? "Class / Programme Intakes" : this.term("programme_offering", true, "Programme Intakes", this.pageContext); },
		editorProgrammeSingular() { return this.term("programme", false, "Class / Programme", this.draftContext); },
		editorDepartmentSingular() { return this.term("department", false, "Academic Unit", this.draftContext); },
		editorExample() {
			const type = this.draftContext?.institution_type;
			if (type === "PRIMARY") return "Example: Primary Section → Primary 1.";
			if (type === "SECONDARY") return "Example: Junior Secondary School → JSS 1.";
			if (type === "TERTIARY") return "Example: Department of Crop Science → BSc Agriculture.";
			if (type === "TRAINING_CENTRE") return "Example: Technical Training → Electrical Installation.";
			return "Select an Institution to apply the correct academic terminology.";
		},
		canCreate() { return Boolean(this.data.permissions.can_create); },
		canWrite() { return Boolean(this.data.permissions.can_write); },
		canSave() {
			const permitted = this.draft.name ? this.canWrite : this.canCreate;
			return Boolean(permitted && this.draft.program_name && this.draft.eduedge_institution && this.draft.department);
		},
		draftDepartments() { return this.data.departments.filter((row) => !row.eduedge_institution || row.eduedge_institution === this.draft.eduedge_institution); },
	},
	mounted() { this.load(true); },
	methods: {
		openRoute: openEduEdgeRoute,
		term(key, plural = false, fallback = "", context = null) { return frappe.eduedge?.term?.(key, { plural, context: context || this.pageContext, fallback }) || fallback; },
		institutionName(name) { return this.data.institutions.find((row) => row.name === name)?.institution_name || name || "Unclassified Institution"; },
		departmentName(name) { return this.data.departments.find((row) => row.name === name)?.department_name || name || `No ${this.departmentSingular}`; },
		departmentLabel(row) { return row.parent_department ? `${row.department_name || row.name} · ${row.parent_department}` : row.department_name || row.name; },
		async load(resetStart = false) {
			if (resetStart) this.data.paging.start = 0;
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.programmes.get_programmes_page", { ...this.filters, start: this.data.paging.start || 0, page_length: this.data.paging.page_length || 25 });
				this.data = response.message || this.data;
				this.filters = { ...this.filters, ...(this.data.filters || {}) };
				if (!this.draft.eduedge_institution) this.draft.eduedge_institution = this.filters.institution || this.activeContext.institution || "";
				this.loadedOnce = true;
			} catch (error) { this.error = error?.message || `${this.programmePlural} could not be loaded.`; }
			finally { this.loading = false; }
		},
		applyFilters() { this.load(true); },
		institutionChanged() { this.filters.department = ""; this.newProgramme(); this.load(true); },
		clearFilters() { this.filters = { institution: "", department: "", search: "" }; this.newProgramme(); this.load(true); },
		previousPage() { this.data.paging.start = Math.max(0, this.data.paging.start - this.data.paging.page_length); this.load(false); },
		nextPage() { if (this.data.paging.has_more) { this.data.paging.start = this.data.paging.next_start; this.load(false); } },
		newProgramme() { this.draft = { ...emptyDraft(), eduedge_institution: this.filters.institution || this.activeContext.institution || "" }; this.saveError = ""; },
		editProgramme(row) { this.draft = { ...emptyDraft(), ...row }; this.saveError = ""; },
		draftInstitutionChanged() {
			if (!this.draftDepartments.some((row) => row.name === this.draft.department)) this.draft.department = "";
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
					department: this.draft.department,
				});
				frappe.show_alert({ message: __(`${this.editorProgrammeSingular} saved`), indicator: "green" });
				await this.load(true);
				const row = this.data.programmes.find((item) => item.name === response.message?.name);
				if (row) this.editProgramme(row); else this.newProgramme();
			} catch (error) { this.saveError = error?.message || `${this.editorProgrammeSingular} could not be saved.`; }
			finally { this.saving = false; }
		},
		openFullForm(name) { if (name) frappe.set_route("Form", "Program", name); },
		openNativeList() { window.open("/app/program", "_blank", "noopener,noreferrer"); },
		openDepartmentTree() { window.open("/app/department/view/tree", "_blank", "noopener,noreferrer"); },
	},
};
</script>

<style scoped>
.eduedge-programme-filter-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(13rem,1fr)); gap:.75rem; width:100%; }
.eduedge-programme-filter-grid label,.eduedge-programme-editor label { display:grid; gap:.35rem; font-weight:600; }
.eduedge-programme-layout { display:grid; grid-template-columns:minmax(0,1.5fr) minmax(20rem,.8fr); gap:1rem; margin-top:1rem; }
.eduedge-programme-panel { display:grid; gap:1rem; align-content:start; padding:1rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.eduedge-programme-panel-heading,.eduedge-programme-row,.eduedge-programme-main,.eduedge-programme-counts,.eduedge-programme-editor-actions { display:flex; gap:.75rem; align-items:center; }
.eduedge-programme-panel-heading { justify-content:space-between; }
.eduedge-programme-panel-heading h2 { margin:0; }
.eduedge-programme-list { display:grid; gap:.65rem; }
.eduedge-programme-row { padding:.75rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.eduedge-programme-main { flex:1; justify-content:space-between; padding:0; border:0; background:transparent; text-align:left; }
.eduedge-programme-title,.eduedge-programme-context { display:grid; gap:.2rem; min-width:0; }
.eduedge-programme-title small,.eduedge-programme-context small { color:var(--text-muted); }
.eduedge-programme-counts { flex-wrap:wrap; }
.eduedge-programme-paging { display:flex; justify-content:space-between; align-items:center; gap:.75rem; }
.eduedge-programme-error { margin:0; color:var(--red-600,#b42318); }
@media (max-width:1050px) { .eduedge-programme-layout { grid-template-columns:1fr; } .eduedge-programme-main { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media (max-width:650px) { .eduedge-programme-row,.eduedge-programme-main,.eduedge-programme-panel-heading,.eduedge-programme-paging { align-items:stretch; flex-direction:column; } .eduedge-programme-main { display:grid; grid-template-columns:1fr; } }
</style>
