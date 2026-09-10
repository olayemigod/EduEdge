<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="activeContext.institution_name || ''"
		:branch-name="activeContext.branch_name || 'Academic Foundation'"
		:menu-items="menuItems"
		active-route="/app/eduedge-academic-foundation"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Academic Foundation"
					:title="`${departmentPlural}, ${programmePlural}, ${studentGroupPlural} and ${academicYearPlural}`"
					:subtitle="`Use Frappe Education's native ${departmentSingular} → ${programmeSingular} → ${studentGroupSingular} hierarchy. EduEdge adds Institution, Branch and calendar isolation without replacing the native masters.`"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading academic foundation..." :skeleton="true" />
			<EdgeErrorState v-else-if="error" title="Academic Foundation could not load" :message="error" action-label="Try again" @retry="load" />
			<template v-else>
				<EdgeFilterBar title="Institution context">
					<div class="eduedge-foundation-context-grid">
						<label>
							<span>Institution</span>
							<select v-model="selectedInstitution" class="form-control" @change="institutionChanged">
								<option value="">Select Institution</option>
								<option v-for="institution in data.institutions" :key="institution.name" :value="institution.name">{{ institution.institution_name }} · {{ institution.institution_type }}</option>
							</select>
						</label>
						<div class="eduedge-context-summary"><span>Native hierarchy</span><strong>{{ departmentSingular }} → {{ programmeSingular }} → {{ studentGroupSingular }}</strong><small>{{ activeContext.institution_type_name || "Institution type not selected" }}</small></div>
					</div>
					<template #actions>
						<button type="button" class="edge-button" @click="openDepartmentTree">{{ departmentPlural }}</button>
						<button type="button" class="edge-button" @click="openProgrammeList">{{ programmePlural }}</button>
						<button type="button" class="edge-button" @click="openCalendarList">All calendars</button>
						<button v-if="permissions.can_create_calendar" type="button" class="edge-button edge-button--primary" :disabled="!selectedInstitution" @click="createCalendar">New {{ academicYearSingular }} calendar</button>
					</template>
				</EdgeFilterBar>

				<EdgeEmptyState v-if="!selectedInstitution" title="Select an Institution" description="Choose an Institution to review its native academic hierarchy and calendar readiness." />
				<template v-else>
					<EdgeDashboardLayout min-column-width="11rem">
						<EdgeStatCard :label="departmentPlural" :value="data.readiness.department_count" helper="Native Department tree" />
						<EdgeStatCard :label="programmePlural" :value="data.readiness.programme_count" :helper="`Native ${programmePlural.toLowerCase()}`" />
						<EdgeStatCard :label="studentGroupPlural" :value="data.readiness.student_group_count" :helper="`Native ${studentGroupPlural.toLowerCase()}`" />
						<EdgeStatCard :label="academicYearPlural" :value="data.readiness.calendar_count" helper="Institution calendars" />
						<EdgeStatCard label="Foundation Readiness" :value="data.readiness.ready ? 'Ready' : 'Needs attention'" :tone="data.readiness.ready ? 'success' : 'warning'" :helper="`${data.readiness.issues.length} issue(s)`" />
					</EdgeDashboardLayout>

					<section class="eduedge-foundation-readiness">
						<div class="eduedge-card-heading">
							<div><p class="edge-eyebrow">Readiness</p><h2>{{ selectedInstitutionLabel }}</h2></div>
							<EdgeStatusBadge :label="data.readiness.ready ? 'Ready for academic operations' : 'Setup needs attention'" :status="data.readiness.ready ? 'ready' : 'attention'" :tone="data.readiness.ready ? 'success' : 'warning'" />
						</div>
						<div v-if="data.readiness.issues.length" class="eduedge-issue-list">
							<div v-for="issue in data.readiness.issues" :key="issue.code" class="eduedge-issue-row">
								<EdgeStatusBadge :label="issue.severity === 'danger' ? 'Required' : 'Review'" :status="issue.severity" :tone="issue.severity === 'danger' ? 'danger' : 'warning'" />
								<span>{{ issue.message }}</span>
							</div>
						</div>
						<p v-else class="eduedge-ready-copy">The native hierarchy and current Institution calendar are ready.</p>
					</section>

					<div class="eduedge-foundation-editor-grid">
						<section class="eduedge-foundation-card">
							<div class="eduedge-card-heading"><div><p class="edge-eyebrow">{{ departmentSingular }}</p><h2>{{ departmentDraft.name ? "Edit" : "Create" }} {{ departmentSingular }}</h2></div><button type="button" class="edge-button" @click="newDepartment">New</button></div>
							<EdgeEmptyState v-if="!permissions.can_create_department && !permissions.can_write_department" title="Read-only hierarchy" :description="`Your role can view ${departmentPlural.toLowerCase()} but cannot maintain them.`" />
							<template v-else>
								<label><span>Name</span><input v-model.trim="departmentDraft.department_name" class="form-control" /></label>
								<label><span>Parent {{ departmentSingular }}</span><select v-model="departmentDraft.parent_department" class="form-control"><option value="">Root of Institution</option><option v-for="row in parentDepartmentOptions" :key="row.name" :value="row.name">{{ indentedDepartmentName(row) }}</option></select></label>
								<label class="eduedge-check"><input v-model="departmentDraft.is_group" type="checkbox" /> Can contain child {{ departmentPlural.toLowerCase() }}</label>
								<button type="button" class="edge-button edge-button--primary" :disabled="!canSaveDepartment || saving === 'department'" @click="saveDepartment">{{ saving === "department" ? "Saving..." : `Save ${departmentSingular}` }}</button>
							</template>
						</section>

						<section class="eduedge-foundation-card">
							<div class="eduedge-card-heading"><div><p class="edge-eyebrow">{{ programmeSingular }}</p><h2>{{ programmeDraft.name ? "Edit" : "Create" }} {{ programmeSingular }}</h2></div><button type="button" class="edge-button" @click="newProgramme">New</button></div>
							<EdgeEmptyState v-if="!permissions.can_create_programme && !permissions.can_write_programme" title="Read-only catalogue" :description="`Your role can view ${programmePlural.toLowerCase()} but cannot maintain them.`" />
							<template v-else>
								<label><span>Name</span><input v-model.trim="programmeDraft.program_name" class="form-control" /></label>
								<label><span>Abbreviation</span><input v-model.trim="programmeDraft.program_abbreviation" class="form-control" /></label>
								<label><span>{{ departmentSingular }}</span><select v-model="programmeDraft.department" class="form-control"><option value="">Select {{ departmentSingular }}</option><option v-for="row in data.departments" :key="row.name" :value="row.name">{{ indentedDepartmentName(row) }}</option></select></label>
								<button type="button" class="edge-button edge-button--primary" :disabled="!canSaveProgramme || saving === 'programme'" @click="saveProgramme">{{ saving === "programme" ? "Saving..." : `Save ${programmeSingular}` }}</button>
								<p class="text-muted">Course rows and curriculum rules remain on the full native Program form.</p>
							</template>
						</section>
					</div>

					<section class="eduedge-foundation-list">
						<div class="eduedge-card-heading">
							<div><p class="edge-eyebrow">Configured native hierarchy</p><h2>{{ selectedInstitutionLabel }}</h2></div>
							<EdgeStatusBadge :label="`${data.departments.length} ${departmentPlural.toLowerCase()} · ${data.programmes.length} ${programmePlural.toLowerCase()} · ${data.student_groups.length} ${studentGroupPlural.toLowerCase()}`" status="hierarchy" tone="neutral" />
						</div>
						<EdgeEmptyState v-if="!flatDepartments.length" title="No native academic hierarchy" :description="`Create the first ${departmentSingular}, then add ${programmePlural.toLowerCase()} and ${studentGroupPlural.toLowerCase()}.`" />
						<div v-else class="eduedge-hierarchy-list">
							<article v-for="department in flatDepartments" :key="department.name" class="eduedge-hierarchy-department" :style="{ '--hierarchy-depth': department.depth }">
								<div class="eduedge-hierarchy-heading">
									<button type="button" class="eduedge-hierarchy-name" @click="editDepartment(department)"><strong>{{ department.department_name || department.name }}</strong><small>{{ department.parent_department ? `Child of ${department.parent_department}` : `Root ${departmentSingular}` }}</small></button>
									<div class="eduedge-hierarchy-actions"><EdgeStatusBadge :label="department.is_group ? 'Group' : 'Leaf'" status="department" tone="neutral" /><button type="button" class="edge-button" @click="newProgrammeForDepartment(department)">Add {{ programmeSingular }}</button><button type="button" class="edge-button" @click="openDepartment(department.name)">Full form</button></div>
								</div>
								<EdgeEmptyState v-if="!department.programmes.length" :title="`No ${programmePlural.toLowerCase()}`" :description="`Add a ${programmeSingular} beneath this ${departmentSingular}.`" />
								<div v-else class="eduedge-hierarchy-programmes">
									<div v-for="programme in department.programmes" :key="programme.name" class="eduedge-hierarchy-programme">
										<div class="eduedge-hierarchy-heading"><button type="button" class="eduedge-hierarchy-name" @click="editProgramme(programme)"><strong>{{ programme.program_name || programme.name }}</strong><small>{{ programme.program_abbreviation || programme.name }} · {{ programme.course_count }} course row(s)</small></button><div class="eduedge-hierarchy-actions"><EdgeStatusBadge :label="`${programme.active_offering_count} active offering(s)`" status="offering" :tone="programme.active_offering_count ? 'success' : 'neutral'" /><button type="button" class="edge-button" @click="createStudentGroup(programme)">Add {{ studentGroupSingular }}</button><button type="button" class="edge-button" @click="openProgramme(programme.name)">Full form</button></div></div>
										<div v-if="programme.student_groups.length" class="eduedge-hierarchy-groups">
											<button v-for="group in programme.student_groups" :key="group.name" type="button" class="eduedge-hierarchy-group" @click="openStudentGroup(group.name)"><span><strong>{{ group.student_group_name || group.name }}</strong><small>{{ branchName(group.eduedge_school_branch) }} · {{ group.academic_year }}{{ group.academic_term ? ` · ${group.academic_term}` : "" }}</small></span><EdgeStatusBadge :label="`${group.student_count} student(s)`" status="students" tone="neutral" /></button>
										</div>
										<p v-else class="text-muted">No {{ studentGroupPlural.toLowerCase() }} configured for this {{ programmeSingular.toLowerCase() }}.</p>
									</div>
								</div>
							</article>
						</div>
					</section>

					<section class="eduedge-foundation-list">
						<div class="eduedge-card-heading"><div><p class="edge-eyebrow">Institution calendar</p><h2>{{ academicYearPlural }} and {{ academicTermPlural }}</h2></div><button v-if="permissions.can_create_calendar" type="button" class="edge-button edge-button--primary" @click="createCalendar">New calendar</button></div>
						<EdgeEmptyState v-if="!data.calendars.length" title="No Institution calendar" :description="`Create an Institution calendar that links a native ${academicYearSingular} to its native ${academicTermPlural}.`" />
						<div v-else class="eduedge-calendar-list">
							<article v-for="calendar in data.calendars" :key="calendar.name" class="eduedge-calendar-row">
								<div><strong>{{ calendar.academic_year }}</strong><small>{{ formatDate(calendar.start_date) }} – {{ formatDate(calendar.end_date) }} · {{ calendar.period_count }} {{ academicTermPlural.toLowerCase() }}</small></div>
								<div class="eduedge-hierarchy-actions"><EdgeStatusBadge v-if="calendar.is_current" label="Current" status="current" tone="success" /><EdgeStatusBadge v-else-if="calendar.contains_today" label="Covers today" status="today" tone="success" /><EdgeStatusBadge v-if="calendar.has_calendar_gap_today" label="Current date gap" status="gap" tone="warning" /><button type="button" class="edge-button" @click="editCalendar(calendar)">Edit</button><button type="button" class="edge-button" @click="openCalendar(calendar.name)">Full form</button></div>
								<div v-if="calendar.periods.length" class="eduedge-calendar-periods"><span v-for="period in calendar.periods" :key="period.name"><strong>{{ period.academic_term }}</strong><small>{{ formatDate(period.start_date) }} – {{ formatDate(period.end_date) }}</small></span></div>
							</article>
						</div>
					</section>

					<p v-if="saveError" class="eduedge-foundation-error">{{ saveError }}</p>
				</template>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const emptyDepartment = () => ({ name: "", department_name: "", parent_department: "", is_group: true });
const emptyProgramme = () => ({ name: "", program_name: "", program_abbreviation: "", department: "", course_count: 0, active_offering_count: 0 });
const emptyData = () => ({ active_context: {}, selected_institution: "", terms: {}, institutions: [], departments: [], programmes: [], branches: [], student_groups: [], calendars: [], hierarchy: [], readiness: { ready: false, issues: [], department_count: 0, programme_count: 0, student_group_count: 0, calendar_count: 0 }, permissions: {} });

export default {
	name: "EduEdgeAcademicFoundation",
	data() { return { menuItems: EDUEDGE_MENU_ITEMS, loading: true, error: "", saving: "", saveError: "", selectedInstitution: "", departmentDraft: emptyDepartment(), programmeDraft: emptyProgramme(), data: emptyData() }; },
	computed: {
		activeContext() { return this.data.active_context || {}; },
		permissions() { return this.data.permissions || {}; },
		departmentSingular() { return this.term("department", false, "Department / School Section"); },
		departmentPlural() { return this.term("department", true, "Departments / School Sections"); },
		programmeSingular() { return this.term("programme", false, "Programme / Class"); },
		programmePlural() { return this.term("programme", true, "Programmes / Classes"); },
		studentGroupSingular() { return this.term("student_group", false, "Student Group / Class Arm / Level"); },
		studentGroupPlural() { return this.term("student_group", true, "Student Groups / Class Arms / Levels"); },
		academicYearSingular() { return this.term("academic_year", false, "Academic Session"); },
		academicYearPlural() { return this.term("academic_year", true, "Academic Sessions"); },
		academicTermSingular() { return this.term("academic_term", false, "Term / Semester"); },
		academicTermPlural() { return this.term("academic_term", true, "Terms / Semesters"); },
		selectedInstitutionLabel() { return this.data.institutions.find((row) => row.name === this.selectedInstitution)?.institution_name || this.selectedInstitution; },
		flatDepartments() {
			const result = [];
			const visit = (rows, depth = 0) => { for (const row of rows || []) { result.push({ ...row, depth }); visit(row.children, depth + 1); } };
			visit(this.data.hierarchy || []);
			return result;
		},
		parentDepartmentOptions() { return this.flatDepartments.filter((row) => row.name !== this.departmentDraft.name && row.is_group); },
		canSaveDepartment() { const allowed = this.departmentDraft.name ? this.permissions.can_write_department : this.permissions.can_create_department; return Boolean(allowed && this.selectedInstitution && this.departmentDraft.department_name); },
		canSaveProgramme() { const allowed = this.programmeDraft.name ? this.permissions.can_write_programme : this.permissions.can_create_programme; return Boolean(allowed && this.selectedInstitution && this.programmeDraft.program_name && this.programmeDraft.department); },
	},
	mounted() { this.load(); },
	methods: {
		openRoute: openEduEdgeRoute,
		term(key, plural = false, fallback = "") { const row = this.data.terms?.[key] || this.activeContext.terms?.[key] || {}; return row[plural ? "plural" : "singular"] || fallback; },
		async load() {
			this.loading = true; this.error = "";
			try { const response = await frappe.call("eduedge.api.academic_foundation.get_academic_foundation", { institution: this.selectedInstitution || undefined }); this.data = response.message || emptyData(); this.selectedInstitution = this.data.selected_institution || this.selectedInstitution; this.syncDraftValidity(); }
			catch (error) { this.error = error?.message || "Academic Foundation could not be loaded."; }
			finally { this.loading = false; }
		},
		async institutionChanged() { this.newDepartment(); this.newProgramme(); await this.load(); },
		syncDraftValidity() { if (this.departmentDraft.name && !this.data.departments.some((row) => row.name === this.departmentDraft.name)) this.newDepartment(); if (this.programmeDraft.name && !this.data.programmes.some((row) => row.name === this.programmeDraft.name)) this.newProgramme(); },
		indentedDepartmentName(row) { const depth = this.flatDepartments.find((item) => item.name === row.name)?.depth || 0; return `${"— ".repeat(depth)}${row.department_name || row.name}`; },
		branchName(name) { return this.data.branches.find((row) => row.name === name)?.branch_name || name || "No Branch"; },
		formatDate(value) { return value ? frappe.datetime.str_to_user(value) : "Not set"; },
		newDepartment() { this.departmentDraft = emptyDepartment(); this.saveError = ""; },
		editDepartment(row) { this.departmentDraft = { ...emptyDepartment(), ...row, is_group: Boolean(row.is_group) }; this.saveError = ""; },
		newProgramme() { this.programmeDraft = emptyProgramme(); this.saveError = ""; },
		newProgrammeForDepartment(department) { this.programmeDraft = { ...emptyProgramme(), department: department.name }; this.saveError = ""; },
		editProgramme(row) { this.programmeDraft = { ...emptyProgramme(), ...row }; this.saveError = ""; },
		async saveDepartment() {
			if (!this.canSaveDepartment) return; this.saving = "department"; this.saveError = "";
			try { await frappe.call("eduedge.api.academic_foundation_safe.save_department", { institution: this.selectedInstitution, department: this.departmentDraft.name || undefined, department_name: this.departmentDraft.department_name, parent_department: this.departmentDraft.parent_department || undefined, is_group: this.departmentDraft.is_group ? 1 : 0 }); frappe.show_alert({ message: __(`${this.departmentSingular} saved`), indicator: "green" }); this.newDepartment(); await this.load(); }
			catch (error) { this.saveError = error?.message || `${this.departmentSingular} could not be saved.`; }
			finally { this.saving = ""; }
		},
		async saveProgramme() {
			if (!this.canSaveProgramme) return; this.saving = "programme"; this.saveError = "";
			try { await frappe.call("eduedge.api.programmes.save_programme", { institution: this.selectedInstitution, programme: this.programmeDraft.name || undefined, program_name: this.programmeDraft.program_name, program_abbreviation: this.programmeDraft.program_abbreviation || undefined, department: this.programmeDraft.department }); frappe.show_alert({ message: __(`${this.programmeSingular} saved`), indicator: "green" }); this.newProgramme(); await this.load(); }
			catch (error) { this.saveError = error?.message || `${this.programmeSingular} could not be saved.`; }
			finally { this.saving = ""; }
		},
		createStudentGroup(programme) {
			const calendar = this.data.calendars.find((row) => row.name === this.data.readiness.current_calendar) || this.data.calendars[0] || {};
			const branch = this.data.branches[0] || {};
			frappe.new_doc("Student Group", { program: programme.name, eduedge_school_branch: branch.name || undefined, academic_year: calendar.academic_year || undefined, academic_term: calendar.current_period?.academic_term || undefined, eduedge_institution: this.selectedInstitution });
		},
		createCalendar() { frappe.new_doc("EduEdge Institution Academic Calendar", { institution: this.selectedInstitution }); },
		editCalendar(calendar) { this.openCalendar(calendar.name); },
		openDepartment(name) { frappe.set_route("Form", "Department", name); },
		openProgramme(name) { frappe.set_route("Form", "Program", name); },
		openStudentGroup(name) { frappe.set_route("Form", "Student Group", name); },
		openCalendar(name) { frappe.set_route("Form", "EduEdge Institution Academic Calendar", name); },
		openDepartmentTree() { window.open("/app/department/view/tree", "_blank", "noopener,noreferrer"); },
		openProgrammeList() { window.open("/app/program", "_blank", "noopener,noreferrer"); },
		openCalendarList() { window.open("/app/eduedge-institution-academic-calendar", "_blank", "noopener,noreferrer"); },
	},
};
</script>

<style scoped>
.eduedge-foundation-context-grid,.eduedge-foundation-editor-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1rem; width:100%; }
.eduedge-foundation-context-grid label,.eduedge-foundation-card label { display:grid; gap:.35rem; font-weight:600; }
.eduedge-context-summary { display:grid; gap:.2rem; padding:.7rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.eduedge-context-summary span,.eduedge-context-summary small { color:var(--text-muted); }
.eduedge-foundation-readiness,.eduedge-foundation-card,.eduedge-foundation-list { display:grid; gap:1rem; margin-top:1rem; padding:1rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.eduedge-card-heading,.eduedge-hierarchy-heading,.eduedge-hierarchy-actions,.eduedge-calendar-row { display:flex; align-items:center; justify-content:space-between; gap:.75rem; }
.eduedge-card-heading h2 { margin:0; }
.eduedge-issue-list,.eduedge-hierarchy-list,.eduedge-hierarchy-programmes,.eduedge-hierarchy-groups,.eduedge-calendar-list { display:grid; gap:.65rem; }
.eduedge-issue-row { display:flex; align-items:flex-start; gap:.65rem; padding:.65rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.eduedge-ready-copy { margin:0; }
.eduedge-check { display:flex!important; align-items:center; grid-template-columns:auto 1fr; }
.eduedge-hierarchy-department { display:grid; gap:.75rem; margin-left:calc(var(--hierarchy-depth) * 1.25rem); padding:.85rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.eduedge-hierarchy-programme { display:grid; gap:.65rem; padding:.75rem; border-left:3px solid var(--border-color); background:var(--card-bg); }
.eduedge-hierarchy-name { display:grid; gap:.15rem; padding:0; border:0; background:transparent; text-align:left; }
.eduedge-hierarchy-name small,.eduedge-calendar-row small,.eduedge-calendar-periods small { color:var(--text-muted); }
.eduedge-hierarchy-actions { justify-content:flex-end; flex-wrap:wrap; }
.eduedge-hierarchy-group { display:flex; justify-content:space-between; gap:.75rem; padding:.65rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); text-align:left; }
.eduedge-hierarchy-group span { display:grid; gap:.15rem; }
.eduedge-calendar-row { align-items:flex-start; flex-wrap:wrap; padding:.8rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.eduedge-calendar-row>div:first-child { display:grid; gap:.2rem; }
.eduedge-calendar-periods { display:grid; grid-template-columns:repeat(auto-fit,minmax(11rem,1fr)); gap:.5rem; width:100%; }
.eduedge-calendar-periods span { display:grid; gap:.15rem; padding:.55rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--card-bg); }
.eduedge-foundation-error { color:var(--red-600,#b42318); }
@media (max-width:850px) { .eduedge-foundation-context-grid,.eduedge-foundation-editor-grid { grid-template-columns:1fr; } }
@media (max-width:650px) { .eduedge-card-heading,.eduedge-hierarchy-heading,.eduedge-calendar-row,.eduedge-hierarchy-group { align-items:stretch; flex-direction:column; } .eduedge-hierarchy-actions { justify-content:flex-start; } .eduedge-hierarchy-department { margin-left:0; } }
</style>
