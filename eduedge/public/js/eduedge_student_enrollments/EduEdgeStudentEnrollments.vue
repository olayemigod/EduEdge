<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="data.selected_branch?.institution_name || ''"
		:branch-name="data.selected_branch?.branch_name || 'Student Enrollments'"
		:menu-items="menuItems"
		active-route="/app/eduedge-student-enrollments"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="People Operations"
					title="Student Enrollments"
					subtitle="Enroll an enabled Student into an active Programme Offering, save a draft, and submit only after the academic context is correct."
					:action-label="canCreate ? 'New Enrollment' : ''"
					@action="newEnrollment"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loaded" message="Loading Student Enrollments..." :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loaded" title="Student Enrollments could not load" :message="error" action-label="Try again" @retry="load(true)" />
			<template v-else>
				<EdgeFilterBar title="Enrollment context">
					<div class="eduedge-enrollment-filters">
						<label>
							<span>Target Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="branchChanged">
								<option v-for="row in data.allowed_branches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option>
							</select>
						</label>
						<label>
							<span>Student</span>
							<EdgeLinkField
								v-model="filters.student"
								:selected-label="filterStudentLabel"
								:searcher="searchFilterStudents"
								:context="{ branch: filters.branch }"
								placeholder="Search Student name, ID, mobile or email"
								:open-on-focus="true"
								@select="filterStudentSelected"
								@clear="filterStudentCleared"
							/>
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" @click="openStudents">Student Profiles</button>
						<button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="load(true)">Refresh</button>
					</template>
				</EdgeFilterBar>

				<p v-if="error" class="eduedge-enrollment-error">{{ error }}</p>
				<section class="eduedge-enrollment-layout">
					<article class="eduedge-enrollment-panel">
						<div class="eduedge-enrollment-heading">
							<div><p class="edge-eyebrow">Enrollment register</p><h2>Current records</h2></div>
							<button v-if="canCreate" type="button" class="edge-button" @click="newEnrollment">New Enrollment</button>
						</div>
						<EdgeLoadingState v-if="loading" message="Refreshing enrollments..." />
						<EdgeEmptyState v-else-if="!data.enrollments.length" title="No Enrollment found" description="Create a draft Enrollment and submit it when the Programme Offering context is correct." />
						<div v-else class="eduedge-enrollment-list">
							<button v-for="row in data.enrollments" :key="row.name" type="button" class="eduedge-enrollment-card" :class="{ 'is-selected': draft.name === row.name }" @click="editEnrollment(row.name)">
								<span><strong>{{ row.student_name || row.student }}</strong><small>{{ row.program }} · {{ row.academic_year }}{{ row.academic_term ? ` · ${row.academic_term}` : '' }}</small></span>
								<EdgeStatusBadge :label="row.status_label" :status="row.status_label" :tone="row.docstatus === 1 ? 'success' : 'warning'" />
							</button>
						</div>
						<div class="eduedge-enrollment-paging">
							<button type="button" class="edge-button" :disabled="loading || data.paging.start <= 0" @click="previousPage">Previous</button>
							<span>{{ data.paging.start + (data.enrollments.length ? 1 : 0) }}–{{ data.paging.start + data.enrollments.length }}</span>
							<button type="button" class="edge-button" :disabled="loading || !data.paging.has_more" @click="nextPage">Next</button>
						</div>
					</article>

					<article class="eduedge-enrollment-panel eduedge-enrollment-editor">
						<div class="eduedge-enrollment-heading">
							<div><p class="edge-eyebrow">{{ draft.name ? 'Enrollment record' : 'Quick create' }}</p><h2>{{ draft.name || 'New Student Enrollment' }}</h2></div>
							<div class="eduedge-enrollment-actions">
								<button v-if="draft.student" type="button" class="edge-button" @click="openStudentProfile">Open Student</button>
								<button v-if="draft.name" type="button" class="edge-button" @click="openFullForm">Open full form</button>
							</div>
						</div>

						<EdgeActionBar
							v-if="draft.docstatus === 1"
							label="This Enrollment is submitted and read-only. Promotion or transfer must use a separate controlled workflow and will not silently create another Enrollment."
						/>

						<div class="eduedge-enrollment-grid">
							<label>
								<span>Student *</span>
								<EdgeLinkField
									v-model="draft.student"
									:selected-label="draftStudentLabel"
									:searcher="searchDraftStudents"
									:context="{ branch: draft.branch }"
									placeholder="Search Student name, ID, mobile or email"
									:disabled="!canEdit || Boolean(draft.name) || !draft.branch"
									:open-on-focus="true"
									@select="draftStudentSelected"
									@clear="draftStudentCleared"
								/>
							</label>
							<label>
								<span>Target Branch / Campus *</span>
								<select v-model="draft.branch" class="form-control" :disabled="!canEdit || Boolean(draft.name)" @change="draftBranchChanged">
									<option value="">Select Branch</option>
									<option v-for="row in data.allowed_branches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option>
								</select>
							</label>
							<label class="wide">
								<span>Programme Offering *</span>
								<EdgeLinkField
									v-model="draft.offering"
									:selected-label="draftOfferingLabel"
									:searcher="searchOfferings"
									:context="{ branch: draft.branch, student: draft.student }"
									:placeholder="draft.student && draft.branch ? 'Search Programme Offering, class or session' : 'Select Student and Branch first'"
									:disabled="!canEdit || !draft.student || !draft.branch || optionsLoading"
									:open-on-focus="true"
									@select="offeringSelected"
									@clear="offeringCleared"
								/>
							</label>
							<label><span>Enrollment date *</span><input v-model="draft.enrollment_date" type="date" class="form-control" :disabled="!canEdit" /></label>
							<label><span>Student category</span><select v-model="draft.student_category" class="form-control" :disabled="!canEdit"><option value="">Not specified</option><option v-for="row in data.student_categories" :key="row.name" :value="row.name">{{ row.name }}</option></select></label>
							<label><span>School house</span><select v-model="draft.school_house" class="form-control" :disabled="!canEdit"><option value="">Not assigned</option><option v-for="row in data.school_houses" :key="row.name" :value="row.name">{{ row.name }}</option></select></label>
							<label class="eduedge-enrollment-check"><input v-model.number="draft.boarding_student" type="checkbox" :true-value="1" :false-value="0" :disabled="!canEdit" /> Boarding Student</label>
						</div>

						<section v-if="draft.offering" class="eduedge-enrollment-context">
							<div><span>Institution</span><strong>{{ data.selected_branch?.institution_name || context.institution || 'Not resolved' }}</strong></div>
							<div><span>Programme / Class</span><strong>{{ context.program || draft.program || 'Not resolved' }}</strong></div>
							<div><span>Academic Session</span><strong>{{ context.academic_year || draft.academic_year || 'Not resolved' }}</strong></div>
							<div><span>Term / Semester</span><strong>{{ context.academic_term || draft.academic_term || 'Session-wide' }}</strong></div>
							<div><span>Batch / Cohort</span><strong>{{ context.student_batch || draft.student_batch_name || 'Not assigned' }}</strong></div>
							<div><span>Capacity</span><strong>{{ capacityLabel }}</strong></div>
						</section>

						<section v-if="draft.offering" class="eduedge-enrollment-courses">
							<div class="eduedge-enrollment-heading"><div><p class="edge-eyebrow">Programme curriculum</p><h3>Courses / Subjects</h3></div><span>{{ requiredCourses.length }} required</span></div>
							<EdgeEmptyState v-if="!options.courses.length" title="No curriculum courses configured" description="The Programme has no Course rows. Review the Programme before submitting the Enrollment." />
							<div v-else class="eduedge-enrollment-course-list">
								<div v-for="row in options.courses" :key="row.course" class="eduedge-enrollment-course-row"><span><strong>{{ row.course_name || row.course }}</strong><small>{{ row.course }}</small></span><EdgeStatusBadge :label="row.required ? 'Required' : 'Optional'" :status="row.required ? 'required' : 'optional'" :tone="row.required ? 'success' : 'neutral'" /></div>
							</div>
						</section>

						<EdgeActionBar
							v-if="canEdit"
							label="Submitting makes this Enrollment authoritative, creates required Course Enrollments, may create configured fee records, and immediately makes the Student eligible for the matching Class Arm."
						>
							<template #actions>
								<button type="button" class="edge-button" :disabled="saving || !canSave" @click="save(false)">{{ saving ? 'Saving...' : 'Save Draft' }}</button>
								<button v-if="canSubmit" type="button" class="edge-button edge-button--primary" :disabled="saving || !canSave" @click="confirmSubmit">Submit Enrollment</button>
							</template>
						</EdgeActionBar>
						<p v-if="saveError" class="eduedge-enrollment-error">{{ saveError }}</p>
					</article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const today = () => frappe.datetime?.get_today?.() || new Date().toISOString().slice(0, 10);
const blankDraft = (branch = "", student = "") => ({
	name: "", student, student_name: "", branch, offering: "", eduedge_program_offering: "", eduedge_school_branch: branch,
	program: "", academic_year: "", academic_term: "", student_batch_name: "", enrollment_date: today(),
	student_category: "", school_house: "", boarding_student: 0, courses: [], docstatus: 0, status_label: "Draft",
	can_edit: true, can_submit: true,
});
const blankData = () => ({
	allowed_branches: [], selected_branch: {}, selected_student: null, enrollments: [], enrollment: null,
	student_categories: [], school_houses: [], permissions: {}, paging: { start: 0, page_length: 25, has_more: false },
});
const blankOptions = () => ({ context: {}, courses: [], student: {}, branch: {} });

export default {
	name: "EduEdgeStudentEnrollments",
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS, loading: true, loaded: false, optionsLoading: false, saving: false,
			error: "", saveError: "", filters: { branch: "", student: "", start: 0 }, data: blankData(),
			options: blankOptions(), draft: blankDraft(), initialCreateMode: false, initialOffering: "",
			filterStudentLabel: "", draftStudentLabel: "", draftOfferingLabel: "",
		};
	},
	computed: {
		canCreate() { return Boolean(this.data.permissions?.can_create); },
		canEdit() { return this.draft.name ? Boolean(this.draft.docstatus === 0 && this.draft.can_edit) : this.canCreate; },
		canSubmit() { return Boolean(this.canEdit && this.data.permissions?.can_submit && (this.draft.can_submit !== false)); },
		canSave() { return Boolean(this.canEdit && this.draft.student && this.draft.branch && this.draft.offering && this.draft.enrollment_date); },
		context() { return this.options.context || {}; },
		requiredCourses() { return (this.options.courses || []).filter((row) => Number(row.required) === 1); },
		capacityLabel() {
			if (!this.context.capacity) return "No limit configured";
			return `${this.context.capacity_consumed || 0} of ${this.context.capacity} used · ${this.context.available_slots || 0} available`;
		},
	},
	async mounted() {
		const params = new URLSearchParams(window.location.search || "");
		this.filters.branch = params.get("branch") || "";
		this.filters.student = params.get("student") || "";
		this.initialOffering = params.get("offering") || "";
		this.initialCreateMode = params.get("mode") === "create";
		await this.load(true);
		if (this.initialCreateMode && this.canCreate) await this.newEnrollment();
	},
	methods: {
		openRoute: openEduEdgeRoute,
		async callSearch(method, args) {
			const response = await frappe.call(method, args);
			return response.message || [];
		},
		searchFilterStudents(query) {
			if (!this.filters.branch) return Promise.resolve([]);
			return this.callSearch("eduedge.api.enrollment_link_search.search_eligible_students", { branch: this.filters.branch, query, page_length: 20 });
		},
		searchDraftStudents(query) {
			if (!this.draft.branch) return Promise.resolve([]);
			return this.callSearch("eduedge.api.enrollment_link_search.search_eligible_students", { branch: this.draft.branch, query, page_length: 20 });
		},
		searchOfferings(query) {
			if (!this.draft.branch || !this.draft.student) return Promise.resolve([]);
			return this.callSearch("eduedge.api.enrollment_link_search.search_enrollment_offerings", { branch: this.draft.branch, student: this.draft.student, query, page_length: 20 });
		},
		async load(reset = false, enrollment = "") {
			if (reset) this.filters.start = 0;
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.student_enrollment_runtime.get_student_enrollments_page", {
					branch: this.filters.branch || undefined, student: this.filters.student || undefined,
					enrollment: enrollment || undefined, start: this.filters.start, page_length: this.data.paging.page_length || 25,
				});
				this.data = response.message || blankData();
				this.filters.branch = this.data.selected_branch?.name || this.filters.branch;
				if (this.data.selected_student?.name === this.filters.student) this.filterStudentLabel = this.data.selected_student.student_name || this.data.selected_student.name;
				this.loaded = true;
				if (this.data.enrollment) {
					const row = this.data.enrollment;
					this.draft = { ...blankDraft(row.eduedge_school_branch || this.filters.branch, row.student), ...row, branch: row.eduedge_school_branch || this.filters.branch, offering: row.eduedge_program_offering || "", boarding_student: Number(row.boarding_student || 0) };
					this.filters.student = row.student || this.filters.student;
					this.filterStudentLabel = row.student_name || this.filterStudentLabel;
					this.draftStudentLabel = row.student_name || row.student || "";
					await this.loadOptions();
				} else if (!this.draft.name) {
					this.draft.branch = this.filters.branch;
					this.draft.eduedge_school_branch = this.filters.branch;
					this.draft.student = this.filters.student;
					this.draftStudentLabel = this.filterStudentLabel;
				}
			} catch (error) { this.error = error?.message || "Student Enrollments could not be loaded."; }
			finally { this.loading = false; }
		},
		async loadOptions() {
			if (!this.draft.student || !this.draft.branch || !this.draft.offering) { this.options = blankOptions(); return; }
			this.optionsLoading = true; this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.student_enrollment_runtime.get_student_enrollment_context", {
					student: this.draft.student, branch: this.draft.branch, offering: this.draft.offering,
				});
				this.options = { ...blankOptions(), ...(response.message || {}) };
				if (this.context.name) {
					this.applyContext(this.context);
					this.draftOfferingLabel = this.context.offering_title || this.context.name;
				}
			} catch (error) { this.options = blankOptions(); this.saveError = error?.message || "Enrollment context could not be loaded."; }
			finally { this.optionsLoading = false; }
		},
		applyContext(context) {
			this.draft.eduedge_program_offering = context.name || "";
			this.draft.eduedge_school_branch = context.school_branch || this.draft.branch;
			this.draft.program = context.program || "";
			this.draft.academic_year = context.academic_year || "";
			this.draft.academic_term = context.academic_term || "";
			this.draft.student_batch_name = context.student_batch || "";
		},
		async newEnrollment() {
			this.draft = blankDraft(this.filters.branch || this.data.selected_branch?.name || "", this.filters.student || "");
			this.draftStudentLabel = this.filterStudentLabel;
			this.draftOfferingLabel = "";
			this.options = blankOptions();
			if (this.initialOffering && this.draft.student && this.draft.branch) {
				this.draft.offering = this.initialOffering;
				this.draft.eduedge_program_offering = this.initialOffering;
				await this.loadOptions();
			}
			this.saveError = "";
		},
		async editEnrollment(name) { await this.load(false, name); },
		async branchChanged() {
			this.initialOffering = ""; this.filters.student = ""; this.filterStudentLabel = "";
			this.draft = blankDraft(this.filters.branch, ""); this.draftStudentLabel = ""; this.draftOfferingLabel = ""; this.options = blankOptions(); await this.load(true);
		},
		async filterStudentSelected(option) { this.filterStudentLabel = option?.label || option?.value || ""; await this.studentFilterChanged(); },
		async filterStudentCleared() { this.filters.student = ""; this.filterStudentLabel = ""; await this.studentFilterChanged(); },
		async studentFilterChanged() {
			this.draft = blankDraft(this.filters.branch, this.filters.student);
			this.draftStudentLabel = this.filterStudentLabel;
			this.draftOfferingLabel = "";
			this.options = blankOptions();
			await this.load(true);
		},
		async draftStudentSelected(option) { this.draftStudentLabel = option?.label || option?.value || ""; await this.studentChanged(); },
		async draftStudentCleared() { this.draft.student = ""; this.draftStudentLabel = ""; await this.studentChanged(); },
		async studentChanged() {
			this.filters.student = this.draft.student;
			this.filterStudentLabel = this.draftStudentLabel;
			this.draft.offering = ""; this.draft.eduedge_program_offering = ""; this.draftOfferingLabel = ""; this.options = blankOptions();
			await this.load(true);
		},
		async draftBranchChanged() {
			this.initialOffering = ""; this.filters.branch = this.draft.branch; this.filters.student = ""; this.filterStudentLabel = "";
			this.draft.student = ""; this.draftStudentLabel = ""; this.draft.offering = ""; this.draftOfferingLabel = ""; this.draft.eduedge_program_offering = "";
			this.draft.program = ""; this.draft.academic_year = ""; this.draft.academic_term = ""; this.draft.student_batch_name = ""; this.options = blankOptions();
			await this.load(true); this.draft.branch = this.filters.branch;
		},
		async offeringSelected(option) { this.draftOfferingLabel = option?.label || option?.value || ""; await this.offeringChanged(); },
		async offeringCleared() { this.draft.offering = ""; this.draftOfferingLabel = ""; this.draft.eduedge_program_offering = ""; this.options = blankOptions(); },
		async offeringChanged() { await this.loadOptions(); },
		async save(submit = false) {
			if (!this.canSave) return;
			this.saving = true; this.saveError = "";
			try {
				const payload = { ...this.draft, branch: this.draft.branch, offering: this.draft.offering };
				const response = await frappe.call({ method: "eduedge.api.student_enrollments.save_student_enrollment", type: "POST", args: { payload: JSON.stringify(payload), submit: submit ? 1 : 0 } });
				const saved = response.message || {};
				frappe.show_alert({ message: submit ? __("Enrollment submitted") : __("Enrollment draft saved"), indicator: "green" });
				this.filters.student = saved.student || this.filters.student;
				await this.load(true, saved.name);
			} catch (error) { this.saveError = error?.message || "Enrollment could not be saved."; }
			finally { this.saving = false; }
		},
		confirmSubmit() {
			frappe.confirm(
				__("Submit this Enrollment? It will become authoritative, create required Course Enrollments, may create configured fee records, and cannot be edited directly afterwards."),
				() => this.save(true),
			);
		},
		openStudents() { window.location.href = "/app/eduedge-students"; },
		openStudentProfile() { if (this.draft.student) window.location.href = `/app/eduedge-students?student=${encodeURIComponent(this.draft.student)}&branch=${encodeURIComponent(this.draft.branch || this.filters.branch)}`; },
		openFullForm() { if (this.draft.name) window.open(`/app/program-enrollment/${encodeURIComponent(this.draft.name)}`, "_blank", "noopener,noreferrer"); },
		previousPage() { this.filters.start = Math.max(0, this.filters.start - this.data.paging.page_length); this.load(); },
		nextPage() { if (this.data.paging.has_more) { this.filters.start += this.data.paging.page_length; this.load(); } },
	},
};
</script>

<style scoped>
.eduedge-enrollment-filters,.eduedge-enrollment-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; width:100%; }
.eduedge-enrollment-filters label,.eduedge-enrollment-grid label { display:grid; gap:.35rem; font-weight:600; }
.eduedge-enrollment-layout { display:grid; grid-template-columns:minmax(18rem,.75fr) minmax(0,1.45fr); gap:1rem; margin-top:1rem; }
.eduedge-enrollment-panel { display:grid; gap:1rem; align-content:start; padding:1rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.eduedge-enrollment-heading,.eduedge-enrollment-actions,.eduedge-enrollment-paging { display:flex; align-items:center; justify-content:space-between; gap:.75rem; flex-wrap:wrap; }
.eduedge-enrollment-heading h2,.eduedge-enrollment-heading h3 { margin:.2rem 0 0; }
.eduedge-enrollment-list,.eduedge-enrollment-course-list { display:grid; gap:.65rem; }
.eduedge-enrollment-card,.eduedge-enrollment-course-row { display:flex; align-items:center; justify-content:space-between; gap:.75rem; padding:.75rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.eduedge-enrollment-card { width:100%; text-align:left; }.eduedge-enrollment-card:hover,.eduedge-enrollment-card.is-selected { border-color:var(--primary); }
.eduedge-enrollment-card span,.eduedge-enrollment-course-row span { display:grid; gap:.15rem; }.eduedge-enrollment-card small,.eduedge-enrollment-course-row small { color:var(--text-muted); }
.eduedge-enrollment-grid .wide { grid-column:1/-1; }.eduedge-enrollment-check { display:flex !important; align-items:center; gap:.5rem !important; font-weight:500 !important; }
.eduedge-enrollment-context { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.75rem; padding:.8rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); }
.eduedge-enrollment-context>div { display:grid; gap:.15rem; }.eduedge-enrollment-context span { color:var(--text-muted); font-size:.78rem; }
.eduedge-enrollment-courses { display:grid; gap:.75rem; padding-top:.75rem; border-top:1px solid var(--border-color); }.eduedge-enrollment-error { color:var(--red-600,#b42318); }
@media (max-width:1000px) { .eduedge-enrollment-layout { grid-template-columns:1fr; } }
@media (max-width:700px) { .eduedge-enrollment-filters,.eduedge-enrollment-grid,.eduedge-enrollment-context { grid-template-columns:1fr; }.eduedge-enrollment-grid .wide { grid-column:auto; } }
</style>