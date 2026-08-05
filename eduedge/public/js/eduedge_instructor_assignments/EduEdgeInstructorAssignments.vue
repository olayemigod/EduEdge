<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="activeInstitutionName"
		branch-name="Instructor Assignments"
		:menu-items="menuItems"
		active-route="/app/eduedge-instructor-assignments"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="People & Academic Operations"
					title="Instructor Assignments"
					subtitle="Assign one Instructor across multiple Institutions, Branches, Classes, Class Arms and Subjects in one controlled operation."
					action-label="Manage Instructors"
					@action="openInstructors"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loaded" message="Loading Instructor Assignments..." :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loaded" title="Instructor Assignments could not load" :message="error" action-label="Try again" @retry="load" />
			<template v-else>
				<p v-if="error" class="assignment-error">{{ error }}</p>
				<section class="assignment-panel">
					<div class="assignment-heading">
						<div><p class="edge-eyebrow">Unified assignment builder</p><h2>What should this Instructor manage?</h2></div>
						<button type="button" class="edge-button" @click="resetForm">Reset</button>
					</div>

					<div class="assignment-grid">
						<label class="wide">
							<span>Instructor *</span>
							<select v-model="form.instructor" class="form-control" @change="instructorChanged">
								<option value="">Select Instructor</option>
								<option v-for="row in data.instructors" :key="row.name" :value="row.name">{{ row.instructor_name || row.name }}{{ row.home_institution_name ? ` · ${row.home_institution_name}` : '' }}{{ row.department ? ` · ${row.department}` : '' }}</option>
							</select>
						</label>
						<label><span>Assignment Scope *</span><select v-model="form.assignment_scope" class="form-control" @change="scopeChanged"><option v-for="value in data.assignment_scopes" :key="value" :value="value">{{ value }}</option></select></label>
						<label><span>Assignment Type *</span><select v-model="form.assignment_type" class="form-control" @change="invalidatePreview"><option v-for="value in data.assignment_types" :key="value" :value="value">{{ value }}</option></select></label>
						<label><span>Valid From</span><input v-model="form.valid_from" type="date" class="form-control" @change="invalidatePreview" /></label>
						<label><span>Valid To</span><input v-model="form.valid_to" type="date" class="form-control" @change="invalidatePreview" /></label>
						<label><span>Status</span><select v-model.number="form.enabled" class="form-control" @change="invalidatePreview"><option :value="1">Active</option><option :value="0">Disabled</option></select></label>
					</div>

					<EdgeActionBar label="An Instructor's Home Institution is administrative only. Assignments may cover every Institution and Branch available to your user." />

					<section class="selection-section">
						<div class="assignment-heading">
							<div><p class="edge-eyebrow">Step 1</p><h3>Institutions and Branches / Campuses</h3><small>Select one or several Branches, including Branches from different Institutions.</small></div>
							<div class="assignment-actions"><button type="button" class="edge-button" @click="selectAllBranches">Select available</button><button type="button" class="edge-button" @click="clearBranches">Clear</button></div>
						</div>
						<div class="institution-groups">
							<section v-for="group in branchGroups" :key="group.institution" class="institution-group">
								<div class="institution-group-title"><strong>{{ group.institution_name }}</strong><span>{{ selectedBranchCount(group.rows) }} of {{ group.rows.length }} selected</span></div>
								<div class="choice-grid">
									<label v-for="row in group.rows" :key="row.name" class="choice-card">
										<input type="checkbox" :checked="form.branches.includes(row.name)" @change="toggleBranch(row.name)" />
										<span><strong>{{ row.branch_name || row.name }}</strong><small>{{ row.branch_code || row.name }}</small></span>
									</label>
								</div>
							</section>
						</div>
						<EdgeEmptyState v-if="!data.allowed_branches.length" title="No Branch available" description="Your user has no enabled Institution or Branch context for Instructor assignment." />
					</section>

					<template v-if="form.assignment_scope !== branchOnlyScope">
						<section class="selection-section">
							<div class="assignment-heading"><div><p class="edge-eyebrow">Step 2</p><h3>Classes / Programme Offerings</h3><small>Classes are filtered to the selected Branches.</small></div><div class="assignment-actions"><button type="button" class="edge-button" @click="selectAllOfferings">Select available</button><button type="button" class="edge-button" @click="clearOfferings">Clear</button></div></div>
							<EdgeEmptyState v-if="!form.branches.length" title="Select a Branch first" description="Classes load only from selected Branches." />
							<div v-else class="choice-grid"><label v-for="row in availableOfferings" :key="row.name" class="choice-card"><input type="checkbox" :checked="form.program_offerings.includes(row.name)" @change="toggleOffering(row.name)" /><span><strong>{{ row.offering_title || row.name }}</strong><small>{{ institutionLabel(row.institution) }} · {{ branchLabel(row.school_branch) }} · {{ row.academic_year }}{{ row.academic_term ? ` · ${row.academic_term}` : '' }}</small></span></label></div>
						</section>

						<section v-if="form.assignment_scope === classArmScope" class="selection-section">
							<div class="assignment-heading"><div><p class="edge-eyebrow">Step 3</p><h3>Class Arms</h3><small>Select Class Arms from the chosen Classes.</small></div><div class="assignment-actions"><button type="button" class="edge-button" @click="selectAllGroups">Select available</button><button type="button" class="edge-button" @click="clearGroups">Clear</button></div></div>
							<EdgeEmptyState v-if="!form.program_offerings.length" title="Select a Class first" description="Class Arms are filtered to the selected Classes." />
							<div v-else class="choice-grid"><label v-for="row in availableGroups" :key="row.name" class="choice-card"><input type="checkbox" :checked="form.student_groups.includes(row.name)" @change="toggleGroup(row.name)" /><span><strong>{{ row.eduedge_display_name || row.student_group_name || row.name }}</strong><small>{{ offeringLabel(row.eduedge_program_offering) }} · {{ branchLabel(row.eduedge_school_branch) }}</small></span></label></div>
						</section>

						<section class="selection-section">
							<div class="assignment-heading"><div><p class="edge-eyebrow">{{ form.assignment_scope === classArmScope ? 'Step 4' : 'Step 3' }}</p><h3>{{ coursePlural }}</h3><small>Subjects apply only to Classes where they are configured.</small></div><div class="assignment-actions"><button type="button" class="edge-button" @click="selectAllCourses">Select available</button><button type="button" class="edge-button" @click="clearCourses">Clear</button></div></div>
							<EdgeActionBar v-if="courseRequired" :label="`${courseSingular} selection is required for ${form.assignment_type}.`" />
							<EdgeEmptyState v-if="!form.program_offerings.length" :title="`Select a Class before choosing ${coursePlural}`" :description="`${coursePlural} come from each selected Class curriculum.`" />
							<div v-else class="choice-grid"><label v-for="row in availableCourses" :key="row.name" class="choice-card"><input type="checkbox" :checked="form.courses.includes(row.name)" @change="toggleCourse(row.name)" /><span><strong>{{ row.course_name || row.name }}</strong><small>Configured in {{ courseCoverage(row.name) }} selected Class{{ courseCoverage(row.name) === 1 ? '' : 'es' }}</small></span></label></div>
						</section>
					</template>

					<label class="notes"><span>Notes</span><textarea v-model.trim="form.notes" rows="3" class="form-control" placeholder="Optional assignment or handover note" @input="invalidatePreview"></textarea></label>

					<EdgeActionBar label="Preview validates every selected Institution, Branch, Class, Class Arm and Subject combination. Exact existing assignments are skipped and conflicts block the batch.">
						<template #actions><button type="button" class="edge-button" :disabled="previewing || !canPreview" @click="previewBatch">{{ previewing ? 'Checking...' : 'Preview Assignment Batch' }}</button><button type="button" class="edge-button edge-button--primary" :disabled="saving || !canSaveBatch" @click="saveBatch">{{ saving ? 'Saving...' : saveButtonLabel }}</button></template>
					</EdgeActionBar>
					<p v-if="saveError" class="assignment-error">{{ saveError }}</p>

					<section v-if="preview" class="preview">
						<div class="preview-metrics"><div><span>Institutions</span><strong>{{ preview.institution_count || selectedInstitutionCount }}</strong></div><div><span>Branches</span><strong>{{ preview.branch_count }}</strong></div><div><span>Valid combinations</span><strong>{{ preview.valid_combinations }}</strong></div><div><span>New records</span><strong>{{ preview.create_count }}</strong></div><div><span>Existing</span><strong>{{ preview.existing_count }}</strong></div><div><span>Conflicts</span><strong>{{ preview.conflict_count }}</strong></div></div>
						<div v-if="preview.conflicts?.length" class="preview-list danger"><strong>Resolve overlapping assignments first</strong><span v-for="row in preview.conflicts" :key="row.name">{{ row.label }} · {{ row.name }}</span></div>
						<div v-if="preview.skipped?.length" class="preview-list"><strong>Skipped because the Subject is not configured for that Class</strong><span v-for="(row,index) in preview.skipped" :key="`${row.program_offering}-${row.course}-${index}`">{{ offeringLabel(row.program_offering) }} · {{ row.course }}</span></div>
					</section>
				</section>

				<section v-if="form.instructor" class="register-layout">
					<article class="assignment-panel"><div class="assignment-heading"><div><p class="edge-eyebrow">Operational access</p><h2>Branch Eligibility</h2></div><span>{{ data.branch_assignments.length }}</span></div><EdgeEmptyState v-if="!data.branch_assignments.length" title="No Branch eligibility" description="Saving an assignment creates the required Branch eligibility." /><div v-else class="register-list"><article v-for="row in data.branch_assignments" :key="row.name"><span><strong>{{ institutionForBranch(row.school_branch) }} · {{ branchLabel(row.school_branch) }}</strong><small>{{ row.is_primary ? 'Primary Branch' : 'Additional Branch' }} · {{ row.valid_from || 'No start restriction' }} → {{ row.valid_to || 'Open ended' }}</small></span><EdgeStatusBadge :label="row.enabled ? 'Active' : 'Disabled'" :status="row.enabled ? 'active' : 'disabled'" :tone="row.enabled ? 'success' : 'danger'" /></article></div></article>
					<article class="assignment-panel"><div class="assignment-heading"><div><p class="edge-eyebrow">Academic responsibility</p><h2>Current Instructor Assignments</h2></div><span>{{ data.assignments.length }}</span></div><EdgeEmptyState v-if="!data.assignments.length" title="No academic assignment" description="Assign Classes, Class Arms and Subjects above." /><div v-else class="register-list"><article v-for="row in data.assignments" :key="row.name"><span><strong>{{ row.assignment_title || row.assignment_type }}</strong><small>{{ institutionForBranch(row.school_branch) }} · {{ branchLabel(row.school_branch) }} · {{ offeringLabel(row.program_offering) }} · {{ row.student_group || 'All Class Arms' }} · {{ row.course || 'Whole class' }}</small></span><div class="assignment-actions"><EdgeStatusBadge :label="row.enabled ? 'Active' : 'Disabled'" :status="row.enabled ? 'active' : 'disabled'" :tone="row.enabled ? 'success' : 'danger'" /><button type="button" class="edge-button" @click="openAssignment(row.name)">Open</button></div></article></div></article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const BRANCH_ONLY_SCOPE = "Branch Access Only";
const CLASS_SCOPE = "Class / Programme Offering";
const CLASS_ARM_SCOPE = "Class Arm";
const COURSE_REQUIRED_TYPES = new Set(["Subject Teacher", "Lecturer", "Tutor", "Practical Instructor", "Assistant Instructor"]);
const blankData = () => ({ allowed_branches: [], selected_branches: [], instructors: [], selected_instructor: null, offerings: [], groups: [], courses: [], course_map: {}, assignments: [], branch_assignments: [], assignment_types: [], assignment_scopes: [], permissions: {} });
const blankForm = (preset = {}) => ({ instructor: preset.instructor || "", branches: preset.branches || [], assignment_scope: preset.assignment_scope || CLASS_ARM_SCOPE, assignment_type: preset.assignment_type || "Subject Teacher", program_offerings: preset.program_offerings || [], student_groups: preset.student_groups || [], courses: preset.courses || [], valid_from: frappe.datetime?.get_today?.() || "", valid_to: "", enabled: 1, notes: "" });

export default {
	name: "EduEdgeInstructorAssignments",
	data() { return { menuItems: EDUEDGE_MENU_ITEMS, loading: true, loaded: false, previewing: false, saving: false, error: "", saveError: "", data: blankData(), form: blankForm(), preview: null, routePreset: {} }; },
	computed: {
		branchOnlyScope() { return BRANCH_ONLY_SCOPE; }, classScope() { return CLASS_SCOPE; }, classArmScope() { return CLASS_ARM_SCOPE; },
		courseSingular() { return frappe.eduedge?.term?.("course", { fallback: __("Subject / Course") }) || __("Subject / Course"); },
		coursePlural() { return frappe.eduedge?.term?.("course", { plural: true, fallback: __("Subjects / Courses") }) || __("Subjects / Courses"); },
		activeInstitutionName() { return this.selectedInstitutionCount > 1 ? `${this.selectedInstitutionCount} Institutions` : (this.branchGroups.find((group) => group.rows.some((row) => this.form.branches.includes(row.name)))?.institution_name || "Instructor Assignments"); },
		branchGroups() {
			const groups = new Map();
			for (const row of this.data.allowed_branches || []) {
				const key = row.institution || "unclassified";
				if (!groups.has(key)) groups.set(key, { institution: key, institution_name: row.institution_name || key, rows: [] });
				groups.get(key).rows.push(row);
			}
			return [...groups.values()].sort((a,b) => a.institution_name.localeCompare(b.institution_name));
		},
		selectedInstitutionCount() { return new Set((this.data.allowed_branches || []).filter((row) => this.form.branches.includes(row.name)).map((row) => row.institution).filter(Boolean)).size; },
		availableOfferings() { return (this.data.offerings || []).filter((row) => this.form.branches.includes(row.school_branch)); },
		availableGroups() { return (this.data.groups || []).filter((row) => this.form.program_offerings.includes(row.eduedge_program_offering)); },
		availableCourses() {
			const selectedPrograms = new Set(this.availableOfferings.filter((row) => this.form.program_offerings.includes(row.name)).map((row) => row.program));
			return (this.data.courses || []).filter((course) => [...selectedPrograms].some((program) => (this.data.course_map?.[program] || []).includes(course.name)));
		},
		courseRequired() { return COURSE_REQUIRED_TYPES.has(this.form.assignment_type); },
		canPreview() { return Boolean(this.form.instructor && this.form.branches.length && (this.form.assignment_scope === BRANCH_ONLY_SCOPE || (this.form.program_offerings.length && (this.form.assignment_scope !== CLASS_ARM_SCOPE || this.form.student_groups.length) && (!this.courseRequired || this.form.courses.length)))); },
		canSaveBatch() { return Boolean(this.preview && !this.preview.conflict_count && (this.preview.create_count || this.preview.existing_count || this.form.assignment_scope === BRANCH_ONLY_SCOPE)); },
		saveButtonLabel() { return this.form.assignment_scope === BRANCH_ONLY_SCOPE ? "Save Branch Eligibility" : "Save Instructor Assignments"; },
	},
	mounted() {
		const params = new URLSearchParams(window.location.search || "");
		this.routePreset = { instructor: params.get("instructor") || "", branches: params.get("branch") ? [params.get("branch")] : [] };
		this.form = blankForm(this.routePreset);
		this.load();
	},
	methods: {
		openRoute: openEduEdgeRoute,
		institutionLabel(name) { return this.branchGroups.find((group) => group.institution === name)?.institution_name || name || "Institution"; },
		branchLabel(name) { return this.data.allowed_branches.find((row) => row.name === name)?.branch_name || name || "Branch"; },
		institutionForBranch(name) { const row = this.data.allowed_branches.find((branch) => branch.name === name); return row?.institution_name || row?.institution || "Institution"; },
		offeringLabel(name) { return this.data.offerings.find((row) => row.name === name)?.offering_title || name || "Class"; },
		selectedBranchCount(rows) { return rows.filter((row) => this.form.branches.includes(row.name)).length; },
		courseCoverage(course) { return this.form.program_offerings.filter((offeringName) => { const offering = this.data.offerings.find((row) => row.name === offeringName); return offering && (this.data.course_map?.[offering.program] || []).includes(course); }).length; },
		async load() {
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.instructor_assignments.get_instructor_assignments_page", { instructor: this.form.instructor || undefined, branches: this.form.branches, offerings: this.form.program_offerings });
				this.data = response.message || blankData();
				if (!this.form.branches.length && this.data.selected_branches?.length) this.form.branches = [...this.data.selected_branches];
				this.loaded = true;
			} catch (error) { this.error = error?.message || "Instructor Assignments could not be loaded."; }
			finally { this.loading = false; }
		},
		invalidatePreview() { this.preview = null; this.saveError = ""; },
		async instructorChanged() { this.invalidatePreview(); await this.load(); },
		async scopeChanged() { if (this.form.assignment_scope === CLASS_SCOPE) this.form.student_groups = []; if (this.form.assignment_scope === BRANCH_ONLY_SCOPE) { this.form.program_offerings = []; this.form.student_groups = []; this.form.courses = []; } this.invalidatePreview(); },
		async refreshContext() { this.invalidatePreview(); await this.load(); this.form.program_offerings = this.form.program_offerings.filter((name) => this.availableOfferings.some((row) => row.name === name)); this.form.student_groups = this.form.student_groups.filter((name) => this.availableGroups.some((row) => row.name === name)); this.form.courses = this.form.courses.filter((name) => this.availableCourses.some((row) => row.name === name)); },
		toggleBranch(name) { this.form.branches = this.form.branches.includes(name) ? this.form.branches.filter((value) => value !== name) : [...this.form.branches, name]; this.refreshContext(); },
		selectAllBranches() { this.form.branches = this.data.allowed_branches.map((row) => row.name); this.refreshContext(); }, clearBranches() { this.form.branches = []; this.form.program_offerings = []; this.form.student_groups = []; this.form.courses = []; this.invalidatePreview(); },
		toggleOffering(name) { this.form.program_offerings = this.form.program_offerings.includes(name) ? this.form.program_offerings.filter((value) => value !== name) : [...this.form.program_offerings, name]; this.refreshContext(); }, selectAllOfferings() { this.form.program_offerings = this.availableOfferings.map((row) => row.name); this.refreshContext(); }, clearOfferings() { this.form.program_offerings = []; this.form.student_groups = []; this.form.courses = []; this.invalidatePreview(); },
		toggleGroup(name) { this.form.student_groups = this.form.student_groups.includes(name) ? this.form.student_groups.filter((value) => value !== name) : [...this.form.student_groups, name]; this.invalidatePreview(); }, selectAllGroups() { this.form.student_groups = this.availableGroups.map((row) => row.name); this.invalidatePreview(); }, clearGroups() { this.form.student_groups = []; this.invalidatePreview(); },
		toggleCourse(name) { this.form.courses = this.form.courses.includes(name) ? this.form.courses.filter((value) => value !== name) : [...this.form.courses, name]; this.invalidatePreview(); }, selectAllCourses() { this.form.courses = this.availableCourses.map((row) => row.name); this.invalidatePreview(); }, clearCourses() { this.form.courses = []; this.invalidatePreview(); },
		payload() { return { ...this.form }; },
		async previewBatch() { if (!this.canPreview) return; this.previewing = true; this.saveError = ""; try { const response = await frappe.call({ method: "eduedge.api.instructor_assignments.preview_instructor_assignment_batch", type: "POST", args: { payload: JSON.stringify(this.payload()) } }); this.preview = response.message || null; } catch (error) { this.preview = null; this.saveError = error?.message || "Instructor Assignment batch could not be previewed."; } finally { this.previewing = false; } },
		async saveBatch() { if (!this.canSaveBatch) return; this.saving = true; this.saveError = ""; try { const response = await frappe.call({ method: "eduedge.api.instructor_assignments.save_instructor_assignment_batch", type: "POST", args: { payload: JSON.stringify(this.payload()) } }); const summary = response.message?.summary || {}; frappe.show_alert({ message: __(`${summary.assignments_created || 0} Instructor Assignment(s) created across ${summary.institutions_covered || this.selectedInstitutionCount} Institution(s)`), indicator: "green" }); this.preview = null; await this.load(); } catch (error) { this.saveError = error?.message || "Instructor Assignments could not be saved."; } finally { this.saving = false; } },
		resetForm() { this.form = blankForm(this.routePreset); this.preview = null; this.saveError = ""; this.load(); },
		openInstructors() { window.location.href = "/app/eduedge-instructors"; }, openAssignment(name) { window.open(`/app/eduedge-instructor-assignment/${encodeURIComponent(name)}`, "_blank", "noopener,noreferrer"); },
	},
};
</script>

<style scoped>
.assignment-panel,.selection-section,.institution-group { display:grid; gap:1rem; align-content:start; padding:1rem; border:1px solid var(--border-color); border-radius:12px; background:var(--card-bg); }.selection-section { margin-top:1rem; background:var(--control-bg); }.assignment-heading,.assignment-actions,.institution-group-title { display:flex; align-items:center; justify-content:space-between; gap:.75rem; flex-wrap:wrap; }.assignment-heading h2,.assignment-heading h3 { margin:.2rem 0 0; }.assignment-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.75rem; }.assignment-grid label,.notes { display:grid; gap:.35rem; font-weight:600; }.assignment-grid .wide { grid-column:1/-1; }.institution-groups { display:grid; gap:1rem; }.institution-group { background:var(--card-bg); }.institution-group-title span { color:var(--text-muted); }.choice-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(15rem,1fr)); gap:.65rem; }.choice-card { display:flex; align-items:flex-start; gap:.6rem; padding:.75rem; border:1px solid var(--border-color); border-radius:8px; background:var(--card-bg); font-weight:500; }.choice-card span,.register-list article>span { display:grid; gap:.15rem; }.choice-card small,.register-list small { color:var(--text-muted); }.preview { display:grid; gap:.75rem; margin-top:1rem; }.preview-metrics { display:grid; grid-template-columns:repeat(auto-fit,minmax(8rem,1fr)); gap:.65rem; }.preview-metrics>div { display:grid; gap:.2rem; padding:.75rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); }.preview-metrics span { color:var(--text-muted); font-size:.75rem; }.preview-metrics strong { font-size:1.3rem; }.preview-list,.register-list { display:grid; gap:.6rem; }.preview-list { padding:.75rem; border:1px solid var(--border-color); border-radius:8px; }.preview-list.danger { border-color:var(--red-400); }.preview-list span { display:block; }.register-layout { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1rem; margin-top:1rem; }.register-list article { display:flex; align-items:center; justify-content:space-between; gap:.75rem; padding:.7rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); }.assignment-error { color:var(--red-600,#b42318); }.notes { margin-top:1rem; } @media (max-width:900px) { .assignment-grid,.register-layout { grid-template-columns:1fr; } } @media (max-width:600px) { .choice-grid { grid-template-columns:1fr; }.assignment-heading,.institution-group-title,.register-list article { align-items:stretch; flex-direction:column; } }
</style>
