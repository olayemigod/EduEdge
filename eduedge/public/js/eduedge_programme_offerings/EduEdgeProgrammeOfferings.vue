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
					eyebrow="Academic Delivery"
					:title="offeringPlural"
					:subtitle="`Open a ${programmeSingular} for a Branch, ${academicYearSingular}, ${academicTermSingular}, cohort, delivery mode, and capacity. ${departmentSingular} is inherited from the ${programmeSingular}.`"
					:action-label="canCreate ? `New ${offeringSingular}` : ''"
					@action="newOffering"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loadedOnce" :message="`Loading ${offeringPlural.toLowerCase()}...`" :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loadedOnce" :title="`${offeringPlural} could not load`" :message="error" action-label="Try again" @retry="load(true)" />
			<template v-else>
				<EdgeFilterBar title="Offering filters">
					<div class="eduedge-offering-filter-grid">
						<label><span>Branch / Campus</span><select v-model="filters.branch" class="form-control" @change="filterBranchChanged"><option value="">Current active Branch</option><option v-for="branch in data.options.branches" :key="branch.name" :value="branch.name">{{ branch.branch_name || branch.name }}</option></select></label>
						<label><span>{{ departmentSingular }}</span><select v-model="filters.department" class="form-control" @change="filterDepartmentChanged"><option value="">All {{ departmentPlural.toLowerCase() }}</option><option v-for="department in data.options.departments" :key="department.name" :value="department.name">{{ department.department_name || department.name }}</option></select></label>
						<label><span>{{ programmeSingular }}</span><select v-model="filters.program" class="form-control" @change="applyFilters"><option value="">All {{ programmePlural.toLowerCase() }}</option><option v-for="programme in filterProgrammes" :key="programme.name" :value="programme.name">{{ programme.program_name || programme.name }}</option></select></label>
						<label><span>{{ academicYearSingular }}</span><select v-model="filters.academic_year" class="form-control" @change="filterYearChanged"><option value="">All {{ academicYearPlural.toLowerCase() }}</option><option v-for="year in data.options.academic_years" :key="year.name" :value="year.name">{{ year.name }}</option></select></label>
						<label><span>{{ academicTermSingular }}</span><select v-model="filters.academic_term" class="form-control" @change="applyFilters"><option value="">All {{ academicTermPlural.toLowerCase() }}</option><option v-for="term in data.options.academic_terms" :key="term.name" :value="term.name">{{ term.name }}</option></select></label>
						<label><span>Status</span><select v-model="filters.is_active" class="form-control" @change="applyFilters"><option value="">Active and disabled</option><option value="1">Active only</option><option value="0">Disabled only</option></select></label>
						<label><span>Study Mode</span><select v-model="filters.study_mode" class="form-control" @change="applyFilters"><option value="">All study modes</option><option v-for="mode in data.options.study_modes" :key="mode" :value="mode">{{ mode }}</option></select></label>
						<label><span>Delivery Mode</span><select v-model="filters.delivery_mode" class="form-control" @change="applyFilters"><option value="">All delivery modes</option><option v-for="mode in data.options.delivery_modes" :key="mode" :value="mode">{{ mode }}</option></select></label>
						<label class="eduedge-offering-search"><span>Search</span><input v-model.trim="filters.search" class="form-control" placeholder="Title, code, programme or department" @keyup.enter="applyFilters" /></label>
					</div>
					<template #actions><button type="button" class="edge-button" @click="clearFilters">Clear</button><button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="applyFilters">{{ loading ? "Loading..." : "Apply" }}</button></template>
				</EdgeFilterBar>

				<EdgeDashboardLayout min-column-width="12rem">
					<EdgeStatCard label="Matching Offerings" :value="data.summary.total_offerings" :helper="`${data.summary.visible_offerings} on this page`" />
					<EdgeStatCard label="Active" :value="data.summary.active" tone="success" helper="Currently operational" />
					<EdgeStatCard label="Upcoming" :value="data.summary.upcoming" helper="Start date is ahead" />
					<EdgeStatCard label="Full" :value="data.summary.full" :tone="data.summary.full ? 'warning' : 'neutral'" helper="Capacity reached" />
					<EdgeStatCard label="Occupied Seats" :value="data.summary.occupied_seats" :helper="capacitySummary" />
				</EdgeDashboardLayout>

				<p v-if="error && loadedOnce" class="eduedge-offering-error">{{ error }}</p>
				<div class="eduedge-offering-layout">
					<section class="eduedge-offering-panel">
						<div class="eduedge-offering-heading"><div><p class="edge-eyebrow">Delivery catalogue</p><h2>{{ offeringPlural }}</h2></div><button type="button" class="edge-button" @click="openNativeList">Open native list</button></div>
						<EdgeLoadingState v-if="loading" :message="`Refreshing ${offeringPlural.toLowerCase()}...`" />
						<EdgeEmptyState v-else-if="!data.offerings.length" :title="`No ${offeringPlural.toLowerCase()} found`" description="Change the filters or create the first Branch-specific Offering." />
						<div v-else class="eduedge-offering-list">
							<article v-for="row in data.offerings" :key="row.name" class="eduedge-offering-card">
								<button type="button" class="eduedge-offering-main" @click="editOffering(row)">
									<div class="eduedge-offering-title"><span><strong>{{ row.offering_title }}</strong><small>{{ row.offering_code }}</small></span><div class="eduedge-offering-badges"><EdgeStatusBadge :label="row.operational_status" :status="row.operational_status" :tone="statusTone(row.operational_status)" /><EdgeStatusBadge v-if="row.identity_locked" label="Identity locked" status="locked" tone="warning" /></div></div>
									<div class="eduedge-offering-grid">
										<span><strong>{{ row.program_display_name || row.program }}</strong><small>{{ row.department_display_name || departmentName(row.department) }}</small></span>
										<span><strong>{{ row.academic_year }}</strong><small>{{ row.academic_term || `${academicYearSingular}-wide` }}</small></span>
										<span><strong>{{ row.study_mode }} · {{ row.delivery_mode }}</strong><small>{{ row.student_batch_display_name || row.student_batch || "No cohort" }}</small></span>
										<span><strong>{{ capacityLabel(row) }}</strong><small>{{ row.occupied_seats }} occupied · {{ branchName(row.school_branch) }}</small></span>
									</div>
									<div class="eduedge-offering-badges"><EdgeStatusBadge :label="row.admission_status" status="admission" :tone="row.application_open ? 'success' : 'neutral'" /><EdgeStatusBadge :label="row.enrollment_status" status="enrollment" :tone="row.enrollment_open ? 'success' : 'neutral'" /><EdgeStatusBadge :label="dateRange(row)" status="dates" tone="neutral" /></div>
								</button>
								<button type="button" class="edge-button" @click="openFullForm(row.name)">Full form</button>
							</article>
						</div>
						<div class="eduedge-offering-paging"><button type="button" class="edge-button" :disabled="loading || data.paging.start <= 0" @click="previousPage">Previous</button><span>{{ data.paging.start + (data.offerings.length ? 1 : 0) }}–{{ data.paging.start + data.offerings.length }} of {{ data.summary.total_offerings }}</span><button type="button" class="edge-button" :disabled="loading || !data.paging.has_more" @click="nextPage">Next</button></div>
					</section>

					<section class="eduedge-offering-panel eduedge-offering-editor">
						<div class="eduedge-offering-heading"><div><p class="edge-eyebrow">{{ draft.name ? "Quick edit" : "Quick create" }}</p><h2>{{ draft.name ? draft.offering_title || offeringSingular : `New ${offeringSingular}` }}</h2></div><button type="button" class="edge-button" @click="newOffering">Reset</button></div>
						<EdgeEmptyState v-if="!canCreate && !canWrite" title="Read-only offerings" description="Your current role can view Offerings but cannot create or edit them." />
						<template v-else>
							<p v-if="draft.identity_locked" class="eduedge-offering-lock-note">This Offering is already referenced by an Applicant, Student Group, or submitted Enrollment. Create a new Offering to change its identity.</p>
							<label><span>Branch / Campus</span><select v-model="draft.school_branch" class="form-control" :disabled="draft.identity_locked" @change="draftBranchChanged"><option value="">Select Branch</option><option v-for="branch in draftOptions.branches" :key="branch.name" :value="branch.name">{{ branch.branch_name || branch.name }}</option></select></label>
							<div class="eduedge-offering-context-readonly"><span>Institution</span><strong>{{ draftInstitutionName }}</strong></div>
							<label><span>{{ programmeSingular }}</span><select v-model="draft.program" class="form-control" :disabled="draft.identity_locked" @change="draftProgramChanged"><option value="">Select {{ programmeSingular }}</option><option v-for="programme in draftOptions.programmes" :key="programme.name" :value="programme.name">{{ programme.program_name || programme.name }}</option></select></label>
							<div class="eduedge-offering-context-readonly"><span>{{ departmentSingular }}</span><strong>{{ draftDepartmentName }}</strong></div>
							<div class="eduedge-offering-two-column"><label><span>{{ academicYearSingular }}</span><select v-model="draft.academic_year" class="form-control" :disabled="draft.identity_locked" @change="draftYearChanged"><option value="">Select {{ academicYearSingular.toLowerCase() }}</option><option v-for="year in draftOptions.academic_years" :key="year.name" :value="year.name">{{ year.name }}</option></select></label><label><span>{{ academicTermSingular }}</span><select v-model="draft.academic_term" class="form-control" :disabled="draft.identity_locked"><option value="">{{ academicYearSingular }}-wide</option><option v-for="term in draftOptions.academic_terms" :key="term.name" :value="term.name">{{ term.name }}</option></select></label></div>
							<label><span>{{ studentBatchSingular }}</span><select v-model="draft.student_batch" class="form-control" :disabled="draft.identity_locked"><option value="">Not assigned</option><option v-for="batch in draftOptions.student_batches" :key="batch.name" :value="batch.name">{{ batch.display_name || batch.name }}</option></select></label>
							<div class="eduedge-offering-two-column"><label><span>Study Mode</span><select v-model="draft.study_mode" class="form-control" :disabled="draft.identity_locked"><option v-for="mode in draftOptions.study_modes" :key="mode" :value="mode">{{ mode }}</option></select></label><label><span>Delivery Mode</span><select v-model="draft.delivery_mode" class="form-control" :disabled="draft.identity_locked"><option v-for="mode in draftOptions.delivery_modes" :key="mode" :value="mode">{{ mode }}</option></select></label></div>
							<label><span>Offering Title</span><input v-model.trim="draft.offering_title" class="form-control" placeholder="Generated when left blank" /></label>
							<label><span>Offering Code</span><input v-model.trim="draft.offering_code" class="form-control" :disabled="Boolean(draft.name)" placeholder="Generated when left blank" /></label>
							<div class="eduedge-offering-two-column"><label><span>Start Date</span><input v-model="draft.start_date" type="date" class="form-control" /></label><label><span>End Date</span><input v-model="draft.end_date" type="date" class="form-control" /></label></div>
							<label><span>Capacity</span><input v-model.number="draft.capacity" type="number" min="0" class="form-control" /><small>Zero means no configured limit.</small></label>
							<div class="eduedge-offering-checks"><label><input v-model="draft.is_active" type="checkbox" /> Active</label><label><input v-model="draft.admission_enabled" type="checkbox" /> Admission enabled</label><label><input v-model="draft.enrollment_enabled" type="checkbox" /> Enrollment enabled</label></div>
							<div class="eduedge-offering-two-column"><label><span>Application Opens</span><input v-model="draft.application_start_date" type="date" class="form-control" /></label><label><span>Application Closes</span><input v-model="draft.application_end_date" type="date" class="form-control" /></label></div>
							<label><span>Notes</span><textarea v-model.trim="draft.notes" class="form-control" rows="3"></textarea></label>
							<div class="eduedge-offering-editor-actions"><button type="button" class="edge-button edge-button--primary" :disabled="!canSave || saving" @click="saveOffering">{{ saving ? "Saving..." : `Save ${offeringSingular}` }}</button><button v-if="draft.name" type="button" class="edge-button" @click="openFullForm(draft.name)">Open full form</button></div>
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

const emptyDraft = () => ({ name: "", school_branch: "", institution: "", program: "", department: "", academic_year: "", academic_term: "", student_batch: "", offering_title: "", offering_code: "", study_mode: "Full-Time", delivery_mode: "Onsite", start_date: "", end_date: "", is_active: true, admission_enabled: true, enrollment_enabled: true, capacity: 0, application_start_date: "", application_end_date: "", notes: "", identity_locked: false });
const emptyOptions = () => ({ branches: [], programmes: [], departments: [], academic_years: [], academic_terms: [], student_batches: [], study_modes: ["Full-Time", "Part-Time", "Weekend", "Evening", "Short Course", "Flexible"], delivery_modes: ["Onsite", "Online", "Hybrid"] });

export default {
	name: "EduEdgeProgrammeOfferings",
	data() { return { loading: true, loadedOnce: false, error: "", saving: false, saveError: "", menuItems: EDUEDGE_MENU_ITEMS, filters: { branch: "", institution: "", program: "", department: "", academic_year: "", academic_term: "", student_batch: "", study_mode: "", delivery_mode: "", is_active: "", admission_enabled: "", enrollment_enabled: "", search: "" }, draft: emptyDraft(), draftOptions: emptyOptions(), data: { active_context: {}, offerings: [], options: emptyOptions(), summary: { total_offerings: 0, visible_offerings: 0, active: 0, upcoming: 0, full: 0, closed_or_disabled: 0, occupied_seats: 0, configured_capacity: 0 }, paging: { start: 0, page_length: 25, has_more: false, next_start: 0 }, permissions: { can_create: false, can_write: false } } }; },
	computed: {
		activeContext() { return this.data.active_context || {}; }, programmeSingular() { return this.term("programme", false, "Programme"); }, programmePlural() { return this.term("programme", true, "Programmes"); }, offeringSingular() { return this.term("programme_offering", false, "Programme Offering"); }, offeringPlural() { return this.term("programme_offering", true, "Programme Offerings"); }, departmentSingular() { return this.term("department", false, "Department / School Section"); }, departmentPlural() { return this.term("department", true, "Departments / School Sections"); }, academicYearSingular() { return this.term("academic_year", false, "Academic Session"); }, academicYearPlural() { return this.term("academic_year", true, "Academic Sessions"); }, academicTermSingular() { return this.term("academic_term", false, "Term / Semester"); }, academicTermPlural() { return this.term("academic_term", true, "Terms / Semesters"); }, studentBatchSingular() { return this.term("student_batch", false, "Cohort / Batch"); }, canCreate() { return Boolean(this.data.permissions.can_create); }, canWrite() { return Boolean(this.data.permissions.can_write); }, canSave() { const permitted = this.draft.name ? this.canWrite : this.canCreate; return Boolean(permitted && this.draft.school_branch && this.draft.program && this.draft.academic_year); }, capacitySummary() { return this.data.summary.configured_capacity ? `${this.data.summary.configured_capacity} configured capacity` : "No limits across visible records"; }, filterProgrammes() { return this.filters.department ? this.data.options.programmes.filter((row) => row.department === this.filters.department) : this.data.options.programmes; }, draftInstitutionName() { const branch = this.draftOptions.branches.find((row) => row.name === this.draft.school_branch); return branch?.institution_name || this.draft.institution || "Select a Branch"; }, draftDepartmentName() { const programme = this.draftOptions.programmes.find((row) => row.name === this.draft.program); return this.departmentName(programme?.department || this.draft.department); },
	},
	mounted() { this.load(true); },
	methods: {
		openRoute: openEduEdgeRoute,
		term(key, plural = false, fallback = "") { return frappe.eduedge?.term?.(key, { plural, context: this.activeContext, fallback }) || fallback; },
		branchName(name) { return this.data.options.branches.find((row) => row.name === name)?.branch_name || name || "Unknown Branch"; },
		departmentName(name) { return this.data.options.departments.find((row) => row.name === name)?.department_name || this.draftOptions.departments.find((row) => row.name === name)?.department_name || name || `No ${this.departmentSingular}`; },
		statusTone(status) { if (status === "Active") return "success"; if (["Full", "Upcoming"].includes(status)) return "warning"; if (["Closed", "Disabled"].includes(status)) return "danger"; return "neutral"; },
		formatDate(value) { return value ? frappe.datetime.str_to_user(value) : ""; }, dateRange(row) { const start = this.formatDate(row.start_date); const end = this.formatDate(row.end_date); return start && end ? `${start} – ${end}` : start || end || "Dates not set"; }, capacityLabel(row) { return Number(row.capacity || 0) ? `${row.seats_remaining} of ${row.capacity} seats left` : "No capacity limit"; },
		async load(resetStart = false) { if (resetStart) this.data.paging.start = 0; this.loading = true; this.error = ""; try { const response = await frappe.call("eduedge.api.programme_offerings.get_programme_offerings_page", { ...this.filters, start: this.data.paging.start || 0, page_length: this.data.paging.page_length || 25 }); this.data = response.message || this.data; this.filters = { ...this.filters, ...(this.data.filters || {}) }; if (!this.draft.school_branch) { this.draft.school_branch = this.filters.branch || ""; this.draft.institution = this.filters.institution || ""; } if (!this.draftOptions.branches.length) this.draftOptions = JSON.parse(JSON.stringify(this.data.options)); this.loadedOnce = true; } catch (error) { this.error = error?.message || `${this.offeringPlural} could not be loaded.`; } finally { this.loading = false; } },
		applyFilters() { this.load(true); }, filterBranchChanged() { this.filters.institution = ""; this.filters.department = ""; this.filters.program = ""; this.filters.student_batch = ""; this.newOffering(); this.load(true); }, filterDepartmentChanged() { if (!this.filterProgrammes.some((row) => row.name === this.filters.program)) this.filters.program = ""; this.load(true); }, filterYearChanged() { this.filters.academic_term = ""; this.load(true); }, clearFilters() { this.filters = { branch: "", institution: "", program: "", department: "", academic_year: "", academic_term: "", student_batch: "", study_mode: "", delivery_mode: "", is_active: "", admission_enabled: "", enrollment_enabled: "", search: "" }; this.newOffering(); this.load(true); }, previousPage() { this.data.paging.start = Math.max(0, this.data.paging.start - this.data.paging.page_length); this.load(false); }, nextPage() { if (this.data.paging.has_more) { this.data.paging.start = this.data.paging.next_start; this.load(false); } },
		async newOffering() { this.draft = { ...emptyDraft(), school_branch: this.filters.branch || "", institution: this.filters.institution || "" }; this.saveError = ""; await this.loadDraftOptions(); }, async editOffering(row) { this.draft = { ...emptyDraft(), ...row, is_active: Boolean(row.is_active), admission_enabled: Boolean(row.admission_enabled), enrollment_enabled: Boolean(row.enrollment_enabled), identity_locked: Boolean(row.identity_locked) }; this.saveError = ""; await this.loadDraftOptions(); },
		async loadDraftOptions() { try { const response = await frappe.call("eduedge.api.programme_offerings.get_programme_offering_options", { branch: this.draft.school_branch || undefined, academic_year: this.draft.academic_year || undefined }); const result = response.message || {}; this.draftOptions = result.options || emptyOptions(); this.draft.institution = result.institution || this.draft.institution || ""; this.draftProgramChanged(); } catch (error) { this.saveError = error?.message || "Offering options could not be loaded."; } },
		async draftBranchChanged() { this.draft.program = ""; this.draft.department = ""; this.draft.academic_year = ""; this.draft.academic_term = ""; this.draft.student_batch = ""; await this.loadDraftOptions(); }, draftProgramChanged() { const programme = this.draftOptions.programmes.find((row) => row.name === this.draft.program); this.draft.department = programme?.department || ""; }, async draftYearChanged() { this.draft.academic_term = ""; await this.loadDraftOptions(); },
		async saveOffering() { if (!this.canSave) return; this.saving = true; this.saveError = ""; try { const response = await frappe.call("eduedge.api.programme_offerings.save_programme_offering", { offering: this.draft.name || undefined, school_branch: this.draft.school_branch, program: this.draft.program, academic_year: this.draft.academic_year, academic_term: this.draft.academic_term || undefined, student_batch: this.draft.student_batch || undefined, offering_title: this.draft.offering_title || undefined, offering_code: this.draft.offering_code || undefined, study_mode: this.draft.study_mode, delivery_mode: this.draft.delivery_mode, start_date: this.draft.start_date || undefined, end_date: this.draft.end_date || undefined, is_active: this.draft.is_active ? 1 : 0, admission_enabled: this.draft.admission_enabled ? 1 : 0, enrollment_enabled: this.draft.enrollment_enabled ? 1 : 0, capacity: this.draft.capacity || 0, application_start_date: this.draft.application_start_date || undefined, application_end_date: this.draft.application_end_date || undefined, notes: this.draft.notes || undefined }); frappe.show_alert({ message: __(`${this.offeringSingular} saved`), indicator: "green" }); await this.load(true); const row = this.data.offerings.find((item) => item.name === response.message?.name); if (row) await this.editOffering(row); else await this.newOffering(); } catch (error) { this.saveError = error?.message || `${this.offeringSingular} could not be saved.`; } finally { this.saving = false; } },
		openFullForm(name) { if (name) frappe.set_route("Form", "EduEdge Program Offering", name); }, openNativeList() { window.open("/app/eduedge-program-offering", "_blank", "noopener,noreferrer"); },
	},
};
</script>

<style scoped>
.eduedge-offering-filter-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(12rem,1fr)); gap:.75rem; width:100%; }
.eduedge-offering-filter-grid label,.eduedge-offering-editor label { display:grid; gap:.35rem; font-weight:600; }
.eduedge-offering-search { grid-column:span 2; }
.eduedge-offering-layout { display:grid; grid-template-columns:minmax(0,1.55fr) minmax(20rem,.85fr); gap:1rem; margin-top:1rem; }
.eduedge-offering-panel { display:grid; gap:1rem; align-content:start; padding:1rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.eduedge-offering-heading,.eduedge-offering-title { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; }
.eduedge-offering-heading h2 { margin:0; }
.eduedge-offering-list { display:grid; gap:.75rem; }
.eduedge-offering-card { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:.75rem; align-items:center; padding:.85rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.eduedge-offering-main { display:grid; gap:.75rem; width:100%; padding:0; border:0; background:transparent; text-align:left; }
.eduedge-offering-title>span,.eduedge-offering-grid span,.eduedge-offering-context-readonly { display:grid; gap:.2rem; }
.eduedge-offering-title small,.eduedge-offering-grid small,.eduedge-offering-editor small { color:var(--text-muted); }
.eduedge-offering-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.75rem; }
.eduedge-offering-badges,.eduedge-offering-editor-actions,.eduedge-offering-checks { display:flex; flex-wrap:wrap; gap:.5rem; }
.eduedge-offering-two-column { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; }
.eduedge-offering-checks label { display:flex; align-items:center; gap:.4rem; font-weight:500; }
.eduedge-offering-paging { display:flex; justify-content:space-between; align-items:center; gap:.75rem; }
.eduedge-offering-lock-note { padding:.75rem; border:1px solid var(--orange-300,#f4b860); border-radius:var(--edge-radius-md,8px); background:var(--orange-50,#fff7e8); }
.eduedge-offering-error { margin:0; color:var(--red-600,#b42318); }
@media (max-width:1100px) { .eduedge-offering-layout { grid-template-columns:1fr; } .eduedge-offering-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media (max-width:700px) { .eduedge-offering-search { grid-column:auto; } .eduedge-offering-card,.eduedge-offering-grid,.eduedge-offering-two-column { grid-template-columns:1fr; } .eduedge-offering-heading,.eduedge-offering-title,.eduedge-offering-paging { align-items:stretch; flex-direction:column; } }
</style>
