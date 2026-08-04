<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="selectedBranch.institution_name || ''"
		:branch-name="selectedBranch.branch_name || classArmPlural"
		:menu-items="menuItems"
		active-route="/app/eduedge-class-arms"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Academic Operations"
					:title="classArmPlural"
					:subtitle="`Create and maintain ${classArmPlural.toLowerCase()} from valid Programme Offerings, enrolled students, and Branch-assigned instructors.`"
					:action-label="canCreate ? `New ${classArmSingular}` : ''"
					@action="newClassArm"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loadedOnce" :message="`Loading ${classArmPlural.toLowerCase()}...`" :skeleton="true" />
			<EdgeErrorState
				v-else-if="error && !loadedOnce"
				:title="`${classArmPlural} could not load`"
				:message="error"
				action-label="Try again"
				@retry="load(true)"
			/>
			<template v-else>
				<EdgeFilterBar :title="`${classArmSingular} filters`">
					<div class="eduedge-class-arm-filter-grid">
						<label>
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="filterBranchChanged">
								<option v-for="branch in data.allowed_branches" :key="branch.name" :value="branch.name">
									{{ branch.branch_name || branch.name }}
								</option>
							</select>
						</label>
						<label>
							<span>{{ academicYearSingular }}</span>
							<select v-model="filters.academic_year" class="form-control" @change="filterYearChanged">
								<option value="">All {{ academicYearPlural.toLowerCase() }}</option>
								<option v-for="year in filterAcademicYears" :key="year" :value="year">{{ year }}</option>
							</select>
						</label>
						<label>
							<span>{{ academicTermSingular }}</span>
							<select v-model="filters.academic_term" class="form-control" :disabled="!filters.academic_year" @change="load(true)">
								<option value="">All {{ academicTermPlural.toLowerCase() }}</option>
								<option v-for="termName in filterAcademicTerms" :key="termName" :value="termName">{{ termName }}</option>
							</select>
						</label>
						<label class="eduedge-class-arm-search">
							<span>Search</span>
							<input v-model.trim="filters.search" class="form-control" :placeholder="`${classArmSingular}, ${programmeSingular.toLowerCase()} or ${courseSingular.toLowerCase()}`" @keyup.enter="load(true)" />
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" @click="clearFilters">Clear</button>
						<button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="load(true)">{{ loading ? "Loading..." : "Apply" }}</button>
					</template>
				</EdgeFilterBar>

				<p v-if="error && loadedOnce" class="eduedge-class-arm-error">{{ error }}</p>
				<section class="eduedge-class-arm-layout">
					<article class="eduedge-class-arm-panel">
						<div class="eduedge-class-arm-heading">
							<div><p class="edge-eyebrow">Class catalogue</p><h2>{{ classArmPlural }}</h2></div>
							<button v-if="canCreate" type="button" class="edge-button" @click="newClassArm">New {{ classArmSingular }}</button>
						</div>
						<EdgeLoadingState v-if="loading" :message="`Refreshing ${classArmPlural.toLowerCase()}...`" />
						<EdgeEmptyState
							v-else-if="!data.class_arms.length"
							:title="`No ${classArmPlural.toLowerCase()} found`"
							:description="canCreate ? `Create the first ${classArmSingular.toLowerCase()} from a valid Programme Offering.` : 'Change the filters or contact an academic administrator.'"
						/>
						<div v-else class="eduedge-class-arm-list">
							<button v-for="row in data.class_arms" :key="row.name" type="button" class="eduedge-class-arm-card" @click="editClassArm(row.name)">
								<div class="eduedge-class-arm-title">
									<span><strong>{{ row.display_name || row.student_group_name || row.name }}</strong><small>{{ row.program || programmeSingular }} · {{ row.academic_year }}</small></span>
									<EdgeStatusBadge :label="row.disabled ? 'Disabled' : 'Active'" :status="row.disabled ? 'disabled' : 'active'" :tone="row.disabled ? 'danger' : 'success'" />
								</div>
								<div class="eduedge-class-arm-meta">
									<span>{{ row.academic_term || `${academicYearSingular}-wide` }}</span>
									<span>{{ row.course || row.group_based_on || "Class" }}</span>
									<span>{{ row.student_count || 0 }} {{ studentPlural.toLowerCase() }}</span>
									<span>{{ (row.instructor_names || []).join(", ") || `No ${instructorSingular.toLowerCase()}` }}</span>
								</div>
							</button>
						</div>
						<div class="eduedge-class-arm-paging">
							<button type="button" class="edge-button" :disabled="loading || data.paging.start <= 0" @click="previousPage">Previous</button>
							<span>{{ data.paging.start + (data.class_arms.length ? 1 : 0) }}–{{ data.paging.start + data.class_arms.length }}</span>
							<button type="button" class="edge-button" :disabled="loading || !data.paging.has_more" @click="nextPage">Next</button>
						</div>
					</article>

					<article class="eduedge-class-arm-panel eduedge-class-arm-editor">
						<div class="eduedge-class-arm-heading">
							<div><p class="edge-eyebrow">{{ draft.name ? "Quick edit" : "Quick create" }}</p><h2>{{ draft.name ? draft.display_name || classArmSingular : `New ${classArmSingular}` }}</h2></div>
							<button type="button" class="edge-button" @click="newClassArm">Reset</button>
						</div>
						<EdgeEmptyState
							v-if="!canCreate && !canWrite"
							:title="`Read-only ${classArmPlural.toLowerCase()}`"
							:description="`Your role can view ${classArmPlural.toLowerCase()} but cannot create or edit them.`"
						/>
						<template v-else>
							<label>
								<span>Branch / Campus</span>
								<select v-model="draft.branch" class="form-control" :disabled="Boolean(draft.name)" @change="draftBranchChanged">
									<option value="">Select Branch / Campus</option>
									<option v-for="branch in data.allowed_branches" :key="branch.name" :value="branch.name">{{ branch.branch_name || branch.name }}</option>
								</select>
							</label>
							<label>
								<span>{{ offeringSingular }}</span>
								<select v-model="draft.offering" class="form-control" :disabled="Boolean(draft.name) || !draft.branch || optionsLoading" @change="draftOfferingChanged">
									<option value="">{{ draft.branch ? `Select ${offeringSingular}` : "Select Branch first" }}</option>
									<option v-for="offering in options.offerings" :key="offering.name" :value="offering.name">
										{{ offering.offering_title || offering.name }} · {{ offering.academic_year }}{{ offering.academic_term ? ` · ${offering.academic_term}` : "" }}
									</option>
								</select>
							</label>

							<div v-if="draft.offering" class="eduedge-class-arm-context">
								<div><span>Institution</span><strong>{{ contextInstitutionName }}</strong></div>
								<div><span>{{ programmeSingular }}</span><strong>{{ draft.program || "Not resolved" }}</strong></div>
								<div><span>{{ academicYearSingular }}</span><strong>{{ draft.academic_year || "Not resolved" }}</strong></div>
								<div><span>{{ academicTermSingular }}</span><strong>{{ draft.academic_term || `${academicYearSingular}-wide` }}</strong></div>
								<div><span>Cohort / Batch</span><strong>{{ draft.batch || "Not assigned" }}</strong></div>
							</div>

							<label><span>{{ classArmSingular }} Name</span><input v-model.trim="draft.display_name" class="form-control" :placeholder="`Example: JSS 1A or ${programmeSingular} Group A`" /></label>
							<div class="eduedge-class-arm-two-column">
								<label><span>Group Based On</span><select v-model="draft.group_based_on" class="form-control" @change="groupBasisChanged"><option value="Batch">Batch / Class</option><option value="Course">Course / Subject</option><option value="Activity">Activity</option></select></label>
								<label><span>Maximum Strength</span><input v-model.number="draft.max_strength" type="number" min="0" class="form-control" /><small>Zero means no configured limit.</small></label>
							</div>
							<label v-if="draft.group_based_on === 'Course'">
								<span>{{ courseSingular }}</span>
								<select v-model="draft.course" class="form-control"><option value="">Select {{ courseSingular }}</option><option v-for="course in options.courses" :key="course.name" :value="course.name">{{ course.label || course.name }}</option></select>
							</label>
							<label class="eduedge-class-arm-check"><input v-model="draft.disabled" type="checkbox" /> Disabled</label>

							<section class="eduedge-class-arm-roster">
								<div class="eduedge-class-arm-subheading"><div><p class="edge-eyebrow">Roster</p><h3>{{ studentPlural }}</h3></div><span>{{ draft.students.length }} selected</span></div>
								<input v-model.trim="studentSearch" class="form-control" :placeholder="`Search eligible ${studentPlural.toLowerCase()}`" />
								<EdgeEmptyState v-if="draft.offering && !studentChoices.length" :title="`No eligible ${studentPlural.toLowerCase()}`" description="Only enabled students with submitted enrollment in this exact Programme Offering and Branch are available." />
								<div v-else class="eduedge-choice-list">
									<div v-for="student in filteredStudentChoices" :key="student.name" class="eduedge-choice-row">
										<label><input type="checkbox" :checked="isStudentSelected(student.name)" @change="toggleStudent(student)" /><span><strong>{{ student.student_name || student.name }}</strong><small>{{ student.name }}</small></span></label>
										<input v-if="isStudentSelected(student.name)" :value="studentRoll(student.name)" type="number" min="1" class="form-control input-sm" placeholder="Roll no." @input="setStudentRoll(student.name, $event.target.value)" />
									</div>
								</div>
							</section>

							<section class="eduedge-class-arm-roster">
								<div class="eduedge-class-arm-subheading"><div><p class="edge-eyebrow">Teaching team</p><h3>{{ instructorPlural }}</h3></div><span>{{ draft.instructors.length }} selected</span></div>
								<EdgeEmptyState v-if="draft.branch && !instructorChoices.length" :title="`No ${instructorPlural.toLowerCase()} available`" description="Create an enabled Instructor Branch Assignment before assigning this Class Arm." />
								<div v-else class="eduedge-choice-list">
									<label v-for="instructor in instructorChoices" :key="instructor.name" class="eduedge-choice-row eduedge-choice-row--single"><input type="checkbox" :checked="isInstructorSelected(instructor.name)" @change="toggleInstructor(instructor)" /><span><strong>{{ instructor.instructor_name || instructor.name }}</strong><small>{{ instructor.name }}</small></span></label>
								</div>
							</section>

							<p v-if="saveError" class="eduedge-class-arm-error">{{ saveError }}</p>
							<div class="eduedge-class-arm-actions">
								<button type="button" class="edge-button edge-button--primary" :disabled="!canSave || saving || optionsLoading" @click="saveClassArm">{{ saving ? "Saving..." : `Save ${classArmSingular}` }}</button>
								<button v-if="draft.name" type="button" class="edge-button" @click="openFullForm(draft.name)">Open full form</button>
							</div>
						</template>
					</article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const emptyDraft = () => ({
	name: "", display_name: "", branch: "", institution: "", offering: "", program: "", academic_year: "", academic_term: "", batch: "",
	group_based_on: "Batch", course: "", max_strength: 0, disabled: false, students: [], instructors: [], can_write: true,
});
const emptyOptions = () => ({ offerings: [], courses: [], students: [], instructors: [], context: {} });
const emptyData = () => ({
	selected_branch: {}, allowed_branches: [], class_arms: [], filters: {}, permissions: { can_create: false, can_write: false },
	paging: { start: 0, page_length: 25, has_more: false, next_start: 0 },
});

export default {
	name: "EduEdgeClassArms",
	data() {
		return {
			loading: true, loadedOnce: false, error: "", optionsLoading: false, saving: false, saveError: "", menuItems: EDUEDGE_MENU_ITEMS,
			filters: { branch: "", academic_year: "", academic_term: "", search: "" }, data: emptyData(), options: emptyOptions(), draft: emptyDraft(),
			studentSearch: "", initialCreateMode: false,
		};
	},
	computed: {
		selectedBranch() { return this.data.selected_branch || {}; },
		classArmSingular() { return this.term("student_group", false, "Class Arm"); },
		classArmPlural() { return this.term("student_group", true, "Class Arms"); },
		programmeSingular() { return this.term("programme", false, "Programme / Class"); },
		offeringSingular() { return this.term("programme_offering", false, "Programme Offering"); },
		academicYearSingular() { return this.term("academic_year", false, "Academic Session"); },
		academicYearPlural() { return this.term("academic_year", true, "Academic Sessions"); },
		academicTermSingular() { return this.term("academic_term", false, "Term / Semester"); },
		academicTermPlural() { return this.term("academic_term", true, "Terms / Semesters"); },
		courseSingular() { return this.term("course", false, "Course / Subject"); },
		studentPlural() { return this.term("student", true, "Students"); },
		instructorSingular() { return this.term("instructor", false, "Instructor"); },
		instructorPlural() { return this.term("instructor", true, "Instructors"); },
		canCreate() { return Boolean(this.data.permissions.can_create); },
		canWrite() { return Boolean(this.data.permissions.can_write); },
		canSave() { const permitted = this.draft.name ? this.draft.can_write && this.canWrite : this.canCreate; return Boolean(permitted && this.draft.branch && this.draft.offering && this.draft.display_name && (this.draft.group_based_on !== "Course" || this.draft.course)); },
		filterAcademicYears() { return [...new Set((this.options.offerings || []).map((row) => row.academic_year).filter(Boolean))]; },
		filterAcademicTerms() { return [...new Set((this.options.offerings || []).filter((row) => !this.filters.academic_year || row.academic_year === this.filters.academic_year).map((row) => row.academic_term).filter(Boolean))]; },
		contextInstitutionName() { const branch = this.data.allowed_branches.find((row) => row.name === this.draft.branch); return branch?.institution_name || this.options.context?.institution || "Not resolved"; },
		studentChoices() {
			const rows = new Map();
			for (const row of this.options.students || []) rows.set(row.name, { ...row });
			for (const row of this.draft.students || []) if (row.student) rows.set(row.student, { name: row.student, student_name: row.student_name || row.student, ...(rows.get(row.student) || {}) });
			return [...rows.values()];
		},
		filteredStudentChoices() { const query = this.studentSearch.toLowerCase(); return query ? this.studentChoices.filter((row) => `${row.student_name || ""} ${row.name || ""}`.toLowerCase().includes(query)) : this.studentChoices; },
		instructorChoices() {
			const rows = new Map();
			for (const row of this.options.instructors || []) rows.set(row.name, { ...row });
			for (const row of this.draft.instructors || []) if (row.instructor) rows.set(row.instructor, { name: row.instructor, instructor_name: row.instructor_name || row.instructor, ...(rows.get(row.instructor) || {}) });
			return [...rows.values()];
		},
	},
	async mounted() {
		const params = new URLSearchParams(window.location.search || "");
		this.filters.branch = params.get("branch") || "";
		this.filters.academic_year = params.get("academic_year") || "";
		this.filters.academic_term = params.get("academic_term") || "";
		this.initialCreateMode = params.get("mode") === "create";
		await this.load(true);
		if (this.initialCreateMode && this.canCreate) await this.newClassArm();
		else await this.loadOptions();
	},
	methods: {
		openRoute: openEduEdgeRoute,
		term(key, plural = false, fallback = "") { return frappe.eduedge?.term?.(key, { plural, context: this.selectedBranch, fallback }) || fallback; },
		async load(resetStart = false) {
			if (resetStart) this.data.paging.start = 0;
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.class_arms.get_class_arms_page", { ...this.filters, start: this.data.paging.start || 0, page_length: this.data.paging.page_length || 25 });
				this.data = response.message || emptyData(); this.filters = { ...this.filters, ...(this.data.filters || {}) }; this.loadedOnce = true;
				if (!this.draft.branch) this.draft.branch = this.filters.branch || "";
			} catch (error) { this.error = error?.message || `${this.classArmPlural} could not be loaded.`; }
			finally { this.loading = false; }
		},
		async loadOptions() {
			if (!this.draft.branch && !this.filters.branch) return;
			this.optionsLoading = true; this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.class_arms.get_class_arm_options", { branch: this.draft.branch || this.filters.branch, offering: this.draft.offering || undefined, class_arm: this.draft.name || undefined });
				const result = response.message || {}; this.options = { ...emptyOptions(), ...result, context: result.context || {} };
				if (!this.data.allowed_branches.length && result.allowed_branches) this.data.allowed_branches = result.allowed_branches;
				if (result.context?.name) this.applyOfferingContext(result.context);
			} catch (error) { this.saveError = error?.message || "Class Arm options could not be loaded."; }
			finally { this.optionsLoading = false; }
		},
		applyOfferingContext(context) { this.draft.institution = context.institution || ""; this.draft.program = context.program || ""; this.draft.academic_year = context.academic_year || ""; this.draft.academic_term = context.academic_term || ""; this.draft.batch = context.student_batch || ""; },
		async newClassArm() { this.draft = { ...emptyDraft(), branch: this.filters.branch || this.data.selected_branch?.name || "", academic_year: this.filters.academic_year || "", academic_term: this.filters.academic_term || "" }; this.options = emptyOptions(); this.studentSearch = ""; this.saveError = ""; await this.loadOptions(); },
		async editClassArm(name) {
			this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.class_arms.get_class_arm", { name });
				const row = response.message || {}; this.draft = { ...emptyDraft(), ...row, offering: row.offering || "", branch: row.branch || this.filters.branch, disabled: Boolean(row.disabled), students: row.students || [], instructors: row.instructors || [] };
				await this.loadOptions();
			} catch (error) { this.saveError = error?.message || `${this.classArmSingular} could not be opened.`; }
		},
		async filterBranchChanged() { this.filters.academic_year = ""; this.filters.academic_term = ""; await this.load(true); await this.newClassArm(); },
		async filterYearChanged() { this.filters.academic_term = ""; await this.load(true); },
		async clearFilters() { const branch = this.filters.branch; this.filters = { branch, academic_year: "", academic_term: "", search: "" }; await this.load(true); },
		async draftBranchChanged() { this.filters.branch = this.draft.branch; this.draft.offering = ""; this.draft.institution = ""; this.draft.program = ""; this.draft.academic_year = ""; this.draft.academic_term = ""; this.draft.batch = ""; this.draft.course = ""; this.draft.students = []; this.draft.instructors = []; await this.load(true); await this.loadOptions(); },
		async draftOfferingChanged() { this.draft.course = ""; this.draft.students = []; this.draft.instructors = []; await this.loadOptions(); },
		groupBasisChanged() { if (this.draft.group_based_on !== "Course") this.draft.course = ""; },
		isStudentSelected(name) { return this.draft.students.some((row) => row.student === name); },
		toggleStudent(student) { const index = this.draft.students.findIndex((row) => row.student === student.name); if (index >= 0) this.draft.students.splice(index, 1); else this.draft.students.push({ student: student.name, student_name: student.student_name || student.name, group_roll_number: "", active: 1 }); },
		studentRoll(name) { return this.draft.students.find((row) => row.student === name)?.group_roll_number || ""; },
		setStudentRoll(name, value) { const row = this.draft.students.find((item) => item.student === name); if (row) row.group_roll_number = value ? Number(value) : ""; },
		isInstructorSelected(name) { return this.draft.instructors.some((row) => row.instructor === name); },
		toggleInstructor(instructor) { const index = this.draft.instructors.findIndex((row) => row.instructor === instructor.name); if (index >= 0) this.draft.instructors.splice(index, 1); else this.draft.instructors.push({ instructor: instructor.name, instructor_name: instructor.instructor_name || instructor.name }); },
		async saveClassArm() {
			if (!this.canSave) return;
			this.saving = true; this.saveError = "";
			try {
				const response = await frappe.call({ method: "eduedge.api.class_arms.save_class_arm", type: "POST", args: { class_arm: this.draft.name || undefined, display_name: this.draft.display_name, branch: this.draft.branch, offering: this.draft.offering, group_based_on: this.draft.group_based_on, course: this.draft.course || undefined, max_strength: this.draft.max_strength || 0, disabled: this.draft.disabled ? 1 : 0, students: JSON.stringify(this.draft.students || []), instructors: JSON.stringify(this.draft.instructors || []) } });
				const saved = response.message || {}; frappe.show_alert({ message: __(`${this.classArmSingular} saved`), indicator: "green" }); this.filters.branch = saved.branch || this.filters.branch; this.filters.academic_year = this.draft.academic_year || this.filters.academic_year; await this.load(true); if (saved.name) await this.editClassArm(saved.name);
			} catch (error) { this.saveError = error?.message || `${this.classArmSingular} could not be saved.`; }
			finally { this.saving = false; }
		},
		openFullForm(name) { if (name) window.open(`/app/student-group/${encodeURIComponent(name)}`, "_blank", "noopener,noreferrer"); },
		previousPage() { this.data.paging.start = Math.max(0, this.data.paging.start - this.data.paging.page_length); this.load(false); },
		nextPage() { if (this.data.paging.has_more) { this.data.paging.start = this.data.paging.next_start; this.load(false); } },
	},
};
</script>

<style scoped>
.eduedge-class-arm-filter-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(12rem,1fr)); gap:.75rem; width:100%; }
.eduedge-class-arm-filter-grid label,.eduedge-class-arm-editor label { display:grid; gap:.35rem; font-weight:600; }
.eduedge-class-arm-search { grid-column:span 2; }
.eduedge-class-arm-layout { display:grid; grid-template-columns:minmax(0,1fr) minmax(24rem,.95fr); gap:1rem; margin-top:1rem; }
.eduedge-class-arm-panel { display:grid; gap:1rem; align-content:start; padding:1rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.eduedge-class-arm-heading,.eduedge-class-arm-title,.eduedge-class-arm-subheading,.eduedge-class-arm-actions,.eduedge-class-arm-paging { display:flex; align-items:center; justify-content:space-between; gap:1rem; }
.eduedge-class-arm-heading h2,.eduedge-class-arm-subheading h3 { margin:.2rem 0 0; }
.eduedge-class-arm-list,.eduedge-choice-list,.eduedge-class-arm-roster { display:grid; gap:.75rem; }
.eduedge-class-arm-card { display:grid; gap:.75rem; width:100%; padding:.9rem; text-align:left; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.eduedge-class-arm-card:hover { border-color:var(--primary); }
.eduedge-class-arm-title>span,.eduedge-choice-row span { display:grid; gap:.15rem; }
.eduedge-class-arm-title small,.eduedge-choice-row small,.eduedge-class-arm-editor small { color:var(--text-muted); }
.eduedge-class-arm-meta { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.5rem; color:var(--text-muted); font-size:.82rem; }
.eduedge-class-arm-context { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; padding:.8rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.eduedge-class-arm-context>div { display:grid; gap:.15rem; }
.eduedge-class-arm-context span { color:var(--text-muted); font-size:.78rem; }
.eduedge-class-arm-two-column { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; }
.eduedge-class-arm-check { display:flex !important; align-items:center; gap:.5rem !important; font-weight:500 !important; }
.eduedge-class-arm-roster { padding-top:.75rem; border-top:1px solid var(--border-color); }
.eduedge-choice-list { max-height:18rem; overflow:auto; padding-right:.25rem; }
.eduedge-choice-row { display:grid; grid-template-columns:minmax(0,1fr) 6rem; align-items:center; gap:.75rem; padding:.65rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.eduedge-choice-row>label,.eduedge-choice-row--single { display:flex !important; align-items:center; gap:.6rem !important; font-weight:500 !important; }
.eduedge-choice-row--single { grid-template-columns:1fr; }
.eduedge-class-arm-error { margin:0; color:var(--red-600,#b42318); }
@media (max-width:1100px) { .eduedge-class-arm-layout { grid-template-columns:1fr; } }
@media (max-width:700px) { .eduedge-class-arm-search { grid-column:auto; } .eduedge-class-arm-meta,.eduedge-class-arm-context,.eduedge-class-arm-two-column,.eduedge-choice-row { grid-template-columns:1fr; } .eduedge-class-arm-heading,.eduedge-class-arm-title,.eduedge-class-arm-subheading,.eduedge-class-arm-actions,.eduedge-class-arm-paging { align-items:stretch; flex-direction:column; } }
</style>
