<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="context.tenant_name || ''"
		:branch-name="activeBranchName"
		:user-name="context.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-attendance"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Academic Operations"
					title="Attendance"
					subtitle="Take attendance, review registers and resolve missing registers without mixing timetable setup into the workflow."
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading attendance..." :skeleton="true" />
			<EdgeErrorState v-else-if="error" title="Attendance could not load" :message="error" action-label="Try again" @retry="loadContext" />
			<template v-else>
				<EdgeFilterBar title="Attendance context">
					<div class="attendance-filter-grid">
						<label>
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="changeBranch">
								<option v-for="branch in context.allowed_branches" :key="branch.name" :value="branch.name">{{ branch.branch_name }}</option>
							</select>
						</label>
						<label>
							<span>Date</span>
							<input v-model="filters.date" type="date" class="form-control" @change="dateChanged" />
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" @click="openRoute('/app/eduedge-teaching-schedule')">Teaching Schedule</button>
						<button type="button" class="edge-button edge-button--primary" @click="loadContext">Refresh</button>
					</template>
				</EdgeFilterBar>

				<div class="attendance-tabs" role="tablist" aria-label="Attendance views">
					<button v-for="tab in tabs" :key="tab.key" type="button" class="edge-button" :class="{ 'edge-button--primary': activeTab === tab.key }" @click="activeTab = tab.key">{{ tab.label }}</button>
				</div>

				<EdgeDashboardLayout min-column-width="11rem">
					<EdgeStatCard label="Scheduled Registers" :value="context.attendance_coverage.length || 0" helper="Sessions expected on selected date" />
					<EdgeStatCard label="Complete" :value="context.counts.attendance_complete_registers || 0" tone="success" helper="Registers with all expected attendance submitted" />
					<EdgeStatCard label="Incomplete" :value="context.counts.attendance_incomplete_registers || 0" :tone="context.counts.attendance_incomplete_registers ? 'warning' : 'success'" helper="Registers started but not complete" />
					<EdgeStatCard label="Missing" :value="context.counts.attendance_missing_registers || 0" :tone="context.counts.attendance_missing_registers ? 'danger' : 'success'" helper="Scheduled sessions with no submitted attendance" />
				</EdgeDashboardLayout>

				<section v-if="activeTab === 'take'" class="attendance-panel">
					<div class="attendance-panel-header"><div><p class="edge-eyebrow">Take Attendance</p><h2>Select a scheduled class session</h2></div></div>
					<div class="attendance-select-grid">
						<label>
							<span>Scheduled Session</span>
							<select v-model="filters.course_schedule" class="form-control" @change="scheduleChanged">
								<option value="">Select a schedule</option>
								<option v-for="row in context.schedules" :key="row.name" :value="row.name">{{ scheduleLabel(row) }}</option>
							</select>
						</label>
					</div>
					<EdgeLoadingState v-if="registerLoading" message="Loading register..." />
					<EdgeErrorState v-else-if="registerError" title="Register could not load" :message="registerError" action-label="Try again" @retry="loadRegister" />
					<EdgeEmptyState v-else-if="!register.students.length" title="Choose a scheduled session" description="Attendance is anchored to an exact Course Schedule so EduEdge does not guess between multiple sessions on the same day." />
					<template v-else>
						<div v-if="register.course_schedule" class="selected-session">
							<div><span>Class</span><strong>{{ register.student_group_name || register.student_group }}</strong></div>
							<div><span>Subject</span><strong>{{ register.course_schedule.course || 'Not set' }}</strong></div>
							<div><span>Instructor</span><strong>{{ register.course_schedule.instructor_name || register.course_schedule.instructor || 'Not assigned' }}</strong></div>
						</div>
						<div class="attendance-register-summary">
							<EdgeStatusBadge :label="`${register.submitted_count} submitted`" :status="register.submitted_count ? 'submitted' : 'none'" :tone="register.submitted_count ? 'success' : 'neutral'" />
							<EdgeStatusBadge :label="`${register.pending_count} editable`" :status="register.pending_count ? 'pending' : 'complete'" :tone="register.pending_count ? 'warning' : 'success'" />
						</div>
						<div class="attendance-table-wrap">
							<table class="table table-bordered attendance-table">
								<thead><tr><th>Roll No.</th><th>Student</th><th>Status</th><th>Record</th></tr></thead>
								<tbody>
									<tr v-for="student in register.students" :key="student.student">
										<td>{{ student.group_roll_number || '—' }}</td>
										<td><strong>{{ student.student_name }}</strong><div class="text-muted">{{ student.student }}</div></td>
										<td><select v-model="student.status" class="form-control input-sm" :disabled="student.locked || saving || !canManageAttendance"><option value="Present">Present</option><option value="Absent">Absent</option><option value="Leave">Leave</option></select></td>
										<td><EdgeStatusBadge :label="student.locked ? 'Submitted' : student.attendance_name ? 'Draft' : 'New'" :status="student.locked ? 'submitted' : 'draft'" :tone="student.locked ? 'success' : 'neutral'" /></td>
									</tr>
								</tbody>
							</table>
						</div>
						<EdgeActionBar :label="canManageAttendance ? 'Submitted attendance remains immutable. Existing submitted records are never edited in place.' : 'This register is read-only for your current role.'">
							<template v-if="canManageAttendance" #actions>
								<button type="button" class="edge-button" :disabled="saving" @click="saveRegister(false)">Save Draft</button>
								<button v-if="canSubmitAttendance" type="button" class="edge-button edge-button--primary" :disabled="saving" @click="saveRegister(true)">Submit Attendance</button>
							</template>
						</EdgeActionBar>
					</template>
				</section>

				<section v-else class="attendance-panel">
					<div class="attendance-panel-header"><div><p class="edge-eyebrow">{{ activeTab === 'missing' ? 'Exceptions' : 'Registers' }}</p><h2>{{ activeTab === 'missing' ? 'Missing attendance registers' : 'Scheduled attendance coverage' }}</h2></div></div>
					<EdgeEmptyState v-if="!visibleCoverage.length" :title="activeTab === 'missing' ? 'No missing registers' : 'No scheduled registers'" :description="activeTab === 'missing' ? 'Every scheduled session has attendance activity for this date.' : 'Create a Teaching Schedule or choose another date.'" />
					<div v-else class="coverage-list">
						<button v-for="row in visibleCoverage" :key="row.course_schedule" type="button" class="coverage-row" @click="openCoverage(row)">
							<span><strong>{{ row.student_group_name }}</strong><small>{{ row.course || 'Course not set' }} · {{ formatTime(row.from_time) }} – {{ formatTime(row.to_time) }} · {{ row.submitted }} of {{ row.expected }} submitted</small></span>
							<EdgeStatusBadge :label="row.complete ? 'Complete' : row.has_attendance ? `${row.missing} missing` : 'Not started'" :status="row.complete ? 'complete' : row.has_attendance ? 'partial' : 'missing'" :tone="row.complete ? 'success' : row.has_attendance ? 'warning' : 'danger'" />
						</button>
					</div>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const emptyPermissions = () => ({ can_read_attendance: false, can_create_attendance: false, can_write_attendance: false, can_submit_attendance: false });
const emptyRegister = () => ({ students: [], submitted_count: 0, pending_count: 0, permissions: emptyPermissions(), course_schedule: null });
const emptyContext = () => ({ user: {}, current_branch: {}, selected_branch: {}, allowed_branches: [], permissions: emptyPermissions(), counts: {}, schedules: [], attendance_coverage: [] });

export default {
	name: "EduEdgeAttendance",
	data() {
		const today = frappe.datetime?.get_today?.() || new Date().toISOString().slice(0, 10);
		return {
			loading: true, error: "", registerLoading: false, registerError: "", saving: false,
			menuItems: EDUEDGE_MENU_ITEMS,
			activeTab: "take",
			tabs: [{ key: "take", label: "Take Attendance" }, { key: "registers", label: "Registers" }, { key: "missing", label: "Missing Registers" }],
			filters: { branch: "", date: today, course_schedule: "", student_group: "" },
			pendingCourseSchedule: "",
			context: emptyContext(), register: emptyRegister(),
		};
	},
	computed: {
		activeBranchName() { return this.context.selected_branch?.branch_name || this.context.current_branch?.branch_name || ""; },
		registerPermissions() { return this.register.permissions || this.context.permissions || emptyPermissions(); },
		canManageAttendance() { return Boolean(this.registerPermissions.can_create_attendance || this.registerPermissions.can_write_attendance); },
		canSubmitAttendance() { return Boolean(this.registerPermissions.can_submit_attendance); },
		visibleCoverage() { return this.activeTab === "missing" ? (this.context.attendance_coverage || []).filter((row) => !row.has_attendance) : (this.context.attendance_coverage || []); },
	},
	mounted() {
		const params = new URLSearchParams(window.location.search || "");
		if (params.get("date")) this.filters.date = params.get("date");
		if (["take", "registers", "missing"].includes(params.get("tab"))) this.activeTab = params.get("tab");
		this.pendingCourseSchedule = params.get("course_schedule") || "";
		this.loadContext();
	},
	methods: {
		openRoute: openEduEdgeRoute,
		formatTime(value) { return String(value || "").slice(0, 5) || "—"; },
		scheduleLabel(row) { return `${this.formatTime(row.from_time)} · ${row.course || 'Subject'} · ${row.student_group || 'Class'} · ${row.instructor_name || row.instructor || 'No Instructor'}`; },
		async loadContext() {
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.academic_operations.get_operations_context", { branch: this.filters.branch || undefined, date: this.filters.date });
				this.context = response.message || emptyContext();
				this.filters.branch = this.context.filters?.branch || this.filters.branch;
				this.filters.date = this.context.filters?.date || this.filters.date;
				if (this.pendingCourseSchedule) {
					this.filters.course_schedule = this.pendingCourseSchedule;
					this.pendingCourseSchedule = "";
					const schedule = this.context.schedules.find((row) => row.name === this.filters.course_schedule);
					if (schedule) {
						this.filters.student_group = schedule.student_group || "";
						if (this.activeTab === "take") await this.loadRegister();
					} else {
						this.filters.course_schedule = ""; this.filters.student_group = ""; this.register = emptyRegister();
					}
				} else if (!this.context.schedules.some((row) => row.name === this.filters.course_schedule)) {
					this.filters.course_schedule = ""; this.filters.student_group = ""; this.register = emptyRegister();
				}
			} catch (error) { this.error = error?.message || "Attendance context could not be loaded."; }
			finally { this.loading = false; }
		},
		async changeBranch() {
			if (!this.filters.branch) return;
			try {
				await frappe.call("eduedge.api.branch_context.switch_school_branch", { branch: this.filters.branch });
				this.filters.course_schedule = ""; this.filters.student_group = ""; this.register = emptyRegister();
				await this.loadContext();
			} catch (error) { frappe.msgprint({ title: __("Unable to switch Branch"), message: error?.message || __("The selected Branch could not be activated."), indicator: "red" }); }
		},
		async dateChanged() { this.filters.course_schedule = ""; this.filters.student_group = ""; this.register = emptyRegister(); await this.loadContext(); },
		async scheduleChanged() {
			const schedule = this.context.schedules.find((row) => row.name === this.filters.course_schedule);
			this.filters.student_group = schedule?.student_group || "";
			if (schedule) await this.loadRegister(); else this.register = emptyRegister();
		},
		async loadRegister() {
			if (!this.filters.student_group || !this.filters.course_schedule) return;
			this.registerLoading = true; this.registerError = "";
			try {
				const response = await frappe.call("eduedge.api.academic_operations.get_attendance_register", { student_group: this.filters.student_group, date: this.filters.date, course_schedule: this.filters.course_schedule });
				this.register = response.message || emptyRegister();
			} catch (error) { this.register = emptyRegister(); this.registerError = error?.message || "The attendance register could not be loaded."; }
			finally { this.registerLoading = false; }
		},
		async saveRegister(submit) {
			if (!this.canManageAttendance || !this.register.students.length || !this.filters.course_schedule) return;
			this.saving = true;
			try {
				const response = await frappe.call("eduedge.api.academic_operations.save_attendance_register", {
					student_group: this.filters.student_group,
					date: this.register.date || this.filters.date,
					course_schedule: this.filters.course_schedule,
					entries: this.register.students.map((row) => ({ student: row.student, status: row.status })),
					submit: submit ? 1 : 0,
				});
				const result = response.message || {};
				frappe.show_alert({ message: submit ? `${result.submitted || 0} attendance records submitted` : `${(result.created || 0) + (result.updated || 0)} draft records saved`, indicator: "green" });
				await this.loadRegister(); await this.loadContext();
			} catch (error) { frappe.msgprint({ title: __("Attendance could not be saved"), message: error?.message || __("Review the register and try again."), indicator: "red" }); }
			finally { this.saving = false; }
		},
		async openCoverage(row) {
			this.activeTab = "take";
			this.filters.course_schedule = row.course_schedule;
			this.filters.student_group = row.student_group;
			await this.loadRegister();
		},
	},
};
</script>

<style scoped>
.attendance-filter-grid,.attendance-select-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(14rem,1fr)); gap:.75rem; width:100%; }
.attendance-filter-grid label,.attendance-select-grid label { display:grid; gap:.35rem; font-weight:600; }
.attendance-tabs { display:flex; flex-wrap:wrap; gap:.5rem; margin:1rem 0; }
.attendance-panel { margin-top:1rem; padding:1rem; border:1px solid var(--edge-color-border,var(--border-color)); border-radius:var(--edge-radius-lg,12px); background:var(--edge-color-surface,var(--card-bg)); }
.attendance-panel-header { display:flex; justify-content:space-between; align-items:center; gap:1rem; margin-bottom:1rem; }
.attendance-panel-header h2 { margin:.2rem 0 0; }
.selected-session { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.75rem; margin:1rem 0; padding:.8rem; border-radius:var(--edge-radius-md,8px); background:var(--edge-color-surface-muted,var(--control-bg)); }
.selected-session > div { display:grid; gap:.2rem; }
.selected-session span { color:var(--edge-color-ink-500,var(--text-muted)); font-size:.8rem; }
.attendance-register-summary { display:flex; flex-wrap:wrap; gap:.5rem; margin:.75rem 0; }
.attendance-table-wrap { overflow-x:auto; }
.attendance-table { min-width:42rem; }
.coverage-list { display:grid; gap:.65rem; }
.coverage-row { display:flex; justify-content:space-between; align-items:center; gap:1rem; width:100%; padding:.85rem; text-align:left; border:1px solid var(--edge-color-border,var(--border-color)); border-radius:var(--edge-radius-md,8px); background:var(--edge-color-surface-muted,var(--control-bg)); color:var(--edge-color-ink-800,var(--text-color)); }
.coverage-row span { display:grid; gap:.2rem; }
.coverage-row small { color:var(--edge-color-ink-500,var(--text-muted)); }
.coverage-row:hover { border-color:var(--primary); }
@media (max-width:780px) { .selected-session { grid-template-columns:1fr; } .coverage-row { align-items:flex-start; flex-direction:column; } }
</style>
