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
					:subtitle="`Maintain the native ${departmentSingular} → ${programmeSingular} structure. Select a Class to review and safely extend its curriculum.`"
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
					<section class="eduedge-programme-panel eduedge-programme-catalogue">
						<div class="eduedge-programme-panel-heading">
							<div><p class="edge-eyebrow">Catalogue</p><h2>{{ programmePlural }}</h2></div>
							<button type="button" class="edge-button" @click="openNativeList">Open native list</button>
						</div>
						<EdgeLoadingState v-if="loading" :message="`Refreshing ${programmePlural.toLowerCase()}...`" />
						<EdgeEmptyState v-else-if="!data.programmes.length" :title="`No ${programmePlural.toLowerCase()} found`" :description="`Create a ${departmentSingular} first, then create the ${programmeSingular} beneath it.`" />
						<div v-else class="eduedge-programme-list">
							<article
								v-for="row in data.programmes"
								:key="row.name"
								class="eduedge-programme-row"
								:class="{ 'is-selected': selectedProgramme?.name === row.name }"
							>
								<button type="button" class="eduedge-programme-main" @click="selectProgramme(row)">
									<span class="eduedge-programme-title"><strong>{{ row.program_name || row.name }}</strong><small>{{ row.program_abbreviation || row.name }}</small></span>
									<span class="eduedge-programme-context">{{ institutionName(row.eduedge_institution) }}<small>{{ departmentName(row.department) }}</small></span>
									<span class="eduedge-programme-counts">
										<EdgeStatusBadge :label="`${row.course_count} ${coursePlural.toLowerCase()} row(s)`" status="courses" tone="neutral" />
										<EdgeStatusBadge :label="`${row.active_offering_count} active ${offeringPlural.toLowerCase()}`" status="offerings" :tone="row.active_offering_count ? 'success' : 'neutral'" />
									</span>
								</button>
								<button v-if="canWrite" type="button" class="edge-button eduedge-programme-edit-button" @click.stop="editProgramme(row)">Edit</button>
							</article>
						</div>
						<div class="eduedge-programme-paging">
							<button type="button" class="edge-button" :disabled="loading || data.paging.start <= 0" @click="previousPage">Previous</button>
							<span>{{ data.paging.start + (data.programmes.length ? 1 : 0) }}–{{ data.paging.start + data.programmes.length }} of {{ data.summary.total_programmes }}</span>
							<button type="button" class="edge-button" :disabled="loading || !data.paging.has_more" @click="nextPage">Next</button>
						</div>
					</section>

					<section ref="curriculumPanel" class="eduedge-programme-panel eduedge-programme-curriculum-manager">
						<EdgeEmptyState
							v-if="!selectedProgramme"
							title="Select a Class"
							:description="`Choose a ${programmeSingular.toLowerCase()} from the catalogue to review its ${coursePlural.toLowerCase()}, add Institution subjects and open active intakes.`"
						/>
						<template v-else>
							<div class="eduedge-programme-panel-heading">
								<div>
									<p class="edge-eyebrow">Curriculum manager</p>
									<h2>{{ selectedProgramme.program_name || selectedProgramme.name }}</h2>
									<small>{{ institutionName(selectedProgramme.eduedge_institution) }} · {{ departmentName(selectedProgramme.department) }}</small>
								</div>
								<div class="eduedge-programme-heading-actions">
									<button v-if="canWrite" type="button" class="edge-button" @click="editProgramme(selectedProgramme)">Edit Class</button>
									<button type="button" class="edge-button" :disabled="curriculumLoading" @click="loadCurriculum(selectedProgramme.name)">{{ curriculumLoading ? "Refreshing..." : "Refresh" }}</button>
								</div>
							</div>

							<EdgeLoadingState v-if="curriculumLoading" :message="`Loading ${curriculumCoursePlural.toLowerCase()}...`" />
							<p v-else-if="curriculumError" class="eduedge-programme-error">{{ curriculumError }}</p>
							<template v-else>
								<div class="eduedge-programme-curriculum-stats">
									<span><strong>{{ curriculum.configured_courses.length }}</strong><small>Configured {{ curriculumCoursePlural }}</small></span>
									<span><strong>{{ curriculum.active_offerings.length }}</strong><small>Active {{ offeringPlural }}</small></span>
								</div>

								<div class="eduedge-programme-curriculum-controls">
									<label>
										<span>Search curriculum</span>
										<input v-model.trim="curriculumSearch" class="form-control" :placeholder="`Search ${curriculumCoursePlural.toLowerCase()}, department or grading scale`" />
									</label>
									<label>
										<span>View</span>
										<select v-model="curriculumView" class="form-control">
											<option value="all">All curriculum</option>
											<option value="configured">Configured only</option>
											<option value="available">Available to add</option>
										</select>
									</label>
								</div>

								<p class="eduedge-programme-governance-note">{{ curriculum.governance_note }}</p>

								<section v-if="showConfiguredCourses" class="eduedge-programme-curriculum-section">
									<div class="eduedge-programme-section-heading">
										<div><strong>Configured {{ curriculumCoursePlural }}</strong><small>{{ filteredConfiguredCourses.length }} of {{ curriculum.configured_courses.length }} shown</small></div>
									</div>
									<EdgeEmptyState
										v-if="!filteredConfiguredCourses.length"
										:title="curriculum.configured_courses.length ? 'No configured subject matches the search' : `No ${curriculumCoursePlural.toLowerCase()} configured`"
										:description="curriculum.configured_courses.length ? 'Clear the search or change the view filter.' : `Add an Institution ${curriculumCourseSingular.toLowerCase()} below. Instructor Assignment additions will also appear here.`"
									/>
									<div v-else class="eduedge-programme-course-list">
										<article v-for="course in filteredConfiguredCourses" :key="course.name" class="eduedge-programme-course-row">
											<span><strong>{{ course.course_name || course.name }}</strong><small>{{ course.department || "No Department / School Section" }}</small></span>
											<span class="eduedge-programme-course-meta">
												<EdgeStatusBadge :label="course.required ? 'Required' : 'Optional'" status="requirement" tone="neutral" />
												<small>{{ course.default_grading_scale || "No default grading scale" }}</small>
												<small v-if="course.institution_mismatch" class="eduedge-programme-warning">Institution mismatch</small>
											</span>
										</article>
									</div>
								</section>

								<section v-if="showAvailableCourses && curriculum.permissions.can_add_courses" class="eduedge-programme-curriculum-section">
									<div class="eduedge-programme-section-heading">
										<div><strong>Available Institution {{ curriculumCoursePlural }}</strong><small>{{ filteredAvailableCourses.length }} of {{ curriculum.available_courses.length }} shown</small></div>
										<button type="button" class="edge-button edge-button--primary" :disabled="curriculumSaving || !selectedCurriculumCourses.length" @click="addCurriculumCourses">{{ curriculumSaving ? "Adding..." : `Add selected (${selectedCurriculumCourses.length})` }}</button>
									</div>
									<EdgeEmptyState
										v-if="!filteredAvailableCourses.length"
										:title="curriculum.available_courses.length ? 'No available subject matches the search' : `All Institution ${curriculumCoursePlural.toLowerCase()} are configured`"
										:description="curriculum.available_courses.length ? 'Clear the search or change the view filter.' : 'No additional Institution Subject/Course is available for this Class.'"
									/>
									<div v-else class="eduedge-programme-curriculum-options">
										<label v-for="course in filteredAvailableCourses" :key="course.name" class="eduedge-programme-curriculum-option">
											<input v-model="selectedCurriculumCourses" type="checkbox" :value="course.name" />
											<span><strong>{{ course.course_name || course.name }}</strong><small>{{ course.department || "No Department / School Section" }}</small></span>
										</label>
									</div>
								</section>

								<section class="eduedge-programme-curriculum-section eduedge-programme-delivery-links">
									<div class="eduedge-programme-section-heading"><div><strong>Active Class / Programme Intakes</strong><small>Open an intake for delivery Topics, CBT and assessment work.</small></div></div>
									<EdgeEmptyState v-if="!curriculum.active_offerings.length" title="No active Class / Programme Intake" description="Create or activate a Programme Offering before managing session/term delivery." />
									<div v-else class="eduedge-programme-offering-links">
										<button v-for="offering in curriculum.active_offerings" :key="offering.name" type="button" class="edge-button" @click="openDeliveryCurriculum(offering)">
											{{ offering.offering_title || offering.name }} · {{ offering.academic_year }}{{ offering.academic_term ? ` · ${offering.academic_term}` : "" }}
										</button>
									</div>
								</section>
							</template>
						</template>
					</section>
				</div>
			</template>
		</EdgePageLayout>

		<div v-if="programmeModalOpen" class="eduedge-programme-modal-backdrop" @click.self="closeProgrammeModal">
			<section class="eduedge-programme-modal" role="dialog" aria-modal="true" :aria-label="draft.name ? `Edit ${editorProgrammeSingular}` : `New ${editorProgrammeSingular}`">
				<header class="eduedge-programme-modal-header">
					<div><p class="edge-eyebrow">{{ draft.name ? "Update class master" : "Create class master" }}</p><h2>{{ draft.name ? draft.program_name || `Edit ${editorProgrammeSingular}` : `New ${editorProgrammeSingular}` }}</h2></div>
					<button type="button" class="edge-button" :disabled="saving" @click="closeProgrammeModal">Close</button>
				</header>
				<div class="eduedge-programme-modal-body">
					<label><span>{{ editorProgrammeSingular }} name *</span><input ref="programmeNameInput" v-model.trim="draft.program_name" class="form-control" /></label>
					<label><span>Abbreviation</span><input v-model.trim="draft.program_abbreviation" class="form-control" /></label>
					<label>
						<span>Institution *</span>
						<select v-model="draft.eduedge_institution" class="form-control" :disabled="Boolean(draft.name && draft.active_offering_count)" @change="draftInstitutionChanged">
							<option value="">Select Institution</option>
							<option v-for="institution in data.institutions" :key="institution.name" :value="institution.name">{{ institution.institution_name }}</option>
						</select>
					</label>
					<label>
						<span>{{ editorDepartmentSingular }} *</span>
						<select v-model="draft.department" class="form-control" :disabled="Boolean(draft.name && draft.active_offering_count)">
							<option value="">Select {{ editorDepartmentSingular }}</option>
							<option v-for="department in draftDepartments" :key="department.name" :value="department.name">{{ departmentLabel(department) }}</option>
						</select>
					</label>
					<p class="eduedge-programme-modal-example">{{ editorExample }}</p>
					<p v-if="draft.name && draft.active_offering_count" class="eduedge-programme-governance-note">Institution and academic unit are locked because this Class has active Programme Offerings.</p>
					<p v-if="saveError" class="eduedge-programme-error">{{ saveError }}</p>
				</div>
				<footer class="eduedge-programme-modal-footer">
					<button v-if="draft.name" type="button" class="edge-button" @click="openFullForm(draft.name)">Open full form</button>
					<span class="eduedge-programme-modal-spacer"></span>
					<button type="button" class="edge-button" :disabled="saving" @click="closeProgrammeModal">Cancel</button>
					<button type="button" class="edge-button edge-button--primary" :disabled="!canSave || saving" @click="saveProgramme">{{ saving ? "Saving..." : `Save ${editorProgrammeSingular}` }}</button>
				</footer>
			</section>
		</div>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const emptyDraft = () => ({ name: "", program_name: "", program_abbreviation: "", department: "", eduedge_institution: "", active_offering_count: 0 });
const emptyCurriculum = () => ({ programme: {}, context: {}, configured_courses: [], available_courses: [], active_offerings: [], permissions: { can_add_courses: false, can_remove_courses: false }, governance_note: "" });

export default {
	name: "EduEdgeProgrammes",
	data() {
		return {
			loading: true, loadedOnce: false, error: "", saving: false, saveError: "",
			programmeModalOpen: false, selectedProgramme: null,
			curriculumLoading: false, curriculumSaving: false, curriculumError: "", curriculumRequestId: 0,
			curriculumSearch: "", curriculumView: "all", selectedCurriculumCourses: [], curriculum: emptyCurriculum(),
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
		pageContext() { return this.data.institutions.find((row) => row.name === this.filters.institution)?.context || this.activeContext; },
		draftContext() { return this.data.institutions.find((row) => row.name === this.draft.eduedge_institution)?.context || this.pageContext; },
		curriculumContext() { return this.curriculum.context || this.data.institutions.find((row) => row.name === this.selectedProgramme?.eduedge_institution)?.context || this.pageContext; },
		programmeSingular() { return this.mixedInstitutionView ? "Class / Programme" : this.term("programme", false, "Programme", this.pageContext); },
		programmePlural() { return this.mixedInstitutionView ? "Classes / Programmes" : this.term("programme", true, "Programmes", this.pageContext); },
		departmentSingular() { return this.mixedInstitutionView ? "School Section / Faculty / Department" : this.term("department", false, "Department", this.pageContext); },
		departmentPlural() { return this.mixedInstitutionView ? "School Sections / Faculties / Departments" : this.term("department", true, "Departments", this.pageContext); },
		coursePlural() { return this.mixedInstitutionView ? "Subjects / Courses / Modules" : this.term("course", true, "Courses", this.pageContext); },
		offeringPlural() { return this.mixedInstitutionView ? "Class / Programme Intakes" : this.term("programme_offering", true, "Programme Intakes", this.pageContext); },
		editorProgrammeSingular() { return this.term("programme", false, "Class / Programme", this.draftContext); },
		editorDepartmentSingular() { return this.term("department", false, "Academic Unit", this.draftContext); },
		curriculumCourseSingular() { return this.term("course", false, "Subject / Course", this.curriculumContext); },
		curriculumCoursePlural() { return this.term("course", true, "Subjects / Courses", this.curriculumContext); },
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
		showConfiguredCourses() { return this.curriculumView === "all" || this.curriculumView === "configured"; },
		showAvailableCourses() { return this.curriculumView === "all" || this.curriculumView === "available"; },
		filteredConfiguredCourses() { return (this.curriculum.configured_courses || []).filter((row) => this.curriculumSearchMatches(row)); },
		filteredAvailableCourses() { return (this.curriculum.available_courses || []).filter((row) => this.curriculumSearchMatches(row)); },
	},
	mounted() {
		window.addEventListener("keydown", this.handleKeydown);
		this.load(true);
	},
	beforeUnmount() { window.removeEventListener("keydown", this.handleKeydown); },
	methods: {
		openRoute: openEduEdgeRoute,
		term(key, plural = false, fallback = "", context = null) { return frappe.eduedge?.term?.(key, { plural, context: context || this.pageContext, fallback }) || fallback; },
		institutionName(name) { return this.data.institutions.find((row) => row.name === name)?.institution_name || name || "Unclassified Institution"; },
		departmentName(name) { return this.data.departments.find((row) => row.name === name)?.department_name || name || `No ${this.departmentSingular}`; },
		departmentLabel(row) { return row.parent_department ? `${row.department_name || row.name} · ${row.parent_department}` : row.department_name || row.name; },
		curriculumSearchMatches(row) {
			const needle = String(this.curriculumSearch || "").trim().toLowerCase();
			if (!needle) return true;
			return [row.name, row.course_name, row.department, row.default_grading_scale]
				.some((value) => String(value || "").toLowerCase().includes(needle));
		},
		handleKeydown(event) { if (event.key === "Escape" && this.programmeModalOpen) this.closeProgrammeModal(); },
		async load(resetStart = false) {
			if (resetStart) this.data.paging.start = 0;
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.programmes.get_programmes_page", { ...this.filters, start: this.data.paging.start || 0, page_length: this.data.paging.page_length || 25 });
				this.data = response.message || this.data;
				this.filters = { ...this.filters, ...(this.data.filters || {}) };
				if (this.selectedProgramme) {
					const refreshed = this.data.programmes.find((row) => row.name === this.selectedProgramme.name);
					if (refreshed) this.selectedProgramme = { ...refreshed };
				}
				this.loadedOnce = true;
			} catch (error) { this.error = error?.message || `${this.programmePlural} could not be loaded.`; }
			finally { this.loading = false; }
		},
		applyFilters() { this.clearProgrammeSelection(); this.load(true); },
		institutionChanged() { this.filters.department = ""; this.clearProgrammeSelection(); this.closeProgrammeModal(true); this.load(true); },
		clearFilters() { this.filters = { institution: "", department: "", search: "" }; this.clearProgrammeSelection(); this.closeProgrammeModal(true); this.load(true); },
		previousPage() { this.clearProgrammeSelection(); this.data.paging.start = Math.max(0, this.data.paging.start - this.data.paging.page_length); this.load(false); },
		nextPage() { if (this.data.paging.has_more) { this.clearProgrammeSelection(); this.data.paging.start = this.data.paging.next_start; this.load(false); } },
		clearProgrammeSelection() {
			this.curriculumRequestId += 1;
			this.selectedProgramme = null; this.curriculum = emptyCurriculum(); this.curriculumSearch = ""; this.curriculumView = "all";
			this.selectedCurriculumCourses = []; this.curriculumError = ""; this.curriculumLoading = false;
		},
		newProgramme() { this.openProgrammeModal(); },
		editProgramme(row) { this.openProgrammeModal(row); },
		openProgrammeModal(row = null) {
			if (row && !this.canWrite) return;
			if (!row && !this.canCreate) return;
			this.draft = row
				? { ...emptyDraft(), ...row }
				: { ...emptyDraft(), eduedge_institution: this.filters.institution || this.activeContext.institution || "" };
			this.saveError = ""; this.programmeModalOpen = true;
			this.$nextTick(() => this.$refs.programmeNameInput?.focus?.());
		},
		closeProgrammeModal(force = false) {
			if (this.saving && !force) return;
			this.programmeModalOpen = false; this.saveError = ""; this.draft = emptyDraft();
		},
		async selectProgramme(row) {
			this.selectedProgramme = { ...row }; this.curriculumSearch = ""; this.curriculumView = "all";
			await this.loadCurriculum(row.name);
		},
		async openCurriculumForRow(row) {
			await this.selectProgramme(row);
			this.$nextTick(() => this.$refs.curriculumPanel?.scrollIntoView?.({ behavior: "smooth", block: "start" }));
		},
		draftInstitutionChanged() { if (!this.draftDepartments.some((row) => row.name === this.draft.department)) this.draft.department = ""; },
		async loadCurriculum(programme) {
			const name = String(programme || "").trim();
			if (!name) { this.curriculum = emptyCurriculum(); return; }
			const requestId = ++this.curriculumRequestId;
			this.curriculumLoading = true; this.curriculumError = ""; this.selectedCurriculumCourses = [];
			try {
				const response = await frappe.call("eduedge.api.programmes.get_programme_curriculum", { programme: name });
				if (requestId !== this.curriculumRequestId || this.selectedProgramme?.name !== name) return;
				this.curriculum = response.message || emptyCurriculum();
			} catch (error) {
				if (requestId === this.curriculumRequestId) this.curriculumError = error?.message || "Class curriculum could not be loaded.";
			} finally { if (requestId === this.curriculumRequestId) this.curriculumLoading = false; }
		},
		async addCurriculumCourses() {
			const programme = this.selectedProgramme?.name;
			if (!programme || !this.selectedCurriculumCourses.length || !this.curriculum.permissions.can_add_courses) return;
			this.curriculumSaving = true; this.curriculumError = "";
			try {
				const response = await frappe.call({
					method: "eduedge.api.programmes.add_programme_curriculum_courses",
					type: "POST",
					args: { programme, courses: JSON.stringify(this.selectedCurriculumCourses) },
				});
				const result = response.message || {};
				this.curriculum = result.curriculum || this.curriculum; this.selectedCurriculumCourses = [];
				const row = this.data.programmes.find((item) => item.name === programme);
				if (row) row.course_count = this.curriculum.configured_courses.length;
				if (this.selectedProgramme) this.selectedProgramme.course_count = this.curriculum.configured_courses.length;
				this.data.summary.course_rows = this.data.programmes.reduce((sum, item) => sum + Number(item.course_count || 0), 0);
				frappe.show_alert({ message: __(`${result.added_count || 0} ${this.curriculumCoursePlural.toLowerCase()} added to Class curriculum`), indicator: "green" });
			} catch (error) { this.curriculumError = error?.message || "Subjects / Courses could not be added to this Class."; }
			finally { this.curriculumSaving = false; }
		},
		async saveProgramme() {
			if (!this.canSave) return;
			this.saving = true; this.saveError = "";
			const savedDraft = { ...this.draft };
			try {
				const response = await frappe.call("eduedge.api.programmes.save_programme", {
					programme: savedDraft.name || undefined,
					program_name: savedDraft.program_name,
					program_abbreviation: savedDraft.program_abbreviation || undefined,
					institution: savedDraft.eduedge_institution,
					department: savedDraft.department,
				});
				frappe.show_alert({ message: __(`${this.editorProgrammeSingular} saved`), indicator: "green" });
				this.programmeModalOpen = false;
				await this.load(true);
				const row = this.data.programmes.find((item) => item.name === response.message?.name);
				this.draft = emptyDraft();
				if (row) await this.selectProgramme(row);
			} catch (error) { this.saveError = error?.message || `${this.editorProgrammeSingular} could not be saved.`; }
			finally { this.saving = false; }
		},
		openDeliveryCurriculum(offering) {
			if (!offering?.name || !offering?.school_branch) return;
			const params = new URLSearchParams({ branch: offering.school_branch, offering: offering.name });
			window.location.href = `/app/eduedge-curriculum?${params.toString()}`;
		},
		openFullForm(name) { if (name) frappe.set_route("Form", "Program", name); },
		openNativeList() { window.open("/app/program", "_blank", "noopener,noreferrer"); },
		openDepartmentTree() { window.open("/app/department/view/tree", "_blank", "noopener,noreferrer"); },
	},
};
</script>

<style scoped>
.eduedge-programme-filter-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(13rem,1fr)); gap:.75rem; width:100%; }
.eduedge-programme-filter-grid label,.eduedge-programme-modal-body label,.eduedge-programme-curriculum-controls label { display:grid; gap:.35rem; font-weight:600; }
.eduedge-programme-layout { display:grid; grid-template-columns:minmax(0,1.5fr) minmax(22rem,.9fr); gap:1rem; margin-top:1rem; align-items:start; }
.eduedge-programme-panel { display:grid; gap:1rem; align-content:start; padding:1rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.eduedge-programme-curriculum-manager { position:sticky; top:1rem; max-height:calc(100vh - 2rem); overflow:auto; scroll-margin-top:6rem; }
.eduedge-programme-panel-heading,.eduedge-programme-row,.eduedge-programme-main,.eduedge-programme-counts,.eduedge-programme-heading-actions,.eduedge-programme-section-heading,.eduedge-programme-modal-header,.eduedge-programme-modal-footer { display:flex; gap:.75rem; align-items:center; }
.eduedge-programme-panel-heading,.eduedge-programme-section-heading,.eduedge-programme-modal-header { justify-content:space-between; }
.eduedge-programme-panel-heading h2,.eduedge-programme-panel-heading h3,.eduedge-programme-modal-header h2 { margin:0; }
.eduedge-programme-panel-heading>div,.eduedge-programme-section-heading>div,.eduedge-programme-modal-header>div { display:grid; gap:.2rem; }
.eduedge-programme-panel-heading small,.eduedge-programme-section-heading small,.eduedge-programme-modal-header small { color:var(--text-muted); }
.eduedge-programme-list { display:grid; gap:.65rem; }
.eduedge-programme-row { padding:.7rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); transition:border-color .15s ease,box-shadow .15s ease; }
.eduedge-programme-row.is-selected { border-color:var(--primary); box-shadow:0 0 0 1px var(--primary); }
.eduedge-programme-main { flex:1; justify-content:space-between; padding:0; border:0; background:transparent; text-align:left; min-width:0; }
.eduedge-programme-title,.eduedge-programme-context { display:grid; gap:.2rem; min-width:0; }
.eduedge-programme-title small,.eduedge-programme-context small { color:var(--text-muted); }
.eduedge-programme-counts,.eduedge-programme-heading-actions,.eduedge-programme-offering-links { flex-wrap:wrap; }
.eduedge-programme-edit-button { flex:0 0 auto; }
.eduedge-programme-paging { display:flex; justify-content:space-between; align-items:center; gap:.75rem; }
.eduedge-programme-error { margin:0; color:var(--red-600,#b42318); }
.eduedge-programme-curriculum-stats { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.6rem; }
.eduedge-programme-curriculum-stats span { display:grid; gap:.15rem; padding:.65rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); }
.eduedge-programme-curriculum-stats strong { font-size:1.25rem; }.eduedge-programme-curriculum-stats small { color:var(--text-muted); }
.eduedge-programme-curriculum-controls { display:grid; grid-template-columns:minmax(0,1fr) 10rem; gap:.6rem; }
.eduedge-programme-governance-note { margin:0; padding:.65rem; border:1px solid var(--orange-300,#f4b860); border-radius:8px; background:var(--orange-50,#fff7e8); font-size:.85rem; }
.eduedge-programme-curriculum-section { display:grid; gap:.65rem; padding:.75rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); }
.eduedge-programme-course-list,.eduedge-programme-curriculum-options { display:grid; gap:.45rem; max-height:18rem; overflow:auto; }
.eduedge-programme-course-row { display:flex; align-items:center; justify-content:space-between; gap:.75rem; padding:.6rem; border:1px solid var(--border-color); border-radius:8px; background:var(--card-bg); }
.eduedge-programme-course-row>span:first-child,.eduedge-programme-course-meta,.eduedge-programme-curriculum-option span { display:grid; gap:.15rem; }
.eduedge-programme-course-row small,.eduedge-programme-curriculum-option small { color:var(--text-muted); }
.eduedge-programme-course-meta { justify-items:end; text-align:right; }
.eduedge-programme-warning { color:var(--red-600,#b42318) !important; }
.eduedge-programme-curriculum-option { display:flex; align-items:flex-start; gap:.6rem; padding:.6rem; border:1px solid var(--border-color); border-radius:8px; background:var(--card-bg); cursor:pointer; }
.eduedge-programme-offering-links { display:flex; gap:.45rem; }
.eduedge-programme-modal-backdrop { position:fixed; inset:0; z-index:1050; display:grid; place-items:center; padding:1rem; background:rgba(15,23,42,.45); }
.eduedge-programme-modal { width:min(40rem,100%); max-height:calc(100vh - 2rem); overflow:auto; border:1px solid var(--border-color); border-radius:14px; background:var(--card-bg); box-shadow:0 24px 80px rgba(15,23,42,.24); }
.eduedge-programme-modal-header,.eduedge-programme-modal-footer { padding:1rem; }
.eduedge-programme-modal-header { border-bottom:1px solid var(--border-color); }
.eduedge-programme-modal-body { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.8rem; padding:1rem; }
.eduedge-programme-modal-example,.eduedge-programme-modal-body>.eduedge-programme-governance-note,.eduedge-programme-modal-body>.eduedge-programme-error { grid-column:1/-1; margin:0; }
.eduedge-programme-modal-example { color:var(--text-muted); }
.eduedge-programme-modal-footer { border-top:1px solid var(--border-color); }
.eduedge-programme-modal-spacer { flex:1; }
@media (max-width:1050px) { .eduedge-programme-layout { grid-template-columns:1fr; } .eduedge-programme-curriculum-manager { position:static; max-height:none; } .eduedge-programme-main { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media (max-width:650px) { .eduedge-programme-row,.eduedge-programme-main,.eduedge-programme-panel-heading,.eduedge-programme-section-heading,.eduedge-programme-paging,.eduedge-programme-course-row,.eduedge-programme-modal-header,.eduedge-programme-modal-footer { align-items:stretch; flex-direction:column; } .eduedge-programme-main,.eduedge-programme-modal-body,.eduedge-programme-curriculum-controls,.eduedge-programme-curriculum-stats { display:grid; grid-template-columns:1fr; } .eduedge-programme-course-meta { justify-items:start; text-align:left; } .eduedge-programme-modal-spacer { display:none; } }
</style>
