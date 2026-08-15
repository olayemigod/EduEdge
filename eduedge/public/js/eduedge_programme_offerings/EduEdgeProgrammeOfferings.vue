<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="activeContext.institution_name || ''"
		:branch-name="activeContext.branch_name || offeringPlural"
		:menu-items="menuItems"
		active-route="/app/eduedge-program-offerings"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Academic Setup"
					:title="offeringPlural"
					:subtitle="`${offeringPlural} are sessional: one ${programmeSingular.toLowerCase()} availability record per Branch and Academic Session. Terms and Semesters are managed in the Institution Academic Calendar.`"
					:action-label="canCreate ? `New ${offeringSingular}` : ''"
					@action="newOffering"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loadedOnce" :message="`Loading ${offeringPlural.toLowerCase()}...`" :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loadedOnce" :title="`${offeringPlural} could not load`" :message="error" action-label="Try again" @retry="load(true, false)" />
			<template v-else>
				<EdgeFilterBar title="Offering filters">
					<div class="eduedge-offering-filter-grid">
						<label><span>Institution</span><select v-model="filters.institution" class="form-control" @change="filterInstitutionChanged"><option value="">All permitted Institutions</option><option v-for="institution in data.options.institutions || []" :key="institution.name" :value="institution.name">{{ institution.institution_name || institution.name }}</option></select></label>
						<label><span>Branch / Campus</span><select v-model="filters.branch" class="form-control" @change="filterBranchChanged"><option value="">Current / permitted Branch</option><option v-for="branch in filterBranches" :key="branch.name" :value="branch.name">{{ branch.branch_name || branch.name }}</option></select></label>
						<label><span>{{ programmeSingular }}</span><select v-model="filters.program" class="form-control" @change="applyFilters"><option value="">All {{ programmePlural.toLowerCase() }}</option><option v-for="programme in filterProgrammes" :key="programme.name" :value="programme.name">{{ programme.program_name || programme.name }}</option></select></label>
						<label><span>{{ academicYearSingular }}</span><select v-model="filters.academic_year" class="form-control" @change="filterYearChanged"><option value="">All {{ academicYearPlural.toLowerCase() }}</option><option v-for="year in data.options.academic_years || []" :key="year.name" :value="year.name">{{ year.name }}</option></select></label>
						<label><span>Status</span><select v-model="filters.is_active" class="form-control" @change="applyFilters"><option value="">Active and disabled</option><option value="1">Active only</option><option value="0">Disabled only</option></select></label>
						<label><span>Study Mode</span><select v-model="filters.study_mode" class="form-control" @change="applyFilters"><option value="">All study modes</option><option v-for="mode in data.options.study_modes || []" :key="mode" :value="mode">{{ mode }}</option></select></label>
						<label><span>Delivery Mode</span><select v-model="filters.delivery_mode" class="form-control" @change="applyFilters"><option value="">All delivery modes</option><option v-for="mode in data.options.delivery_modes || []" :key="mode" :value="mode">{{ mode }}</option></select></label>
						<label class="eduedge-offering-search"><span>Search</span><input v-model.trim="filters.search" class="form-control" :placeholder="`Title, code or ${programmeSingular.toLowerCase()}`" @keyup.enter="applyFilters" /></label>
					</div>
					<template #actions><button type="button" class="edge-button" @click="clearFilters">Clear</button><button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="applyFilters">{{ loading ? "Loading..." : "Apply" }}</button></template>
				</EdgeFilterBar>

				<section class="session-rule">
					<div><span>Offering identity</span><strong>Branch + {{ programmeSingular }} + {{ academicYearSingular }}</strong></div>
					<div><span>Terms / Semesters</span><strong>Not part of Programme Offering identity</strong></div>
					<div><span>Class Arms</span><strong>Created once per Academic Session</strong></div>
				</section>

				<EdgeDashboardLayout min-column-width="12rem">
					<EdgeStatCard :label="`Matching ${offeringPlural}`" :value="data.summary.total_offerings" :helper="`${data.summary.visible_offerings} on this page`" />
					<EdgeStatCard label="Active" :value="data.summary.active" tone="success" helper="Currently operational" />
					<EdgeStatCard label="Upcoming" :value="data.summary.upcoming" helper="Session start is ahead" />
					<EdgeStatCard label="Full" :value="data.summary.full" :tone="data.summary.full ? 'warning' : 'neutral'" helper="Capacity reached" />
				</EdgeDashboardLayout>

				<p v-if="error && loadedOnce" class="eduedge-offering-error">{{ error }}</p>
				<div class="eduedge-offering-layout">
					<section class="eduedge-offering-panel">
						<div class="eduedge-offering-heading"><div><p class="edge-eyebrow">Session catalogue</p><h2>{{ offeringPlural }}</h2></div><button type="button" class="edge-button" @click="openNativeList">Open native list</button></div>
						<EdgeLoadingState v-if="loading" :message="`Refreshing ${offeringPlural.toLowerCase()}...`" />
						<EdgeEmptyState v-else-if="!data.offerings.length" :title="`No ${offeringPlural.toLowerCase()} found`" :description="`Create a sessional ${offeringSingular} for a permitted Branch and ${academicYearSingular}.`" />
						<div v-else class="eduedge-offering-list">
							<article v-for="row in data.offerings" :key="row.name" class="eduedge-offering-card">
								<button type="button" class="eduedge-offering-main" @click="editOffering(row)">
									<div class="eduedge-offering-title"><span><strong>{{ row.offering_title }}</strong><small>{{ row.offering_code }}</small></span><div class="eduedge-offering-badges"><EdgeStatusBadge :label="row.operational_status" :status="row.operational_status" :tone="statusTone(row.operational_status)" /><EdgeStatusBadge v-if="row.academic_term" label="Legacy Term Offering" status="legacy" tone="warning" /></div></div>
									<div class="eduedge-offering-grid"><span><strong>{{ row.program }}</strong><small>{{ institutionName(row.institution) }} · {{ branchName(row.school_branch) }}</small></span><span><strong>{{ row.academic_year }}</strong><small>{{ row.academic_term ? `Historical · ${row.academic_term}` : "Full Academic Session" }}</small></span><span><strong>{{ row.study_mode }} · {{ row.delivery_mode }}</strong><small>{{ row.student_batch || "No cohort" }}</small></span><span><strong>{{ capacityLabel(row) }}</strong><small>{{ row.occupied_seats }} occupied</small></span></div>
								</button>
								<button type="button" class="edge-button" @click="openFullForm(row.name)">Full form</button>
							</article>
						</div>
						<div class="eduedge-offering-paging"><button type="button" class="edge-button" :disabled="loading || data.paging.start <= 0" @click="previousPage">Previous</button><span>{{ data.paging.start + (data.offerings.length ? 1 : 0) }}–{{ data.paging.start + data.offerings.length }} of {{ data.summary.total_offerings }}</span><button type="button" class="edge-button" :disabled="loading || !data.paging.has_more" @click="nextPage">Next</button></div>
					</section>

					<section class="eduedge-offering-panel eduedge-offering-editor">
						<div class="eduedge-offering-heading"><div><p class="edge-eyebrow">{{ draft.name ? "Session Offering" : "New Session Offering" }}</p><h2>{{ draft.name ? draft.offering_title || offeringSingular : `New ${offeringSingular}` }}</h2></div><button type="button" class="edge-button" @click="newOffering">Reset</button></div>
						<div v-if="legacyDraft" class="legacy-warning"><strong>Historical term-bound Offering</strong><span>This Offering is retained for existing applicants, enrollments, Class Arms and academic history. It cannot be converted in place. Create a sessional Offering for current/future operations.</span></div>
						<EdgeEmptyState v-if="!canCreate && !canWrite" :title="`Read-only ${offeringPlural.toLowerCase()}`" :description="`Your current role can view ${offeringPlural} but cannot create or edit them.`" />
						<template v-else>
							<label><span>Institution</span><select v-model="draft.institution" class="form-control" :disabled="Boolean(draft.name)" @change="draftInstitutionChanged"><option value="">Select Institution</option><option v-for="institution in data.options.institutions || []" :key="institution.name" :value="institution.name">{{ institution.institution_name || institution.name }}</option></select></label>
							<label><span>Branch / Campus</span><select v-model="draft.school_branch" class="form-control" :disabled="Boolean(draft.name) || !draft.institution" @change="draftBranchChanged"><option value="">Select permitted Branch</option><option v-for="branch in draftBranches" :key="branch.name" :value="branch.name">{{ branch.branch_name || branch.name }}</option></select></label>
							<label><span>{{ programmeSingular }}</span><select v-model="draft.program" class="form-control" :disabled="Boolean(draft.name) || !draft.institution" @change="draftProgramChanged"><option value="">Select {{ programmeSingular }}</option><option v-for="programme in draftProgrammes" :key="programme.name" :value="programme.name">{{ programme.program_name || programme.name }}</option></select></label>
							<label><span>{{ academicYearSingular }}</span><select v-model="draft.academic_year" class="form-control" :disabled="Boolean(draft.name) || !draft.institution" @change="draftYearChanged"><option value="">Select {{ academicYearSingular }}</option><option v-for="year in data.options.academic_years || []" :key="year.name" :value="year.name">{{ year.name }}</option></select><small>This Offering automatically covers all Terms / Semesters configured inside the selected Academic Session.</small></label>
							<div class="eduedge-offering-context-readonly"><span>Coverage</span><strong>{{ legacyDraft ? `Historical · ${draft.academic_term}` : "Full Academic Session" }}</strong></div>
							<label><span>Student Batch / Cohort</span><select v-model="draft.student_batch" class="form-control" :disabled="legacyDraft"><option value="">Not assigned</option><option v-for="batch in data.options.student_batches || []" :key="batch.name" :value="batch.name">{{ batch.name }}</option></select></label>
							<div class="eduedge-offering-two-column"><label><span>Study Mode</span><select v-model="draft.study_mode" class="form-control" :disabled="legacyDraft"><option v-for="mode in data.options.study_modes || []" :key="mode" :value="mode">{{ mode }}</option></select></label><label><span>Delivery Mode</span><select v-model="draft.delivery_mode" class="form-control" :disabled="legacyDraft"><option v-for="mode in data.options.delivery_modes || []" :key="mode" :value="mode">{{ mode }}</option></select></label></div>
							<label><span>{{ offeringSingular }} Title</span><input v-model.trim="draft.offering_title" class="form-control" :disabled="legacyDraft" placeholder="Generated when left blank" /></label>
							<label><span>{{ offeringSingular }} Code</span><input v-model.trim="draft.offering_code" class="form-control" :disabled="Boolean(draft.name)" placeholder="Generated when left blank" /></label>
							<div class="eduedge-offering-two-column"><label><span>Start Date</span><input v-model="draft.start_date" type="date" class="form-control" :disabled="legacyDraft" /></label><label><span>End Date</span><input v-model="draft.end_date" type="date" class="form-control" :disabled="legacyDraft" /></label></div>
							<label><span>Capacity</span><input v-model.number="draft.capacity" type="number" min="0" class="form-control" :disabled="legacyDraft" /><small>Zero means no configured limit.</small></label>
							<div class="eduedge-offering-checks"><label><input v-model="draft.is_active" type="checkbox" :disabled="legacyDraft" /> Active</label><label><input v-model="draft.admission_enabled" type="checkbox" :disabled="legacyDraft" /> Admission enabled</label><label><input v-model="draft.enrollment_enabled" type="checkbox" :disabled="legacyDraft" /> Enrollment enabled</label></div>
							<div class="eduedge-offering-two-column"><label><span>Application Opens</span><input v-model="draft.application_start_date" type="date" class="form-control" :disabled="legacyDraft" /></label><label><span>Application Closes</span><input v-model="draft.application_end_date" type="date" class="form-control" :disabled="legacyDraft" /></label></div>
							<label><span>Notes</span><textarea v-model.trim="draft.notes" class="form-control" rows="3" :disabled="legacyDraft"></textarea></label>
							<div class="eduedge-offering-editor-actions"><button v-if="!legacyDraft" type="button" class="edge-button edge-button--primary" :disabled="!canSave || saving" @click="saveOffering">{{ saving ? "Saving..." : `Save ${offeringSingular}` }}</button><button v-if="draft.name" type="button" class="edge-button" @click="openFullForm(draft.name)">Open full form</button></div>
							<p v-if="saveError" class="eduedge-offering-error">{{ saveError }}</p>
						</template>
					</section>
				</div>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const emptyDraft = () => ({ name: "", school_branch: "", institution: "", program: "", department: "", academic_year: "", academic_term: "", student_batch: "", offering_title: "", offering_code: "", study_mode: "Full-Time", delivery_mode: "Onsite", start_date: "", end_date: "", is_active: true, admission_enabled: true, enrollment_enabled: true, capacity: 0, application_start_date: "", application_end_date: "", notes: "" });
const emptyFilters = () => ({ branch: "", institution: "", program: "", academic_year: "", study_mode: "", delivery_mode: "", is_active: "", admission_enabled: "", enrollment_enabled: "", search: "" });
const emptyData = () => ({ active_context: {}, offerings: [], options: { institutions: [], branches: [], programmes: [], academic_years: [], student_batches: [], study_modes: [], delivery_modes: [] }, summary: { total_offerings: 0, visible_offerings: 0, active: 0, upcoming: 0, full: 0 }, paging: { start: 0, page_length: 25, has_more: false, next_start: 0 }, permissions: { can_create: false, can_write: false } });

export default {
	name: "EduEdgeProgrammeOfferings",
	data() { return { loading: true, loadedOnce: false, error: "", saving: false, saveError: "", menuItems: EDUEDGE_MENU_ITEMS, filters: emptyFilters(), draft: emptyDraft(), data: emptyData() }; },
	computed: {
		activeContext() { return this.data.active_context || {}; },
		programmeSingular() { return this.term("programme", false, "Programme / Class"); }, programmePlural() { return this.term("programme", true, "Programmes / Classes"); },
		offeringSingular() { return this.term("programme_offering", false, "Programme Offering"); }, offeringPlural() { return this.term("programme_offering", true, "Programme Offerings"); },
		academicYearSingular() { return this.term("academic_year", false, "Academic Session"); }, academicYearPlural() { return this.term("academic_year", true, "Academic Sessions"); },
		canCreate() { return Boolean(this.data.permissions.can_create); }, canWrite() { return Boolean(this.data.permissions.can_write); },
		legacyDraft() { return Boolean(this.draft.name && this.draft.academic_term); },
		canSave() { const permitted = this.draft.name ? this.canWrite : this.canCreate; return Boolean(!this.legacyDraft && permitted && this.draft.institution && this.draft.school_branch && this.draft.program && this.draft.academic_year); },
		filterBranches() { return this.filters.institution ? (this.data.options.branches || []).filter((row) => row.institution === this.filters.institution) : (this.data.options.branches || []); },
		filterProgrammes() { return this.filters.institution ? (this.data.options.programmes || []).filter((row) => !row.eduedge_institution || row.eduedge_institution === this.filters.institution) : (this.data.options.programmes || []); },
		draftBranches() { return this.draft.institution ? (this.data.options.branches || []).filter((row) => row.institution === this.draft.institution) : []; },
		draftProgrammes() { return this.draft.institution ? (this.data.options.programmes || []).filter((row) => !row.eduedge_institution || row.eduedge_institution === this.draft.institution) : []; },
	},
	mounted() { this.load(true, true); },
	methods: {
		openRoute: openEduEdgeRoute,
		term(key, plural = false, fallback = "") { return frappe.eduedge?.term?.(key, { plural, context: this.activeContext, fallback }) || fallback; },
		institutionName(name) { return (this.data.options.institutions || []).find((row) => row.name === name)?.institution_name || name || "Unknown Institution"; },
		branchName(name) { return (this.data.options.branches || []).find((row) => row.name === name)?.branch_name || name || "Unknown Branch"; },
		statusTone(status) { if (status === "Active") return "success"; if (["Full", "Upcoming"].includes(status)) return "warning"; if (["Closed", "Disabled"].includes(status)) return "danger"; return "neutral"; },
		capacityLabel(row) { return Number(row.capacity || 0) ? `${row.seats_remaining} of ${row.capacity} seats left` : "No capacity limit"; },
		async load(resetStart = false, useActiveBranch = false) { if (resetStart) this.data.paging.start = 0; this.loading = true; this.error = ""; try { const response = await frappe.call("eduedge.api.programme_offerings.get_programme_offerings_page", { ...this.filters, use_active_branch: useActiveBranch ? 1 : 0, start: this.data.paging.start || 0, page_length: this.data.paging.page_length || 25 }); this.data = response.message || emptyData(); this.filters = { ...this.filters, ...(this.data.filters || {}) }; this.loadedOnce = true; if (!this.draft.institution) this.draft.institution = this.filters.institution || this.activeContext.institution || ""; if (!this.draft.school_branch) this.draft.school_branch = this.filters.branch || this.activeContext.branch || ""; } catch (error) { this.error = error?.message || `${this.offeringPlural} could not be loaded.`; } finally { this.loading = false; } },
		applyFilters() { this.load(true, false); },
		async filterInstitutionChanged() { this.filters.branch = ""; this.filters.program = ""; this.filters.academic_year = ""; await this.load(true, false); },
		async filterBranchChanged() { this.filters.program = ""; this.filters.academic_year = ""; await this.load(true, false); },
		filterYearChanged() { this.load(true, false); },
		async clearFilters() { this.filters = emptyFilters(); await this.load(true, false); },
		previousPage() { this.data.paging.start = Math.max(0, this.data.paging.start - this.data.paging.page_length); this.load(false, false); },
		nextPage() { if (this.data.paging.has_more) { this.data.paging.start = this.data.paging.next_start; this.load(false, false); } },
		newOffering() { this.saveError = ""; this.draft = { ...emptyDraft(), institution: this.filters.institution || this.activeContext.institution || "", school_branch: this.filters.branch || this.activeContext.branch || "" }; },
		editOffering(row) { this.saveError = ""; this.draft = { ...emptyDraft(), ...row, is_active: Boolean(row.is_active), admission_enabled: Boolean(row.admission_enabled), enrollment_enabled: Boolean(row.enrollment_enabled) }; },
		draftInstitutionChanged() { this.draft.school_branch = ""; this.draft.program = ""; this.draft.academic_year = ""; this.draft.student_batch = ""; },
		draftBranchChanged() { this.draft.program = ""; this.draft.academic_year = ""; this.draft.student_batch = ""; },
		draftProgramChanged() { const programme = this.draftProgrammes.find((row) => row.name === this.draft.program); this.draft.department = programme?.department || ""; },
		draftYearChanged() { /* Terms are deliberately not part of Offering identity. */ },
		async saveOffering() { if (!this.canSave) return; this.saving = true; this.saveError = ""; try { const response = await frappe.call({ method: "eduedge.api.programme_offerings.save_programme_offering", type: "POST", args: { offering: this.draft.name || undefined, school_branch: this.draft.school_branch, program: this.draft.program, academic_year: this.draft.academic_year, student_batch: this.draft.student_batch || undefined, offering_title: this.draft.offering_title || undefined, offering_code: this.draft.offering_code || undefined, study_mode: this.draft.study_mode, delivery_mode: this.draft.delivery_mode, start_date: this.draft.start_date || undefined, end_date: this.draft.end_date || undefined, is_active: this.draft.is_active ? 1 : 0, admission_enabled: this.draft.admission_enabled ? 1 : 0, enrollment_enabled: this.draft.enrollment_enabled ? 1 : 0, capacity: this.draft.capacity || 0, application_start_date: this.draft.application_start_date || undefined, application_end_date: this.draft.application_end_date || undefined, notes: this.draft.notes || undefined } }); frappe.show_alert({ message: __(`${this.offeringSingular} saved for the Academic Session`), indicator: "green" }); await this.load(true, false); const row = this.data.offerings.find((item) => item.name === response.message?.name); if (row) this.editOffering(row); else this.newOffering(); } catch (error) { this.saveError = error?.message || `${this.offeringSingular} could not be saved.`; } finally { this.saving = false; } },
		openFullForm(name) { if (name) frappe.set_route("Form", "EduEdge Program Offering", name); }, openNativeList() { window.open("/app/eduedge-program-offering", "_blank", "noopener,noreferrer"); },
	},
};
</script>

<style scoped>
.eduedge-offering-filter-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(12rem,1fr)); gap:.75rem; width:100%; }.eduedge-offering-filter-grid label,.eduedge-offering-editor label { display:grid; gap:.35rem; font-weight:600; }.eduedge-offering-search { grid-column:span 2; }.session-rule { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.75rem; margin:1rem 0; }.session-rule>div { display:grid; gap:.2rem; padding:.8rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); }.session-rule span { color:var(--text-muted); font-size:.78rem; }.eduedge-offering-layout { display:grid; grid-template-columns:minmax(0,1.55fr) minmax(20rem,.85fr); gap:1rem; margin-top:1rem; }.eduedge-offering-panel { display:grid; gap:1rem; align-content:start; padding:1rem; border:1px solid var(--border-color); border-radius:12px; background:var(--card-bg); }.eduedge-offering-heading,.eduedge-offering-title { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; }.eduedge-offering-heading h2 { margin:0; }.eduedge-offering-list { display:grid; gap:.75rem; }.eduedge-offering-card { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:.75rem; align-items:center; padding:.85rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); }.eduedge-offering-main { display:grid; gap:.75rem; width:100%; padding:0; border:0; background:transparent; text-align:left; }.eduedge-offering-title>span,.eduedge-offering-grid span,.eduedge-offering-context-readonly { display:grid; gap:.2rem; }.eduedge-offering-title small,.eduedge-offering-grid small,.eduedge-offering-editor small { color:var(--text-muted); }.eduedge-offering-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.75rem; }.eduedge-offering-badges,.eduedge-offering-editor-actions,.eduedge-offering-checks { display:flex; flex-wrap:wrap; gap:.5rem; }.eduedge-offering-two-column { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; }.eduedge-offering-checks label { display:flex; align-items:center; gap:.4rem; font-weight:500; }.eduedge-offering-paging { display:flex; justify-content:space-between; align-items:center; gap:.75rem; }.legacy-warning { display:grid; gap:.25rem; padding:.75rem; border:1px solid var(--orange-300,#f4b860); border-radius:8px; background:var(--control-bg); }.eduedge-offering-error { margin:0; color:var(--red-600,#b42318); } @media (max-width:1100px) { .eduedge-offering-layout { grid-template-columns:1fr; }.eduedge-offering-grid,.session-rule { grid-template-columns:repeat(2,minmax(0,1fr)); } } @media (max-width:700px) { .eduedge-offering-search { grid-column:auto; }.eduedge-offering-card,.eduedge-offering-grid,.eduedge-offering-two-column,.session-rule { grid-template-columns:1fr; }.eduedge-offering-heading,.eduedge-offering-title,.eduedge-offering-paging { align-items:stretch; flex-direction:column; } }
</style>
