<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="activeInstitutionName"
		:branch-name="'Teacher Assignments'"
		:menu-items="menuItems"
		active-route="/app/eduedge-instructor-assignments"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="People & Academic Operations"
					title="Teacher Assignments"
					subtitle="Assign one teacher to multiple Branches, Classes, Class Arms and Subjects in one controlled operation. Branch eligibility is maintained automatically."
					action-label="Manage Teachers"
					@action="openInstructors"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loaded" message="Loading Teacher Assignments..." :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loaded" title="Teacher Assignments could not load" :message="error" action-label="Try again" @retry="load" />
			<template v-else>
				<p v-if="error" class="teacher-assignment-error">{{ error }}</p>
				<section class="teacher-assignment-panel">
					<div class="teacher-assignment-heading">
						<div><p class="edge-eyebrow">Unified assignment builder</p><h2>Who and what should this teacher manage?</h2></div>
						<button type="button" class="edge-button" @click="resetForm">Reset</button>
					</div>

					<div class="teacher-assignment-grid">
						<label class="wide">
							<span>Teacher / Instructor *</span>
							<select v-model="form.instructor" class="form-control" @change="instructorChanged">
								<option value="">Select Teacher / Instructor</option>
								<option v-for="row in data.instructors" :key="row.name" :value="row.name">{{ row.instructor_name || row.name }}{{ row.department ? ` · ${row.department}` : '' }}</option>
							</select>
						</label>
						<label>
							<span>Assignment Scope *</span>
							<select v-model="form.assignment_scope" class="form-control" @change="scopeChanged">
								<option v-for="value in data.assignment_scopes" :key="value" :value="value">{{ value }}</option>
							</select>
						</label>
						<label>
							<span>Assignment Type *</span>
							<select v-model="form.assignment_type" class="form-control" @change="invalidatePreview">
								<option v-for="value in data.assignment_types" :key="value" :value="value">{{ value }}</option>
							</select>
						</label>
						<label><span>Valid From</span><input v-model="form.valid_from" type="date" class="form-control" @change="invalidatePreview" /></label>
						<label><span>Valid To</span><input v-model="form.valid_to" type="date" class="form-control" @change="invalidatePreview" /></label>
						<label><span>Status</span><select v-model.number="form.enabled" class="form-control" @change="invalidatePreview"><option :value="1">Active</option><option :value="0">Disabled</option></select></label>
					</div>

					<section class="teacher-selection-section">
						<div class="teacher-assignment-heading">
							<div><p class="edge-eyebrow">Step 1</p><h3>Branches / Campuses</h3><small>Select one or several campuses within the teacher's Institution.</small></div>
						<div class="teacher-assignment-actions"><button type="button" class="edge-button" @click="selectAllBranches">Select available</button><button type="button" class="edge-button" @click="clearBranches">Clear</button></div>
						</div>
						<div class="teacher-checkbox-grid">
							<label v-for="row in availableBranches" :key="row.name" class="teacher-choice-card">
								<input type="checkbox" :checked="form.branches.includes(row.name)" @change="toggleBranch(row.name)" />
								<span><strong>{{ row.branch_name || row.name }}</strong><small>{{ row.institution_name || row.institution }}</small></span>
							</label>
						</div>
						<EdgeEmptyState v-if="form.instructor && !availableBranches.length" title="No Branch available" description="The selected Teacher does not share an Institution with any Branch available to your user." />
					</section>

					<template v-if="form.assignment_scope !== branchOnlyScope">
						<section class="teacher-selection-section">
							<div class="teacher-assignment-heading">
								<div><p class="edge-eyebrow">Step 2</p><h3>Classes / Programme Offerings</h3><small>Select multiple Classes across the selected Branches.</small></div>
								<div class="teacher-assignment-actions"><button type="button" class="edge-button" @click="selectAllOfferings">Select available</button><button type="button" class="edge-button" @click="clearOfferings">Clear</button></div>
							</div>
							<EdgeEmptyState v-if="!form.branches.length" title="Select a Branch first" description="Classes are loaded only from the selected Branches." />
							<div v-else class="teacher-checkbox-grid">
								<label v-for="row in availableOfferings" :key="row.name" class="teacher-choice-card">
									<input type="checkbox" :checked="form.program_offerings.includes(row.name)" @change="toggleOffering(row.name)" />
									<span><strong>{{ row.offering_title || row.name }}</strong><small>{{ branchLabel(row.school_branch) }} · {{ row.academic_year }}{{ row.academic_term ? ` · ${row.academic_term}` : '' }}</small></span>
								</label>
							</div>
						</section>

						<section v-if="form.assignment_scope === classArmScope" class="teacher-selection-section">
							<div class="teacher-assignment-heading">
								<div><p class="edge-eyebrow">Step 3</p><h3>Class Arms</h3><small>Select one or several Class Arms from the chosen Classes.</small></div>
								<div class="teacher-assignment-actions"><button type="button" class="edge-button" @click="selectAllGroups">Select available</button><button type="button" class="edge-button" @click="clearGroups">Clear</button></div>
							</div>
							<EdgeEmptyState v-if="!form.program_offerings.length" title="Select a Class first" description="Class Arms are filtered to the selected Classes." />
							<div v-else class="teacher-checkbox-grid">
								<label v-for="row in availableGroups" :key="row.name" class="teacher-choice-card">
									<input type="checkbox" :checked="form.student_groups.includes(row.name)" @change="toggleGroup(row.name)" />
									<span><strong>{{ row.eduedge_display_name || row.student_group_name || row.name }}</strong><small>{{ offeringLabel(row.eduedge_program_offering) }} · {{ branchLabel(row.eduedge_school_branch) }}</small></span>
								</label>
							</div>
						</section>

						<section class="teacher-selection-section">
							<div class="teacher-assignment-heading">
								<div><p class="edge-eyebrow">{{ form.assignment_scope === classArmScope ? 'Step 4' : 'Step 3' }}</p><h3>{{ coursePlural }}</h3><small>Selected {{ coursePlural.toLowerCase() }} are applied only to Classes where they are configured.</small></div>
								<div class="teacher-assignment-actions"><button type="button" class="edge-button" @click="selectAllCourses">Select available</button><button type="button" class="edge-button" @click="clearCourses">Clear</button></div>
							</div>
							<EdgeActionBar v-if="courseRequired" :label="`${courseSingular} selection is required for ${form.assignment_type}.`" />
							<EdgeEmptyState v-if="!form.program_offerings.length" :title="`Select a Class before choosing ${coursePlural}`" :description="`${coursePlural} come from each selected Class curriculum.`" />
							<div v-else class="teacher-checkbox-grid">
								<label v-for="row in availableCourses" :key="row.name" class="teacher-choice-card">
									<input type="checkbox" :checked="form.courses.includes(row.name)" @change="toggleCourse(row.name)" />
									<span><strong>{{ row.course_name || row.name }}</strong><small>Configured in {{ courseCoverage(row.name) }} selected Class{{ courseCoverage(row.name) === 1 ? '' : 'es' }}</small></span>
								</label>
							</div>
						</section>
					</template>

					<label class="teacher-notes"><span>Notes</span><textarea v-model.trim="form.notes" rows="3" class="form-control" placeholder="Optional assignment or handover note" @input="invalidatePreview"></textarea></label>

					<EdgeActionBar label="Preview validates every selected combination. Exact existing assignments are skipped; conflicting overlaps block the batch.">
						<template #actions>
							<button type="button" class="edge-button" :disabled="previewing || !canPreview" @click="previewBatch">{{ previewing ? 'Checking...' : 'Preview Assignment Batch' }}</button>
							<button type="button" class="edge-button edge-button--primary" :disabled="saving || !canSaveBatch" @click="saveBatch">{{ saving ? 'Saving...' : saveButtonLabel }}</button>
						</template>
					</EdgeActionBar>
					<p v-if="saveError" class="teacher-assignment-error">{{ saveError }}</p>

					<section v-if="preview" class="teacher-preview">
						<div class="teacher-preview-metrics">
							<div><span>Branches</span><strong>{{ preview.branch_count }}</strong></div>
							<div><span>Valid combinations</span><strong>{{ preview.valid_combinations }}</strong></div>
							<div><span>New records</span><strong>{{ preview.create_count }}</strong></div>
							<div><span>Already existing</span><strong>{{ preview.existing_count }}</strong></div>
							<div><span>Invalid combinations skipped</span><strong>{{ preview.skipped_count }}</strong></div>
							<div><span>Conflicts</span><strong>{{ preview.conflict_count }}</strong></div>
						</div>
						<div v-if="preview.conflicts?.length" class="teacher-preview-list danger"><strong>Resolve these overlapping assignments first</strong><span v-for="row in preview.conflicts" :key="row.name">{{ row.label }} · {{ row.name }}</span></div>
						<div v-if="preview.skipped?.length" class="teacher-preview-list"><strong>Skipped because the {{ courseSingular.toLowerCase() }} is not configured for that Class</strong><span v-for="(row,index) in preview.skipped" :key="`${row.program_offering}-${row.course}-${index}`">{{ offeringLabel(row.program_offering) }} · {{ row.course }}</span></div>
					</section>
				</section>

				<section v-if="form.instructor" class="teacher-register-layout">
					<article class="teacher-assignment-panel">
						<div class="teacher-assignment-heading"><div><p class="edge-eyebrow">Background access</p><h2>Branch Access</h2></div><span>{{ data.branch_assignments.length }}</span></div>
						<EdgeEmptyState v-if="!data.branch_assignments.length" title="No Branch access" description="Saving the first assignment will create the required Branch eligibility." />
						<div v-else class="teacher-register-list"><article v-for="row in data.branch_assignments" :key="row.name"><span><strong>{{ branchLabel(row.school_branch) }}</strong><small>{{ row.is_primary ? 'Primary Branch' : 'Additional Branch' }} · {{ row.valid_from || 'No start restriction' }} → {{ row.valid_to || 'Open ended' }}</small></span><EdgeStatusBadge :label="row.enabled ? 'Active' : 'Disabled'" :status="row.enabled ? 'active' : 'disabled'" :tone="row.enabled ? 'success' : 'danger'" /></article></div>
					</article>
					<article class="teacher-assignment-panel">
						<div class="teacher-assignment-heading"><div><p class="edge-eyebrow">Academic responsibility</p><h2>Current Assignments</h2></div><span>{{ data.assignments.length }}</span></div>
						<EdgeEmptyState v-if="!data.assignments.length" title="No academic assignment" description="Use the builder above to assign Classes, Class Arms and Subjects." />
						<div v-else class="teacher-register-list"><article v-for="row in data.assignments" :key="row.name"><span><strong>{{ row.assignment_title || row.assignment_type }}</strong><small>{{ row.assignment_scope || classArmScope }} · {{ offeringLabel(row.program_offering) }} · {{ row.student_group || 'All Class Arms' }} · {{ row.course || 'Whole class' }}</small></span><div class="teacher-assignment-actions"><EdgeStatusBadge :label="row.enabled ? 'Active' : 'Disabled'" :status="row.enabled ? 'active' : 'disabled'" :tone="row.enabled ? 'success' : 'danger'" /><button type="button" class="edge-button" @click="openAssignment(row.name)">Open</button></div></article></div>
					</article>
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
const blankForm = (preset = {}) => ({ instructor: preset.instructor || "", branches: preset.branches || [], assignment_scope: CLASS_ARM_SCOPE, assignment_type: "Subject Teacher", program_offerings: [], student_groups: [], courses: [], valid_from: frappe.datetime?.get_today?.() || "", valid_to: "", enabled: 1, notes: "" });

export default {
	name: "EduEdgeInstructorAssignments",
	data() {
		const params = new URLSearchParams(window.location.search || "");
		const branch = params.get("branch") || "";
		return { menuItems: EDUEDGE_MENU_ITEMS, branchOnlyScope: BRANCH_ONLY_SCOPE, classScope: CLASS_SCOPE, classArmScope: CLASS_ARM_SCOPE, loading: true, loaded: false, previewing: false, saving: false, error: "", saveError: "", preview: null, data: blankData(), form: blankForm({ instructor: params.get("instructor") || "", branches: branch ? [branch] : [] }) };
	},
	computed: {
		selectedInstructor() { return this.data.instructors.find((row) => row.name === this.form.instructor) || null; },
		activeInstitutionName() { const row = this.availableBranches.find((branch) => this.form.branches.includes(branch.name)) || this.availableBranches[0]; return row?.institution_name || ""; },
		availableBranches() { const institution = this.selectedInstructor?.eduedge_institution; return (this.data.allowed_branches || []).filter((row) => !institution || row.institution === institution); },
		availableOfferings() { return (this.data.offerings || []).filter((row) => this.form.branches.includes(row.school_branch)); },
		availableGroups() { return (this.data.groups || []).filter((row) => this.form.program_offerings.includes(row.eduedge_program_offering)); },
		availableCourses() { const names = new Set(); for (const offeringName of this.form.program_offerings) { const offering = this.availableOfferings.find((row) => row.name === offeringName); for (const course of this.data.course_map?.[offering?.program] || []) names.add(course); } return (this.data.courses || []).filter((row) => names.has(row.name)); },
		courseSingular() { return frappe.eduedge?.term?.("course", { fallback: __("Subject / Course") }) || __("Subject / Course"); },
		coursePlural() { return frappe.eduedge?.term?.("course", { plural: true, fallback: __("Subjects / Courses") }) || __("Subjects / Courses"); },
		courseRequired() { return COURSE_REQUIRED_TYPES.has(this.form.assignment_type); },
		canPreview() { if (!this.form.instructor || !this.form.branches.length) return false; if (this.form.assignment_scope === BRANCH_ONLY_SCOPE) return true; if (!this.form.program_offerings.length) return false; if (this.form.assignment_scope === CLASS_ARM_SCOPE && !this.form.student_groups.length) return false; if (this.courseRequired && !this.form.courses.length) return false; return true; },
		canSaveBatch() { return Boolean(this.preview && !this.preview.conflict_count && this.data.permissions?.can_manage_branch_access && (this.form.assignment_scope === BRANCH_ONLY_SCOPE || this.data.permissions?.can_create)); },
		saveButtonLabel() { if (!this.preview) return "Preview before saving"; if (this.form.assignment_scope === BRANCH_ONLY_SCOPE) return `Save ${this.preview.branch_count} Branch Access Record${this.preview.branch_count === 1 ? '' : 's'}`; return `Create ${this.preview.create_count} Assignment${this.preview.create_count === 1 ? '' : 's'}`; },
	},
	async mounted() { await this.load(); },
	methods: {
		openRoute: openEduEdgeRoute,
		branchLabel(name) { return this.data.allowed_branches.find((row) => row.name === name)?.branch_name || name || ""; },
		offeringLabel(name) { return this.data.offerings.find((row) => row.name === name)?.offering_title || name || ""; },
		courseCoverage(course) { return this.form.program_offerings.filter((name) => { const offering = this.availableOfferings.find((row) => row.name === name); return (this.data.course_map?.[offering?.program] || []).includes(course); }).length; },
		payload() { return { ...this.form, branches: [...this.form.branches], program_offerings: [...this.form.program_offerings], student_groups: [...this.form.student_groups], courses: [...this.form.courses] }; },
		async load() {
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.teacher_assignments.get_teacher_assignments_page", { instructor: this.form.instructor || undefined, branches: JSON.stringify(this.form.branches || []), offerings: JSON.stringify(this.form.program_offerings || []) });
				this.data = response.message || blankData();
				this.form.branches = (this.form.branches || []).filter((name) => this.data.selected_branches.includes(name));
				if (!this.form.branches.length && this.data.selected_branches.length) this.form.branches = [...this.data.selected_branches];
				this.form.program_offerings = this.form.program_offerings.filter((name) => this.data.offerings.some((row) => row.name === name));
				this.form.student_groups = this.form.student_groups.filter((name) => this.data.groups.some((row) => row.name === name));
				this.form.courses = this.form.courses.filter((name) => this.availableCourses.some((row) => row.name === name));
				this.loaded = true;
			} catch (error) { this.error = error?.message || "Teacher Assignments could not be loaded."; }
			finally { this.loading = false; }
		},
		invalidatePreview() { this.preview = null; this.saveError = ""; },
		async instructorChanged() { const institution = this.selectedInstructor?.eduedge_institution; this.form.branches = this.form.branches.filter((name) => this.data.allowed_branches.find((row) => row.name === name)?.institution === institution); this.form.program_offerings = []; this.form.student_groups = []; this.form.courses = []; this.invalidatePreview(); await this.load(); },
		async scopeChanged() { if (this.form.assignment_scope === BRANCH_ONLY_SCOPE) { this.form.program_offerings = []; this.form.student_groups = []; this.form.courses = []; } else if (this.form.assignment_scope === CLASS_SCOPE) this.form.student_groups = []; this.invalidatePreview(); },
		async toggleBranch(name) { this.form.branches = this.form.branches.includes(name) ? this.form.branches.filter((value) => value !== name) : [...this.form.branches, name]; this.form.program_offerings = []; this.form.student_groups = []; this.form.courses = []; this.invalidatePreview(); await this.load(); },
		async selectAllBranches() { this.form.branches = this.availableBranches.map((row) => row.name); this.form.program_offerings = []; this.form.student_groups = []; this.form.courses = []; this.invalidatePreview(); await this.load(); },
		async clearBranches() { this.form.branches = []; this.form.program_offerings = []; this.form.student_groups = []; this.form.courses = []; this.invalidatePreview(); await this.load(); },
		toggleOffering(name) { this.form.program_offerings = this.form.program_offerings.includes(name) ? this.form.program_offerings.filter((value) => value !== name) : [...this.form.program_offerings, name]; this.form.student_groups = this.form.student_groups.filter((group) => this.availableGroups.some((row) => row.name === group)); this.form.courses = this.form.courses.filter((course) => this.availableCourses.some((row) => row.name === course)); this.invalidatePreview(); },
		selectAllOfferings() { this.form.program_offerings = this.availableOfferings.map((row) => row.name); this.invalidatePreview(); },
		clearOfferings() { this.form.program_offerings = []; this.form.student_groups = []; this.form.courses = []; this.invalidatePreview(); },
		toggleGroup(name) { this.form.student_groups = this.form.student_groups.includes(name) ? this.form.student_groups.filter((value) => value !== name) : [...this.form.student_groups, name]; this.invalidatePreview(); },
		selectAllGroups() { this.form.student_groups = this.availableGroups.map((row) => row.name); this.invalidatePreview(); },
		clearGroups() { this.form.student_groups = []; this.invalidatePreview(); },
		toggleCourse(name) { this.form.courses = this.form.courses.includes(name) ? this.form.courses.filter((value) => value !== name) : [...this.form.courses, name]; this.invalidatePreview(); },
		selectAllCourses() { this.form.courses = this.availableCourses.map((row) => row.name); this.invalidatePreview(); },
		clearCourses() { this.form.courses = []; this.invalidatePreview(); },
		async previewBatch() { if (!this.canPreview) return; this.previewing = true; this.saveError = ""; try { const response = await frappe.call({ method: "eduedge.api.teacher_assignments.preview_teacher_assignment_batch", type: "POST", args: { payload: JSON.stringify(this.payload()) } }); this.preview = response.message || null; } catch (error) { this.preview = null; this.saveError = error?.message || "Assignment batch could not be previewed."; } finally { this.previewing = false; } },
		async saveBatch() { if (!this.canSaveBatch) return; this.saving = true; this.saveError = ""; try { const response = await frappe.call({ method: "eduedge.api.teacher_assignments.save_teacher_assignment_batch", type: "POST", args: { payload: JSON.stringify(this.payload()) } }); const summary = response.message?.summary || {}; frappe.show_alert({ message: __(`${summary.assignments_created || 0} assignments created; ${summary.branches_created_or_updated || 0} Branch access records confirmed`), indicator: "green" }); this.preview = null; await this.load(); } catch (error) { this.saveError = error?.message || "Teacher Assignment batch could not be saved."; } finally { this.saving = false; } },
		resetForm() { const instructor = this.form.instructor; const branches = [...this.form.branches]; this.form = blankForm({ instructor, branches }); this.preview = null; this.saveError = ""; },
		openInstructors() { window.location.href = "/app/eduedge-instructors"; },
		openAssignment(name) { window.open(`/app/eduedge-instructor-assignment/${encodeURIComponent(name)}`, "_blank", "noopener,noreferrer"); },
	},
};
</script>

<style scoped>
.teacher-assignment-panel,.teacher-selection-section { display:grid; gap:1rem; padding:1rem; border:1px solid var(--border-color); border-radius:12px; background:var(--card-bg); }.teacher-selection-section { margin-top:1rem; background:var(--control-bg); }.teacher-assignment-heading,.teacher-assignment-actions { display:flex; align-items:center; justify-content:space-between; gap:.75rem; flex-wrap:wrap; }.teacher-assignment-heading h2,.teacher-assignment-heading h3 { margin:.15rem 0 0; }.teacher-assignment-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.75rem; }.teacher-assignment-grid label,.teacher-notes { display:grid; gap:.35rem; font-weight:600; }.teacher-assignment-grid .wide { grid-column:span 2; }.teacher-checkbox-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(15rem,1fr)); gap:.65rem; }.teacher-choice-card { display:flex; align-items:flex-start; gap:.65rem; padding:.75rem; border:1px solid var(--border-color); border-radius:8px; background:var(--card-bg); cursor:pointer; }.teacher-choice-card:has(input:checked) { border-color:var(--primary); }.teacher-choice-card span,.teacher-register-list article>span { display:grid; gap:.15rem; }.teacher-choice-card small,.teacher-register-list small,.teacher-assignment-heading small { color:var(--text-muted); }.teacher-notes { margin-top:1rem; }.teacher-preview { display:grid; gap:.75rem; padding:1rem; border:1px solid var(--border-color); border-radius:10px; background:var(--control-bg); }.teacher-preview-metrics { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:.65rem; }.teacher-preview-metrics div { display:grid; gap:.2rem; padding:.65rem; border-radius:8px; background:var(--card-bg); }.teacher-preview-metrics span { color:var(--text-muted); font-size:.78rem; }.teacher-preview-metrics strong { font-size:1.25rem; }.teacher-preview-list { display:grid; gap:.3rem; padding:.75rem; border-radius:8px; background:var(--card-bg); }.teacher-preview-list.danger { border:1px solid var(--red-300,#fecdca); color:var(--red-700,#b42318); }.teacher-register-layout { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1rem; margin-top:1rem; }.teacher-register-list { display:grid; gap:.65rem; }.teacher-register-list article { display:flex; align-items:center; justify-content:space-between; gap:.75rem; padding:.75rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); }.teacher-assignment-error { color:var(--red-600,#b42318); } @media (max-width:1000px) { .teacher-preview-metrics { grid-template-columns:repeat(3,minmax(0,1fr)); }.teacher-register-layout { grid-template-columns:1fr; } } @media (max-width:760px) { .teacher-assignment-grid,.teacher-preview-metrics { grid-template-columns:1fr; }.teacher-assignment-grid .wide { grid-column:auto; }.teacher-register-list article { align-items:stretch; flex-direction:column; } }
</style>
