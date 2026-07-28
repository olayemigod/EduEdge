<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="context.tenant_name || ''"
		:branch-name="activeBranchName"
		:user-name="context.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-academic-operations"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Academic Operations"
					:title="`${term('student_group', true, 'Classes')}, ${term('class_session', true, 'Schedules')} and attendance`"
					:subtitle="`Run daily academic activity for ${activeInstitutionName || 'the selected Institution'} and ${activeBranchName || 'Branch / Campus'}.`"
					:action-label="`New ${term('student_group', false, 'Class / Student Group')}`"
					@action="openRoute('/app/student-group/new-student-group')"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading academic operations..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error"
				title="Academic operations could not load"
				:message="error"
				action-label="Try again"
				@retry="loadContext"
			/>
			<template v-else>
				<EdgeFilterBar title="Operational context">
					<div class="eduedge-filter-grid">
						<label>
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="changeBranch">
								<option
									v-for="branch in context.allowed_branches"
									:key="branch.name"
									:value="branch.name"
								>
									{{ branch.branch_name }}
								</option>
							</select>
						</label>
						<label>
							<span>Date</span>
							<input v-model="filters.date" type="date" class="form-control" @change="dateChanged" />
						</label>
						<label>
							<span>{{ term('student_group', false, 'Class / Student Group') }}</span>
							<select v-model="filters.student_group" class="form-control" @change="groupChanged">
								<option value="">All {{ term('student_group', true, 'classes') }}</option>
								<option v-for="group in context.student_groups" :key="group.name" :value="group.name">
									{{ group.student_group_name }} · {{ group.student_count || 0 }} {{ term('student', true, 'students') }}
								</option>
							</select>
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button edge-button--primary" @click="loadContext">Refresh</button>
					</template>
				</EdgeFilterBar>

				<section class="eduedge-context-strip">
					<div>
						<span>Institution</span>
						<strong>{{ activeInstitutionName || "Not configured" }}</strong>
					</div>
					<div>
						<span>{{ term('academic_year', false, 'Academic Year') }}</span>
						<strong>{{ context.filters?.academic_year || "Not resolved" }}</strong>
					</div>
					<div>
						<span>{{ term('academic_term', false, 'Academic Period') }}</span>
						<strong>{{ calendarPeriodLabel }}</strong>
					</div>
					<EdgeStatusBadge
						:label="calendarSourceLabel"
						:status="context.academic_calendar?.source || 'unknown'"
						:tone="context.academic_calendar?.calendar_gap ? 'warning' : 'success'"
					/>
				</section>

				<EdgeActionBar
					v-if="context.academic_calendar?.calendar_gap"
					label="This date is inside the Institution calendar but outside every configured academic period. EduEdge has intentionally left the period blank."
				>
					<template #actions>
						<button type="button" class="edge-button" @click="openRoute('/app/eduedge-academic-foundation')">
							Review Academic Calendar
						</button>
					</template>
				</EdgeActionBar>

				<EdgeDashboardLayout min-column-width="12rem">
					<EdgeStatCard :label="term('student_group', true, 'Classes')" :value="context.counts.student_groups" helper="Active groups in the resolved session" />
					<EdgeStatCard :label="`Assigned ${term('instructor', true, 'Instructors')}`" :value="context.counts.assigned_instructors" helper="Enabled Branch assignments" />
					<EdgeStatCard :label="`Today's ${term('class_session', true, 'Schedules')}`" :value="context.counts.schedules" helper="Filtered by selected date" />
					<EdgeStatCard label="Rooms Used" :value="context.counts.rooms_used" :helper="`${context.counts.unassigned_room_sessions || 0} sessions without rooms`" />
					<EdgeStatCard label="Attendance Complete" :value="context.counts.attendance_complete_groups" tone="success" helper="Scheduled groups with complete registers" />
					<EdgeStatCard label="Missing Registers" :value="context.counts.attendance_missing_groups" :tone="context.counts.attendance_missing_groups ? 'danger' : 'success'" helper="Scheduled groups with no submitted attendance" />
				</EdgeDashboardLayout>

				<section class="eduedge-quick-actions" aria-label="Academic quick actions">
					<button type="button" class="edge-button" @click="openRoute('/app/eduedge-academic-foundation')">Academic Foundation</button>
					<button type="button" class="edge-button" @click="openRoute('/app/eduedge-programs')">{{ term('programme', true, 'Programmes') }}</button>
					<button type="button" class="edge-button" @click="openRoute('/app/eduedge-program-offerings')">{{ term('programme_offering', true, 'Programme Offerings') }}</button>
					<button type="button" class="edge-button" @click="openRoute('/app/course-schedule/new-course-schedule')">Add {{ term('class_session', false, 'Schedule') }}</button>
					<button type="button" class="edge-button" @click="openRoute('/app/room')">Manage Rooms</button>
					<button type="button" class="edge-button" @click="openRoute('/app/eduedge-instructor-branch-assignment')">Instructor Assignments</button>
				</section>

				<section class="eduedge-operations-grid">
					<article class="eduedge-panel">
						<div class="eduedge-panel-header">
							<div>
								<p class="edge-eyebrow">{{ term('class_session', false, 'Schedule') }}</p>
								<h2>{{ term('student_group', true, 'Classes') }} for {{ filters.date }}</h2>
							</div>
							<button type="button" class="edge-button" @click="openRoute('/app/course-schedule/new-course-schedule')">
								Add {{ term('class_session', false, 'schedule') }}
							</button>
						</div>
						<EdgeEmptyState
							v-if="!context.schedules.length"
							:title="`No ${term('student_group', true, 'classes').toLowerCase()} scheduled`"
							description="Create a Course Schedule or choose another date."
						/>
						<div v-else class="eduedge-schedule-list">
							<button
								v-for="schedule in context.schedules"
								:key="schedule.name"
								type="button"
								class="eduedge-schedule-card"
								:class="{ 'is-selected': filters.course_schedule === schedule.name }"
								@click="selectSchedule(schedule)"
							>
								<strong>{{ schedule.course }}</strong>
								<span>{{ schedule.student_group }}</span>
								<span>{{ schedule.instructor_name || schedule.instructor || `No ${term('instructor', false, 'instructor')}` }}</span>
								<span>{{ formatTime(schedule.from_time) }} – {{ formatTime(schedule.to_time) }} · {{ schedule.room || "Room not assigned" }}</span>
							</button>
						</div>
					</article>

					<article class="eduedge-panel">
						<div class="eduedge-panel-header">
							<div>
								<p class="edge-eyebrow">Attendance</p>
								<h2>{{ term('student_group', false, 'Class') }} register</h2>
							</div>
							<button type="button" class="edge-button" :disabled="!filters.student_group || registerLoading" @click="loadRegister">
								Load register
							</button>
						</div>

						<div v-if="selectedSchedule" class="eduedge-selected-schedule">
							<div><span>{{ term('course', false, 'Course') }}</span><strong>{{ selectedSchedule.course }}</strong></div>
							<div><span>{{ term('instructor', false, 'Instructor') }}</span><strong>{{ selectedSchedule.instructor_name || selectedSchedule.instructor || "Not assigned" }}</strong></div>
							<div><span>Time and Room</span><strong>{{ formatTime(selectedSchedule.from_time) }} – {{ formatTime(selectedSchedule.to_time) }} · {{ selectedSchedule.room || "Not assigned" }}</strong></div>
						</div>

						<EdgeLoadingState v-if="registerLoading" message="Loading class register..." />
						<EdgeErrorState
							v-else-if="registerError"
							title="Register could not load"
							:message="registerError"
							action-label="Try again"
							@retry="loadRegister"
						/>
						<EdgeEmptyState
							v-else-if="!register.students.length"
							:title="`Select a ${term('student_group', false, 'class')}`"
							:description="`Choose a ${term('student_group', false, 'Class / Student Group')} or a schedule to mark attendance.`"
						/>
						<template v-else>
							<div class="eduedge-register-summary">
								<EdgeStatusBadge :label="`${register.submitted_count} submitted`" :status="register.submitted_count ? 'submitted' : 'none'" :tone="register.submitted_count ? 'success' : 'neutral'" />
								<EdgeStatusBadge :label="`${register.pending_count} editable`" :status="register.pending_count ? 'pending' : 'complete'" :tone="register.pending_count ? 'warning' : 'success'" />
							</div>
							<div class="eduedge-table-wrap">
								<table class="table table-bordered eduedge-register-table">
									<thead><tr><th>Roll No.</th><th>{{ term('student', false, 'Student') }}</th><th>Status</th><th>Record</th></tr></thead>
									<tbody>
										<tr v-for="student in register.students" :key="student.student">
											<td>{{ student.group_roll_number || "—" }}</td>
											<td><strong>{{ student.student_name }}</strong><div class="text-muted">{{ student.student }}</div></td>
											<td>
												<select v-model="student.status" class="form-control input-sm" :disabled="student.locked || saving">
													<option value="Present">Present</option><option value="Absent">Absent</option><option value="Leave">Leave</option>
												</select>
											</td>
											<td><EdgeStatusBadge :label="student.locked ? 'Submitted' : student.attendance_name ? 'Draft' : 'New'" :status="student.locked ? 'submitted' : 'draft'" :tone="student.locked ? 'success' : 'neutral'" /></td>
										</tr>
									</tbody>
								</table>
							</div>
							<EdgeActionBar label="Submitted attendance is immutable. Cancel or amend the record before changing it.">
								<template #actions>
									<button type="button" class="edge-button" :disabled="saving" @click="saveRegister(false)">Save Draft</button>
									<button type="button" class="edge-button edge-button--primary" :disabled="saving" @click="saveRegister(true)">Submit Attendance</button>
								</template>
							</EdgeActionBar>
						</template>
					</article>
				</section>

				<section class="eduedge-insight-grid">
					<article class="eduedge-panel">
						<div class="eduedge-panel-header"><div><p class="edge-eyebrow">Register readiness</p><h2>Scheduled attendance coverage</h2></div></div>
						<EdgeEmptyState v-if="!context.attendance_coverage.length" title="No scheduled registers" description="Attendance readiness will appear when a class is scheduled for this date." />
						<div v-else class="eduedge-readiness-list">
							<button v-for="row in context.attendance_coverage" :key="row.student_group" type="button" class="eduedge-readiness-row" @click="selectCoverage(row)">
								<span><strong>{{ row.student_group_name }}</strong><small>{{ row.submitted }} of {{ row.expected }} submitted</small></span>
								<EdgeStatusBadge :label="row.complete ? 'Complete' : row.has_attendance ? `${row.missing} missing` : 'Not started'" :status="row.complete ? 'complete' : row.has_attendance ? 'partial' : 'missing'" :tone="row.complete ? 'success' : row.has_attendance ? 'warning' : 'danger'" />
							</button>
						</div>
					</article>
					<article class="eduedge-panel">
						<div class="eduedge-panel-header"><div><p class="edge-eyebrow">Facilities</p><h2>Room usage</h2></div></div>
						<EdgeEmptyState v-if="!context.room_usage.length" title="No room usage" description="Room allocation will appear when schedules exist for this date." />
						<div v-else class="eduedge-readiness-list">
							<div v-for="row in context.room_usage" :key="row.room" class="eduedge-readiness-row is-static">
								<span><strong>{{ row.room }}</strong><small>{{ formatTime(row.first_start) }} – {{ formatTime(row.last_end) }}</small></span>
								<EdgeStatusBadge :label="`${row.sessions} session${row.sessions === 1 ? '' : 's'}`" :status="row.is_unassigned ? 'missing' : 'active'" :tone="row.is_unassigned ? 'warning' : 'neutral'" />
							</div>
						</div>
					</article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const emptyRegister = () => ({ students: [], submitted_count: 0, pending_count: 0 });

export default {
	name: "EduEdgeAcademicOperations",
	data() {
		const today = new Date().toISOString().slice(0, 10);
		return {
			loading: true,
			error: "",
			registerLoading: false,
			registerError: "",
			saving: false,
			menuItems: EDUEDGE_MENU_ITEMS,
			filters: { branch: "", date: today, student_group: "", course_schedule: "" },
			context: {
				user: {}, current_branch: null, selected_branch: {}, allowed_branches: [], academic_calendar: {},
				counts: { student_groups: 0, assigned_instructors: 0, schedules: 0, rooms_used: 0, unassigned_room_sessions: 0, attendance_submitted: 0, present: 0, absent: 0, leave: 0, attendance_complete_groups: 0, attendance_incomplete_groups: 0, attendance_missing_groups: 0 },
				student_groups: [], schedules: [], attendance_coverage: [], room_usage: [],
			},
			register: emptyRegister(),
		};
	},
	computed: {
		activeBranchName() {
			return this.context.selected_branch?.branch_name || this.context.allowed_branches.find((item) => item.name === this.filters.branch)?.branch_name || this.context.current_branch?.branch_name || "";
		},
		activeInstitutionName() { return this.context.selected_branch?.institution_name || ""; },
		calendarPeriodLabel() { return this.context.academic_calendar?.period_label || this.context.filters?.academic_term || "Not resolved"; },
		calendarSourceLabel() {
			if (this.context.academic_calendar?.calendar_gap) return "Calendar period gap";
			return this.context.academic_calendar?.source === "institution_calendar" ? "Institution calendar" : "Education Settings fallback";
		},
		selectedSchedule() { return this.context.schedules.find((row) => row.name === this.filters.course_schedule) || null; },
	},
	mounted() { this.loadContext(); },
	methods: {
		openRoute: openEduEdgeRoute,
		term(key, plural = false, fallback = "") { return frappe.eduedge?.term?.(key, { plural, context: this.context, fallback }) || fallback; },
		formatTime(value) { return String(value || "").slice(0, 5) || "—"; },
		async loadContext() {
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.academic_operations.get_operations_context", { branch: this.filters.branch || undefined, date: this.filters.date, student_group: this.filters.student_group || undefined });
				this.context = response.message || this.context;
				this.filters.branch = this.context.filters?.branch || this.filters.branch;
				this.filters.date = this.context.filters?.date || this.filters.date;
			} catch (error) { this.error = error?.message || "Academic operations context could not be loaded."; }
			finally { this.loading = false; }
		},
		async changeBranch() {
			if (!this.filters.branch) return;
			try {
				await frappe.call("eduedge.api.branch_context.switch_school_branch", { branch: this.filters.branch });
				this.filters.student_group = ""; this.filters.course_schedule = ""; this.register = emptyRegister();
				await this.loadContext();
			} catch (error) { frappe.msgprint({ title: __("Unable to switch branch"), message: error?.message || __("The selected branch could not be activated."), indicator: "red" }); }
		},
		async dateChanged() { this.filters.course_schedule = ""; this.register = emptyRegister(); await this.loadContext(); },
		async groupChanged() { this.filters.course_schedule = ""; this.register = emptyRegister(); await this.loadContext(); },
		selectSchedule(schedule) { this.filters.student_group = schedule.student_group; this.filters.course_schedule = schedule.name; this.loadRegister(); },
		selectCoverage(row) { this.filters.student_group = row.student_group; this.filters.course_schedule = ""; this.loadRegister(); },
		async loadRegister() {
			if (!this.filters.student_group) return;
			this.registerLoading = true; this.registerError = "";
			try {
				const response = await frappe.call("eduedge.api.academic_operations.get_attendance_register", { student_group: this.filters.student_group, date: this.filters.date, course_schedule: this.filters.course_schedule || undefined });
				this.register = response.message || this.register;
			} catch (error) { this.registerError = error?.message || "The attendance register could not be loaded."; }
			finally { this.registerLoading = false; }
		},
		async saveRegister(submit) {
			if (!this.register.students.length) return;
			this.saving = true;
			try {
				const response = await frappe.call("eduedge.api.academic_operations.save_attendance_register", { student_group: this.filters.student_group, date: this.register.date || this.filters.date, course_schedule: this.filters.course_schedule || undefined, entries: this.register.students.map((row) => ({ student: row.student, status: row.status })), submit: submit ? 1 : 0 });
				const result = response.message || {};
				frappe.show_alert({ message: submit ? `${result.submitted || 0} attendance records submitted` : `${(result.created || 0) + (result.updated || 0)} draft records saved`, indicator: "green" });
				await this.loadRegister(); await this.loadContext();
			} catch (error) { frappe.msgprint({ title: __("Attendance could not be saved"), message: error?.message || __("Review the register and try again."), indicator: "red" }); }
			finally { this.saving = false; }
		},
	},
};
</script>

<style scoped>
.eduedge-filter-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(13rem,1fr)); gap:.75rem; width:100%; }
.eduedge-filter-grid label { display:grid; gap:.35rem; font-weight:600; }
.eduedge-context-strip { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)) auto; gap:1rem; align-items:center; padding:1rem; margin:1rem 0; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.eduedge-context-strip > div { display:grid; gap:.2rem; }
.eduedge-context-strip span,.eduedge-selected-schedule span { color:var(--text-muted); font-size:.8rem; }
.eduedge-quick-actions { display:flex; flex-wrap:wrap; gap:.5rem; margin-top:1rem; }
.eduedge-operations-grid,.eduedge-insight-grid { display:grid; grid-template-columns:minmax(18rem,.8fr) minmax(28rem,1.5fr); gap:var(--edge-space-4,1rem); margin-top:var(--edge-space-5,1.25rem); }
.eduedge-insight-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
.eduedge-panel { padding:var(--edge-space-5,1.25rem); border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.eduedge-panel-header { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:1rem; }
.eduedge-panel-header h2 { margin:.25rem 0 0; }
.eduedge-schedule-list,.eduedge-readiness-list { display:grid; gap:.75rem; }
.eduedge-schedule-card,.eduedge-readiness-row { display:flex; justify-content:space-between; align-items:center; gap:1rem; width:100%; padding:.9rem; text-align:left; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.eduedge-schedule-card { display:grid; gap:.25rem; }
.eduedge-schedule-card:hover,.eduedge-schedule-card.is-selected,.eduedge-readiness-row:not(.is-static):hover { border-color:var(--primary); }
.eduedge-schedule-card span,.eduedge-readiness-row small { color:var(--text-muted); }
.eduedge-readiness-row span { display:grid; gap:.15rem; }
.eduedge-selected-schedule { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.75rem; padding:.75rem; margin-bottom:1rem; border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.eduedge-selected-schedule > div { display:grid; gap:.2rem; }
.eduedge-register-summary { display:flex; flex-wrap:wrap; gap:.5rem; margin-bottom:1rem; }
.eduedge-table-wrap { overflow-x:auto; }
.eduedge-register-table { min-width:42rem; }
@media (max-width:960px) { .eduedge-context-strip,.eduedge-operations-grid,.eduedge-insight-grid,.eduedge-selected-schedule { grid-template-columns:1fr; } }
</style>
