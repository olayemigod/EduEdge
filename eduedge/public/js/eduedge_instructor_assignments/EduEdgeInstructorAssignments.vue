<template>
	<EdgeAppShell product="eduedge" title="EduEdge" :tenant-name="data.selected_branch?.institution_name || ''" :branch-name="data.selected_branch?.branch_name || 'Instructor Assignments'" :menu-items="menuItems" active-route="/app/eduedge-instructor-assignments" @navigate="openRoute">
		<EdgePageLayout>
			<template #header><EdgePageHeader eyebrow="Academic Operations" title="Instructor Assignments" subtitle="Assign eligible instructors to a Programme Offering, Class Arm and Course without exposing background Branch-governance records." :action-label="canCreate ? 'New Assignment' : ''" @action="newAssignment" /></template>
			<EdgeLoadingState v-if="loading && !loaded" message="Loading instructor assignments..." :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loaded" title="Instructor Assignments could not load" :message="error" action-label="Try again" @retry="load" />
			<template v-else>
				<EdgeFilterBar title="Academic assignment context">
					<div class="assignment-filters">
						<label><span>Branch / Campus</span><select v-model="filters.branch" class="form-control" @change="branchChanged"><option v-for="row in data.allowed_branches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option></select></label>
						<label><span>Programme Offering</span><select v-model="filters.offering" class="form-control" @change="offeringChanged"><option value="">All offerings</option><option v-for="row in data.offerings" :key="row.name" :value="row.name">{{ row.offering_title || row.name }}</option></select></label>
						<label><span>Class Arm / Student Group</span><select v-model="filters.student_group" class="form-control" @change="groupChanged"><option value="">All Class Arms</option><option v-for="row in data.groups" :key="row.name" :value="row.name">{{ row.eduedge_display_name || row.student_group_name || row.name }}</option></select></label>
					</div>
					<template #actions><button type="button" class="edge-button edge-button--primary" @click="load">Refresh</button></template>
				</EdgeFilterBar>
				<p v-if="error" class="assignment-error">{{ error }}</p>
				<section class="assignment-layout">
					<article class="assignment-panel">
						<div class="assignment-heading"><div><p class="edge-eyebrow">Teaching responsibility</p><h2>Current Assignments</h2></div><button v-if="canCreate" type="button" class="edge-button" @click="newAssignment">New Assignment</button></div>
						<EdgeEmptyState v-if="!data.assignments.length" title="No Instructor Assignment" description="Assign an eligible Instructor to the selected academic context." />
						<div v-else class="assignment-list"><button v-for="row in data.assignments" :key="row.name" type="button" class="assignment-card" :class="{ 'is-selected': draft.name === row.name }" @click="editAssignment(row.name)"><span><strong>{{ row.assignment_title || row.instructor_name || row.instructor }}</strong><small>{{ row.assignment_type }} · {{ row.student_group }} · {{ row.course || 'Whole class' }}</small></span><EdgeStatusBadge :label="row.enabled ? 'Active' : 'Disabled'" :status="row.enabled ? 'active' : 'disabled'" :tone="row.enabled ? 'success' : 'danger'" /></button></div>
					</article>
					<article class="assignment-panel editor">
						<div class="assignment-heading"><div><p class="edge-eyebrow">Assignment editor</p><h2>{{ draft.name ? draft.assignment_title || 'Edit Assignment' : 'New Instructor Assignment' }}</h2></div><div class="assignment-actions"><button type="button" class="edge-button" @click="openInstructors">Manage Instructors</button><button type="button" class="edge-button edge-button--primary" :disabled="saving || !canSave" @click="save">{{ saving ? 'Saving...' : 'Save assignment' }}</button></div></div>
						<section class="context-card"><div><span>Institution</span><strong>{{ data.selected_branch?.institution_name || draft.institution || 'Not resolved' }}</strong></div><div><span>Academic Session</span><strong>{{ draft.academic_year || data.selected_offering?.academic_year || 'Select an Offering' }}</strong></div><div><span>Term / Semester</span><strong>{{ draft.academic_term || data.selected_offering?.academic_term || 'Session-wide' }}</strong></div></section>
						<div class="assignment-grid">
							<label><span>Branch / Campus *</span><select v-model="draft.school_branch" class="form-control" :disabled="!canEdit" @change="draftBranchChanged"><option v-for="row in data.allowed_branches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option></select></label>
							<label><span>Programme Offering *</span><select v-model="draft.program_offering" class="form-control" :disabled="!canEdit" @change="draftOfferingChanged"><option value="">Select Offering</option><option v-for="row in data.offerings" :key="row.name" :value="row.name">{{ row.offering_title || row.name }}</option></select></label>
							<label><span>Class Arm / Student Group *</span><select v-model="draft.student_group" class="form-control" :disabled="!canEdit || !draft.program_offering" @change="draftGroupChanged"><option value="">Select Class Arm</option><option v-for="row in data.groups" :key="row.name" :value="row.name">{{ row.eduedge_display_name || row.student_group_name || row.name }}</option></select></label>
							<label><span>Instructor *</span><select v-model="draft.instructor" class="form-control" :disabled="!canEdit"><option value="">Select eligible Instructor</option><option v-for="row in data.instructors" :key="row.name" :value="row.name">{{ row.instructor_name || row.name }}</option></select></label>
							<label><span>Assignment type *</span><select v-model="draft.assignment_type" class="form-control" :disabled="!canEdit"><option v-for="value in assignmentTypes" :key="value">{{ value }}</option></select></label>
							<label><span>Course / Subject</span><select v-model="draft.course" class="form-control" :disabled="!canEdit"><option value="">Whole class / no specific course</option><option v-for="row in data.courses" :key="row.course" :value="row.course">{{ row.course }}</option></select></label>
							<label><span>Valid from</span><input v-model="draft.valid_from" type="date" class="form-control" :disabled="!canEdit" /></label>
							<label><span>Valid to</span><input v-model="draft.valid_to" type="date" class="form-control" :disabled="!canEdit" /></label>
							<label><span>Status</span><select v-model.number="draft.enabled" class="form-control" :disabled="!canEdit"><option :value="1">Active</option><option :value="0">Disabled</option></select></label>
							<label class="wide"><span>Notes</span><textarea v-model.trim="draft.notes" rows="3" class="form-control" :disabled="!canEdit"></textarea></label>
						</div>
						<EdgeActionBar label="Branch eligibility remains a background governance rule. This page records the actual academic responsibility used by classes, subjects and schedules."><template #actions><button type="button" class="edge-button" @click="openClassArms">Manage Class Arms</button><button type="button" class="edge-button" @click="openAcademicOperations">Academic Operations</button></template></EdgeActionBar>
						<p v-if="saveError" class="assignment-error">{{ saveError }}</p>
					</article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";
const assignmentTypes = ["Class Teacher", "Subject Teacher", "Lecturer", "Tutor", "Practical Instructor", "Assistant Instructor", "Form Teacher", "Head of Class / Level"];
const blankAssignment = (branch = "", preset = {}) => ({ name: "", assignment_title: "", instructor: preset.instructor || "", instructor_name: "", assignment_type: "Subject Teacher", enabled: 1, institution: "", school_branch: branch, program_offering: preset.offering || "", academic_year: "", academic_term: "", student_group: preset.student_group || "", course: "", valid_from: frappe.datetime?.get_today?.() || "", valid_to: "", notes: "" });
const blankData = () => ({ allowed_branches: [], selected_branch: {}, offerings: [], groups: [], courses: [], instructors: [], selected_offering: null, selected_group: null, assignments: [], assignment: null, permissions: {} });
export default {
	name: "EduEdgeInstructorAssignments",
	data() { const params = new URLSearchParams(window.location.search); const preset = { branch: params.get("branch") || "", offering: params.get("offering") || "", student_group: params.get("student_group") || "", instructor: params.get("instructor") || "" }; return { menuItems: EDUEDGE_MENU_ITEMS, assignmentTypes, preset, loading: true, loaded: false, saving: false, error: "", saveError: "", filters: { branch: preset.branch, offering: preset.offering, student_group: preset.student_group }, data: blankData(), draft: blankAssignment(preset.branch, preset) }; },
	computed: { canCreate() { return Boolean(this.data.permissions?.can_create); }, canEdit() { return this.draft.name ? Boolean(this.data.permissions?.can_write) : this.canCreate; }, canSave() { const needsCourse = ["Subject Teacher", "Lecturer", "Tutor", "Practical Instructor", "Assistant Instructor"].includes(this.draft.assignment_type); return Boolean(this.canEdit && this.draft.school_branch && this.draft.program_offering && this.draft.student_group && this.draft.instructor && (!needsCourse || this.draft.course)); } },
	mounted() { this.load(); },
	methods: {
		openRoute: openEduEdgeRoute,
		async load(assignment = "") { this.loading = true; this.error = ""; try { const response = await frappe.call("eduedge.api.people_operations.get_instructor_assignments_page", { branch: this.filters.branch || undefined, offering: this.filters.offering || undefined, student_group: this.filters.student_group || undefined, assignment: assignment || undefined }); this.data = response.message || blankData(); this.filters.branch = this.data.selected_branch?.name || this.filters.branch; if (assignment && this.data.assignment) this.draft = { ...blankAssignment(this.filters.branch, this.preset), ...this.data.assignment }; else if (!this.draft.name) { this.draft.school_branch = this.filters.branch; this.applySelectedContext(); } this.loaded = true; } catch (error) { this.error = error?.message || "Instructor Assignments could not be loaded."; } finally { this.loading = false; } },
		applySelectedContext() { const offering = this.data.selected_offering; if (offering) { this.draft.program_offering = offering.name; this.draft.institution = offering.institution; this.draft.academic_year = offering.academic_year; this.draft.academic_term = offering.academic_term || ""; } if (this.data.selected_group) this.draft.student_group = this.data.selected_group.name; },
		branchChanged() { this.filters.offering = ""; this.filters.student_group = ""; this.draft = blankAssignment(this.filters.branch, { instructor: this.preset.instructor }); this.load(); },
		offeringChanged() { this.filters.student_group = ""; this.draft = blankAssignment(this.filters.branch, { instructor: this.preset.instructor, offering: this.filters.offering }); this.load(); },
		groupChanged() { this.draft = blankAssignment(this.filters.branch, { instructor: this.preset.instructor, offering: this.filters.offering, student_group: this.filters.student_group }); this.load(); },
		newAssignment() { this.draft = blankAssignment(this.filters.branch, { instructor: this.preset.instructor, offering: this.filters.offering, student_group: this.filters.student_group }); this.applySelectedContext(); this.saveError = ""; },
		editAssignment(name) { this.load(name); },
		async refreshDraftOptions() { const response = await frappe.call("eduedge.api.people_operations.get_instructor_assignment_options", { branch: this.draft.school_branch, offering: this.draft.program_offering || undefined, student_group: this.draft.student_group || undefined }); this.data = { ...this.data, ...(response.message || {}) }; this.applySelectedContext(); },
		async draftBranchChanged() { this.draft.program_offering = ""; this.draft.student_group = ""; this.draft.course = ""; await this.refreshDraftOptions(); },
		async draftOfferingChanged() { this.draft.student_group = ""; this.draft.course = ""; await this.refreshDraftOptions(); },
		async draftGroupChanged() { this.draft.course = ""; await this.refreshDraftOptions(); },
		async save() { if (!this.canSave) return; this.saving = true; this.saveError = ""; try { const response = await frappe.call("eduedge.api.people_operations.save_instructor_assignment", { payload: JSON.stringify(this.draft) }); this.draft = { ...this.draft, ...(response.message || {}) }; frappe.show_alert({ message: __("Instructor Assignment saved"), indicator: "green" }); await this.load(this.draft.name); } catch (error) { this.saveError = error?.message || "Instructor Assignment could not be saved."; } finally { this.saving = false; } },
		openInstructors() { window.location.href = "/app/eduedge-instructors"; }, openClassArms() { window.location.href = "/app/eduedge-class-arms"; }, openAcademicOperations() { window.location.href = "/app/eduedge-academic-operations"; },
	},
};
</script>

<style scoped>
.assignment-filters,.assignment-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.75rem; width:100%; }.assignment-filters label,.assignment-grid label { display:grid; gap:.35rem; font-weight:600; }.assignment-layout { display:grid; grid-template-columns:minmax(18rem,.75fr) minmax(0,1.5fr); gap:1rem; margin-top:1rem; }.assignment-panel { display:grid; gap:1rem; align-content:start; padding:1rem; border:1px solid var(--border-color); border-radius:12px; background:var(--card-bg); }.assignment-heading,.assignment-actions { display:flex; align-items:center; justify-content:space-between; gap:.75rem; flex-wrap:wrap; }.assignment-heading h2 { margin:0; }.assignment-list { display:grid; gap:.65rem; }.assignment-card { display:flex; justify-content:space-between; align-items:center; gap:.75rem; padding:.75rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); text-align:left; }.assignment-card:hover,.assignment-card.is-selected { border-color:var(--primary); }.assignment-card span { display:grid; gap:.15rem; }.assignment-card small,.context-card span { color:var(--text-muted); }.context-card { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.75rem; padding:.8rem; border-radius:8px; background:var(--control-bg); }.context-card div { display:grid; gap:.2rem; }.assignment-grid .wide { grid-column:1/-1; }.assignment-error { color:var(--red-600,#b42318); } @media (max-width:1000px) { .assignment-layout { grid-template-columns:1fr; } } @media (max-width:760px) { .assignment-filters,.assignment-grid,.context-card { grid-template-columns:1fr; }.assignment-grid .wide { grid-column:auto; } }
</style>
