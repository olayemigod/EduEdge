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
					:subtitle="`Create ${classArmPlural.toLowerCase()} from valid Programme Offerings and enrolled students. Teaching responsibility is managed through Instructor Assignments.`"
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
					<div class="class-arm-filter-grid">
						<label><span>Branch / Campus</span><select v-model="filters.branch" class="form-control" @change="filterBranchChanged"><option v-for="branch in data.allowed_branches" :key="branch.name" :value="branch.name">{{ branch.branch_name || branch.name }}</option></select></label>
						<label><span>{{ academicYearSingular }}</span><select v-model="filters.academic_year" class="form-control" @change="filterYearChanged"><option value="">All {{ academicYearPlural.toLowerCase() }}</option><option v-for="year in filterAcademicYears" :key="year" :value="year">{{ year }}</option></select></label>
						<label><span>{{ academicTermSingular }}</span><select v-model="filters.academic_term" class="form-control" :disabled="!filters.academic_year" @change="load(true)"><option value="">All {{ academicTermPlural.toLowerCase() }}</option><option v-for="termName in filterAcademicTerms" :key="termName" :value="termName">{{ termName }}</option></select></label>
						<label class="class-arm-search"><span>Search</span><input v-model.trim="filters.search" class="form-control" :placeholder="`${classArmSingular}, ${programmeSingular.toLowerCase()} or ${courseSingular.toLowerCase()}`" @keyup.enter="load(true)" /></label>
					</div>
					<template #actions><button type="button" class="edge-button" @click="clearFilters">Clear</button><button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="load(true)">{{ loading ? "Loading..." : "Apply" }}</button></template>
				</EdgeFilterBar>

				<p v-if="error && loadedOnce" class="class-arm-error">{{ error }}</p>
				<section class="class-arm-layout">
					<article class="class-arm-panel">
						<div class="class-arm-heading"><div><p class="edge-eyebrow">Class catalogue</p><h2>{{ classArmPlural }}</h2></div><button v-if="canCreate" type="button" class="edge-button" @click="newClassArm">New {{ classArmSingular }}</button></div>
						<EdgeLoadingState v-if="loading" :message="`Refreshing ${classArmPlural.toLowerCase()}...`" />
						<EdgeEmptyState v-else-if="!data.class_arms.length" :title="`No ${classArmPlural.toLowerCase()} found`" :description="canCreate ? `Create the first ${classArmSingular.toLowerCase()} from a valid Programme Offering.` : 'Change the filters or contact an academic administrator.'" />
						<div v-else class="class-arm-list">
							<button v-for="row in data.class_arms" :key="row.name" type="button" class="class-arm-card" :class="{ 'is-selected': draft.name === row.name }" @click="editClassArm(row.name)">
								<div class="class-arm-title"><span><strong>{{ row.display_name || row.student_group_name || row.name }}</strong><small>{{ row.program || programmeSingular }} · {{ row.academic_year }}</small></span><EdgeStatusBadge :label="row.disabled ? 'Disabled' : 'Active'" :status="row.disabled ? 'disabled' : 'active'" :tone="row.disabled ? 'danger' : 'success'" /></div>
								<div class="class-arm-meta"><span>{{ row.academic_term || `${academicYearSingular}-wide` }}</span><span>{{ row.course || row.group_based_on || "Class" }}</span><span>{{ row.student_count || 0 }} {{ studentPlural.toLowerCase() }}</span><span>Teaching team via assignments</span></div>
							</button>
						</div>
						<div class="class-arm-paging"><button type="button" class="edge-button" :disabled="loading || data.paging.start <= 0" @click="previousPage">Previous</button><span>{{ data.paging.start + (data.class_arms.length ? 1 : 0) }}–{{ data.paging.start + data.class_arms.length }}</span><button type="button" class="edge-button" :disabled="loading || !data.paging.has_more" @click="nextPage">Next</button></div>
					</article>

					<article class="class-arm-panel editor">
						<div class="class-arm-heading"><div><p class="edge-eyebrow">{{ draft.name ? "Quick edit" : "Quick create" }}</p><h2>{{ draft.name ? draft.display_name || classArmSingular : `New ${classArmSingular}` }}</h2></div><button type="button" class="edge-button" @click="newClassArm">Reset</button></div>
						<EdgeEmptyState v-if="!canCreate && !canWrite" :title="`Read-only ${classArmPlural.toLowerCase()}`" :description="`Your role can view ${classArmPlural.toLowerCase()} but cannot create or edit them.`" />
						<template v-else>
							<label><span>Branch / Campus</span><select v-model="draft.branch" class="form-control" :disabled="Boolean(draft.name)" @change="draftBranchChanged"><option value="">Select Branch / Campus</option><option v-for="branch in data.allowed_branches" :key="branch.name" :value="branch.name">{{ branch.branch_name || branch.name }}</option></select></label>
							<label><span>{{ offeringSingular }}</span><select v-model="draft.offering" class="form-control" :disabled="Boolean(draft.name) || !draft.branch || optionsLoading" @change="draftOfferingChanged"><option value="">{{ draft.branch ? `Select ${offeringSingular}` : "Select Branch first" }}</option><option v-for="offering in options.offerings" :key="offering.name" :value="offering.name">{{ offering.offering_title || offering.name }} · {{ offering.academic_year }}{{ offering.academic_term ? ` · ${offering.academic_term}` : "" }}</option></select></label>

							<div v-if="draft.offering" class="class-arm-context">
								<div><span>Institution</span><strong>{{ contextInstitutionName }}</strong></div><div><span>{{ programmeSingular }}</span><strong>{{ draft.program || "Not resolved" }}</strong></div><div><span>{{ academicYearSingular }}</span><strong>{{ draft.academic_year || "Not resolved" }}</strong></div><div><span>{{ academicTermSingular }}</span><strong>{{ draft.academic_term || `${academicYearSingular}-wide` }}</strong></div><div><span>Cohort / Batch</span><strong>{{ draft.batch || "Not assigned" }}</strong></div>
							</div>

							<label><span>{{ classArmSingular }} Name</span><input v-model.trim="draft.display_name" class="form-control" :placeholder="`Example: JSS 1A or ${programmeSingular} Group A`" /></label>
							<div class="two-column"><label><span>Group Based On</span><select v-model="draft.group_based_on" class="form-control" @change="groupBasisChanged"><option value="Batch">Batch / Class</option><option value="Course">Course / Subject</option><option value="Activity">Activity</option></select></label><label><span>Maximum Strength</span><input v-model.number="draft.max_strength" type="number" min="0" class="form-control" /><small>Zero means no configured limit.</small></label></div>
							<label v-if="draft.group_based_on === 'Course'"><span>{{ courseSingular }}</span><select v-model="draft.course" class="form-control"><option value="">Select {{ courseSingular }}</option><option v-for="course in options.courses" :key="course.name" :value="course.name">{{ course.label || course.name }}</option></select></label>
							<label class="class-arm-check"><input v-model="draft.disabled" type="checkbox" /> Disabled</label>

							<section class="class-arm-roster">
								<div class="class-arm-subheading"><div><p class="edge-eyebrow">Roster</p><h3>{{ studentPlural }}</h3></div><span>{{ draft.students.length }} selected</span></div>
								<input v-model.trim="studentSearch" class="form-control" :placeholder="`Search eligible ${studentPlural.toLowerCase()}`" />
								<EdgeEmptyState v-if="draft.offering && !studentChoices.length" :title="`No eligible ${studentPlural.toLowerCase()}`" description="Only enabled students with submitted enrollment in this exact Programme Offering and Branch are available." />
								<div v-else class="choice-list"><div v-for="student in filteredStudentChoices" :key="student.name" class="choice-row"><label><input type="checkbox" :checked="isStudentSelected(student.name)" @change="toggleStudent(student)" /><span><strong>{{ student.student_name || student.name }}</strong><small>{{ student.name }}</small></span></label><input v-if="isStudentSelected(student.name)" :value="studentRoll(student.name)" type="number" min="1" class="form-control input-sm" placeholder="Roll no." @input="setStudentRoll(student.name, $event.target.value)" /></div></div>
							</section>

							<EdgeActionBar label="Save the Class Arm first, then create Instructor Assignments for the whole class or its Courses / Subjects.">
								<template #actions><button v-if="draft.name" type="button" class="edge-button edge-button--primary" @click="openInstructorAssignments">Assign Instructor</button><button type="button" class="edge-button" @click="openInstructors">Manage Instructors</button></template>
							</EdgeActionBar>

							<p v-if="saveError" class="class-arm-error">{{ saveError }}</p>
							<div class="class-arm-actions"><button type="button" class="edge-button edge-button--primary" :disabled="!canSave || saving || optionsLoading" @click="saveClassArm">{{ saving ? "Saving..." : `Save ${classArmSingular}` }}</button><button v-if="draft.name" type="button" class="edge-button" @click="openFullForm(draft.name)">Open full form</button></div>
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
const emptyData = () => ({ selected_branch: {}, allowed_branches: [], class_arms: [], filters: {}, permissions: { can_create: false, can_write: false }, paging: { start: 0, page_length: 25, has_more: false, next_start: 0 } });

export default {
	name: "EduEdgeClassArms",
	data() { return { loading: true, loadedOnce: false, error: "", optionsLoading: false, saving: false, saveError: "", menuItems: EDUEDGE_MENU_ITEMS, filters: { branch: "", academic_year: "", academic_term: "", search: "" }, data: emptyData(), options: emptyOptions(), draft: emptyDraft(), studentSearch: "", initialCreateMode: false }; },
	computed: {
		selectedBranch() { return this.data.selected_branch || {}; },
		classArmSingular() { return this.term("student_group", false, "Class Arm"); }, classArmPlural() { return this.term("student_group", true, "Class Arms"); },
		programmeSingular() { return this.term("programme", false, "Programme / Class"); }, offeringSingular() { return this.term("programme_offering", false, "Programme Offering"); },
		academicYearSingular() { return this.term("academic_year", false, "Academic Session"); }, academicYearPlural() { return this.term("academic_year", true, "Academic Sessions"); },
		academicTermSingular() { return this.term("academic_term", false, "Term / Semester"); }, academicTermPlural() { return this.term("academic_term", true, "Terms / Semesters"); },
		courseSingular() { return this.term("course", false, "Course / Subject"); }, studentPlural() { return this.term("student", true, "Students"); },
		canCreate() { return Boolean(this.data.permissions.can_create); }, canWrite() { return Boolean(this.data.permissions.can_write); },
		canSave() { const permitted = this.draft.name ? this.draft.can_write && this.canWrite : this.canCreate; return Boolean(permitted && this.draft.branch && this.draft.offering && this.draft.display_name && (this.draft.group_based_on !== "Course" || this.draft.course)); },
		filterAcademicYears() { return [...new Set((this.options.offerings || []).map((row) => row.academic_year).filter(Boolean))]; },
		filterAcademicTerms() { return [...new Set((this.options.offerings || []).filter((row) => !this.filters.academic_year || row.academic_year === this.filters.academic_year).map((row) => row.academic_term).filter(Boolean))]; },
		contextInstitutionName() { const branch = this.data.allowed_branches.find((row) => row.name === this.draft.branch); return branch?.institution_name || this.options.context?.institution || "Not resolved"; },
		studentChoices() { const rows = new Map(); for (const row of this.options.students || []) rows.set(row.name, { ...row }); for (const row of this.draft.students || []) if (row.student) rows.set(row.student, { name: row.student, student_name: row.student_name || row.student, ...(rows.get(row.student) || {}) }); return [...rows.values()]; },
		filteredStudentChoices() { const query = this.studentSearch.toLowerCase(); return query ? this.studentChoices.filter((row) => `${row.student_name || ""} ${row.name || ""}`.toLowerCase().includes(query)) : this.studentChoices; },
	},
	async mounted() { const params = new URLSearchParams(window.location.search || ""); this.filters.branch = params.get("branch") || ""; this.filters.academic_year = params.get("academic_year") || ""; this.filters.academic_term = params.get("academic_term") || ""; this.initialCreateMode = params.get("mode") === "create"; await this.load(true); if (this.initialCreateMode && this.canCreate) await this.newClassArm(); else await this.loadOptions(); },
	methods: {
		openRoute: openEduEdgeRoute,
		term(key, plural = false, fallback = "") { return frappe.eduedge?.term?.(key, { plural, context: this.selectedBranch, fallback }) || fallback; },
		async load(resetStart = false) { if (resetStart) this.data.paging.start = 0; this.loading = true; this.error = ""; try { const response = await frappe.call("eduedge.api.class_arms.get_class_arms_page", { ...this.filters, start: this.data.paging.start || 0, page_length: this.data.paging.page_length || 25 }); this.data = response.message || emptyData(); this.filters = { ...this.filters, ...(this.data.filters || {}) }; this.loadedOnce = true; if (!this.draft.branch) this.draft.branch = this.filters.branch || ""; } catch (error) { this.error = error?.message || `${this.classArmPlural} could not be loaded.`; } finally { this.loading = false; } },
		async loadOptions() { if (!this.draft.branch && !this.filters.branch) return; this.optionsLoading = true; this.saveError = ""; try { const response = await frappe.call("eduedge.api.class_arms.get_class_arm_options", { branch: this.draft.branch || this.filters.branch, offering: this.draft.offering || undefined, class_arm: this.draft.name || undefined }); const result = response.message || {}; this.options = { ...emptyOptions(), ...result, context: result.context || {} }; if (!this.data.allowed_branches.length && result.allowed_branches) this.data.allowed_branches = result.allowed_branches; if (result.context?.name) this.applyOfferingContext(result.context); } catch (error) { this.saveError = error?.message || "Class Arm options could not be loaded."; } finally { this.optionsLoading = false; } },
		applyOfferingContext(context) { this.draft.institution = context.institution || ""; this.draft.program = context.program || ""; this.draft.academic_year = context.academic_year || ""; this.draft.academic_term = context.academic_term || ""; this.draft.batch = context.student_batch || ""; },
		async newClassArm() { this.draft = { ...emptyDraft(), branch: this.filters.branch || this.data.selected_branch?.name || "", academic_year: this.filters.academic_year || "", academic_term: this.filters.academic_term || "" }; this.options = emptyOptions(); this.studentSearch = ""; this.saveError = ""; await this.loadOptions(); },
		async editClassArm(name) { this.saveError = ""; try { const response = await frappe.call("eduedge.api.class_arms.get_class_arm", { name }); const row = response.message || {}; this.draft = { ...emptyDraft(), ...row, offering: row.offering || "", branch: row.branch || this.filters.branch, disabled: Boolean(row.disabled), students: row.students || [], instructors: row.instructors || [] }; await this.loadOptions(); } catch (error) { this.saveError = error?.message || `${this.classArmSingular} could not be opened.`; } },
		async filterBranchChanged() { this.filters.academic_year = ""; this.filters.academic_term = ""; await this.load(true); await this.newClassArm(); }, async filterYearChanged() { this.filters.academic_term = ""; await this.load(true); }, async clearFilters() { const branch = this.filters.branch; this.filters = { branch, academic_year: "", academic_term: "", search: "" }; await this.load(true); },
		async draftBranchChanged() { this.filters.branch = this.draft.branch; this.draft.offering = ""; this.draft.institution = ""; this.draft.program = ""; this.draft.academic_year = ""; this.draft.academic_term = ""; this.draft.batch = ""; this.draft.course = ""; this.draft.students = []; this.draft.instructors = []; await this.load(true); await this.loadOptions(); },
		async draftOfferingChanged() { this.draft.course = ""; this.draft.students = []; this.draft.instructors = []; await this.loadOptions(); }, groupBasisChanged() { if (this.draft.group_based_on !== "Course") this.draft.course = ""; },
		isStudentSelected(name) { return this.draft.students.some((row) => row.student === name); }, toggleStudent(student) { const index = this.draft.students.findIndex((row) => row.student === student.name); if (index >= 0) this.draft.students.splice(index, 1); else this.draft.students.push({ student: student.name, student_name: student.student_name || student.name, group_roll_number: "", active: 1 }); }, studentRoll(name) { return this.draft.students.find((row) => row.student === name)?.group_roll_number || ""; }, setStudentRoll(name, value) { const row = this.draft.students.find((item) => item.student === name); if (row) row.group_roll_number = value ? Number(value) : ""; },
		async saveClassArm() { if (!this.canSave) return; this.saving = true; this.saveError = ""; try { const response = await frappe.call({ method: "eduedge.api.class_arms.save_class_arm", type: "POST", args: { class_arm: this.draft.name || undefined, display_name: this.draft.display_name, branch: this.draft.branch, offering: this.draft.offering, group_based_on: this.draft.group_based_on, course: this.draft.course || undefined, max_strength: this.draft.max_strength || 0, disabled: this.draft.disabled ? 1 : 0, students: JSON.stringify(this.draft.students || []), instructors: JSON.stringify(this.draft.instructors || []) } }); const saved = response.message || {}; frappe.show_alert({ message: __(`${this.classArmSingular} saved`), indicator: "green" }); this.filters.branch = saved.branch || this.filters.branch; this.filters.academic_year = this.draft.academic_year || this.filters.academic_year; await this.load(true); if (saved.name) await this.editClassArm(saved.name); } catch (error) { this.saveError = error?.message || `${this.classArmSingular} could not be saved.`; } finally { this.saving = false; } },
		openInstructorAssignments() { if (!this.draft.name) return; const params = new URLSearchParams({ branch: this.draft.branch, offering: this.draft.offering, student_group: this.draft.name }); window.location.href = `/app/eduedge-instructor-assignments?${params.toString()}`; },
		openInstructors() { window.location.href = "/app/eduedge-instructors"; }, openFullForm(name) { if (name) window.open(`/app/student-group/${encodeURIComponent(name)}`, "_blank", "noopener,noreferrer"); }, previousPage() { this.data.paging.start = Math.max(0, this.data.paging.start - this.data.paging.page_length); this.load(false); }, nextPage() { if (this.data.paging.has_more) { this.data.paging.start = this.data.paging.next_start; this.load(false); } },
	},
};
</script>

<style scoped>
.class-arm-filter-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(12rem,1fr)); gap:.75rem; width:100%; }.class-arm-filter-grid label,.editor label { display:grid; gap:.35rem; font-weight:600; }.class-arm-search { grid-column:span 2; }.class-arm-layout { display:grid; grid-template-columns:minmax(0,1fr) minmax(24rem,.95fr); gap:1rem; margin-top:1rem; }.class-arm-panel { display:grid; gap:1rem; align-content:start; padding:1rem; border:1px solid var(--border-color); border-radius:12px; background:var(--card-bg); }.class-arm-heading,.class-arm-title,.class-arm-subheading,.class-arm-actions,.class-arm-paging { display:flex; align-items:center; justify-content:space-between; gap:1rem; }.class-arm-heading h2,.class-arm-subheading h3 { margin:.2rem 0 0; }.class-arm-list,.choice-list,.class-arm-roster { display:grid; gap:.75rem; }.class-arm-card { display:grid; gap:.75rem; width:100%; padding:.9rem; text-align:left; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); }.class-arm-card:hover,.class-arm-card.is-selected { border-color:var(--primary); }.class-arm-title>span,.choice-row span { display:grid; gap:.15rem; }.class-arm-title small,.choice-row small,.editor small { color:var(--text-muted); }.class-arm-meta { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.5rem; color:var(--text-muted); font-size:.82rem; }.class-arm-context { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; padding:.8rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); }.class-arm-context>div { display:grid; gap:.15rem; }.class-arm-context span { color:var(--text-muted); font-size:.78rem; }.two-column { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; }.class-arm-check { display:flex !important; align-items:center; gap:.5rem !important; font-weight:500 !important; }.class-arm-roster { padding-top:.75rem; border-top:1px solid var(--border-color); }.choice-list { max-height:18rem; overflow:auto; padding-right:.25rem; }.choice-row { display:grid; grid-template-columns:minmax(0,1fr) 6rem; align-items:center; gap:.75rem; padding:.65rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); }.choice-row>label { display:flex !important; align-items:center; gap:.6rem !important; font-weight:500 !important; }.class-arm-error { margin:0; color:var(--red-600,#b42318); } @media (max-width:1100px) { .class-arm-layout { grid-template-columns:1fr; } } @media (max-width:700px) { .class-arm-search { grid-column:auto; }.class-arm-meta,.class-arm-context,.two-column,.choice-row { grid-template-columns:1fr; }.class-arm-heading,.class-arm-title,.class-arm-subheading,.class-arm-actions,.class-arm-paging { align-items:stretch; flex-direction:column; } }
</style>
