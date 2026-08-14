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
					eyebrow="Academics"
					title="Academic Operations"
					subtitle="Daily academic command centre for teaching activity, attendance readiness and issues that need attention."
					:action-label="canCreateStudentGroup ? `New ${term('student_group', false, 'Class Arm')}` : ''"
					@action="openClassArms(true)"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading academic operations..." :skeleton="true" />
			<EdgeErrorState v-else-if="error" title="Academic operations could not load" :message="error" action-label="Try again" @retry="loadContext" />
			<template v-else>
				<EdgeFilterBar title="Daily context">
					<div class="operations-filter-grid">
						<label>
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="changeBranch">
								<option v-for="branch in context.allowed_branches" :key="branch.name" :value="branch.name">{{ branch.branch_name }}</option>
							</select>
						</label>
						<label>
							<span>Date</span>
							<input v-model="filters.date" type="date" class="form-control" @change="loadContext" />
						</label>
					</div>
					<template #actions><button type="button" class="edge-button edge-button--primary" @click="loadContext">Refresh</button></template>
				</EdgeFilterBar>

				<section class="operations-context-strip">
					<div><span>Institution</span><strong>{{ activeInstitutionName || 'Not configured' }}</strong></div>
					<div><span>Academic Session</span><strong>{{ context.filters?.academic_year || 'Not resolved' }}</strong></div>
					<div><span>Term / Semester</span><strong>{{ context.academic_calendar?.period_label || context.filters?.academic_term || 'Not resolved' }}</strong></div>
					<EdgeStatusBadge :label="calendarReady ? 'Institution calendar' : 'Calendar attention'" :status="calendarReady ? 'ready' : 'warning'" :tone="calendarReady ? 'success' : 'warning'" />
				</section>

				<EdgeActionBar v-if="context.academic_calendar?.blocking_issue" :label="context.academic_calendar.blocking_issue">
					<template #actions><button type="button" class="edge-button" @click="openRoute('/app/eduedge-academic-foundation')">Review Academic Calendar</button></template>
				</EdgeActionBar>
				<EdgeActionBar v-else-if="context.academic_calendar?.calendar_gap" label="The selected date is inside the Institution Academic Session but outside every configured Term / Semester.">
					<template #actions><button type="button" class="edge-button" @click="openRoute('/app/eduedge-academic-foundation')">Review Academic Calendar</button></template>
				</EdgeActionBar>

				<EdgeDashboardLayout min-column-width="11rem">
					<EdgeStatCard :label="term('student_group', true, 'Classes')" :value="context.counts.student_groups || 0" helper="Active groups in the resolved academic period" />
					<EdgeStatCard :label="term('class_session', true, 'Scheduled Sessions')" :value="context.counts.schedules || 0" helper="Teaching sessions for selected date" />
					<EdgeStatCard :label="`Assigned ${term('instructor', true, 'Instructors')}`" :value="context.counts.assigned_instructors || 0" helper="Current Branch assignment coverage" />
					<EdgeStatCard label="Attendance Complete" :value="context.counts.attendance_complete_registers || 0" tone="success" helper="Scheduled registers completed" />
					<EdgeStatCard label="Missing Registers" :value="context.counts.attendance_missing_registers || context.counts.attendance_missing_groups || 0" :tone="(context.counts.attendance_missing_registers || context.counts.attendance_missing_groups) ? 'danger' : 'success'" helper="Sessions with no submitted attendance" />
					<EdgeStatCard label="Room Gaps" :value="context.counts.unassigned_room_sessions || 0" :tone="context.counts.unassigned_room_sessions ? 'warning' : 'success'" helper="Scheduled sessions without rooms" />
				</EdgeDashboardLayout>

				<section class="operations-actions" aria-label="Academic operation areas">
					<button v-if="canCreateCourseSchedule || permissions.can_read_course_schedule !== false" type="button" class="operation-action" @click="openFocused('/app/eduedge-teaching-schedule')"><strong>Teaching Schedule</strong><span>Day, week, upcoming {{ term('class_session', true, 'sessions').toLowerCase() }} and rooms</span></button>
					<button v-if="canReadAttendance" type="button" class="operation-action" @click="openFocused('/app/eduedge-attendance')"><strong>Attendance</strong><span>Take attendance and resolve missing registers. Submitted attendance is immutable.</span></button>
					<button v-if="canReadInstructorAssignments" type="button" class="operation-action" @click="openRoute('/app/eduedge-instructor-assignments')"><strong>{{ term('instructor', false, 'Instructor') }} Assignments</strong><span>Teaching responsibility and Branch eligibility</span></button>
					<button type="button" class="operation-action" @click="openRoute('/app/eduedge-schemes-of-work')"><strong>Scheme of Work</strong><span>{{ term('course', true, 'Subjects') }} and approved curriculum delivery plan</span></button>
					<button type="button" class="operation-action" @click="openRoute('/app/eduedge-lesson-plans')"><strong>Lesson Plans</strong><span>Teaching preparation and evidence</span></button>
					<button type="button" class="operation-action" @click="openRoute('/app/eduedge-program-offerings')"><strong>{{ term('programme_offering', true, 'Programme Offerings') }}</strong><span>{{ term('programme', true, 'Programmes') }} by Branch and academic period</span></button>
					<button v-if="canCreateStudentGroup" type="button" class="operation-action" @click="openClassArms(false)"><strong>Manage {{ term('student_group', true, 'Class Arms') }}</strong><span>Create and maintain class-group structure</span></button>
					<button type="button" class="operation-action" @click="openRoute('/app/eduedge-academic-readiness')"><strong>Academic Readiness</strong><span>Coverage, gaps and management attention</span></button>
				</section>

				<section class="operations-grid">
					<article class="operations-panel">
						<div class="operations-panel-header">
							<div><p class="edge-eyebrow">Today’s teaching</p><h2>{{ filters.date }}</h2></div>
							<button type="button" class="edge-button" @click="openFocused('/app/eduedge-teaching-schedule')">Open Schedule</button>
						</div>
						<EdgeEmptyState v-if="!context.schedules.length" title="No scheduled sessions" description="Open Teaching Schedule to review another date or create a session." />
						<div v-else class="operations-list">
							<button v-for="schedule in context.schedules" :key="schedule.name" type="button" class="operations-row" @click="openSchedule(schedule.name)">
								<span><strong>{{ schedule.course || term('course', false, 'Subject') }}</strong><small>{{ schedule.student_group }} · {{ schedule.instructor_name || schedule.instructor || `No ${term('instructor', false, 'Instructor')}` }}</small></span>
								<span class="operations-row-meta"><strong>{{ formatTime(schedule.from_time) }} – {{ formatTime(schedule.to_time) }}</strong><small>{{ schedule.room || 'Room not assigned' }}</small></span>
							</button>
						</div>
					</article>

					<article class="operations-panel">
						<div class="operations-panel-header"><div><p class="edge-eyebrow">Class context</p><h2>{{ term('student_group', true, 'Classes') }}</h2></div><button type="button" class="edge-button" @click="openClassArms(false)">Manage</button></div>
						<EdgeEmptyState v-if="!context.student_groups?.length" :title="`No ${term('student_group', true, 'classes').toLowerCase()}`" description="Class context appears when the selected Branch and academic period have active groups." />
						<div v-else class="operations-list">
							<div v-for="group in context.student_groups.slice(0, 6)" :key="group.name" class="operations-row is-static">
								<span><strong>{{ group.hierarchy_label || group.student_group_name || group.name }}</strong><small>{{ group.student_count || 0 }} {{ term('student', true, 'students') }}</small></span>
							</div>
						</div>
					</article>

					<article class="operations-panel">
						<div class="operations-panel-header"><div><p class="edge-eyebrow">Attendance readiness</p><h2>Scheduled attendance coverage</h2></div><button type="button" class="edge-button" @click="openFocused('/app/eduedge-attendance')">Open Attendance</button></div>
						<EdgeEmptyState v-if="!context.attendance_coverage?.length" title="No scheduled registers" description="Attendance coverage follows exact Course Schedule identity for the selected date." />
						<div v-else class="operations-list">
							<button v-for="row in context.attendance_coverage" :key="row.course_schedule" type="button" class="operations-row" @click="openAttendanceCoverage(row)">
								<span><strong>{{ row.student_group_name }}</strong><small>{{ row.course || term('course', false, 'Subject') }} · {{ row.submitted }} of {{ row.expected }} submitted</small></span>
								<EdgeStatusBadge :label="row.complete ? 'Complete' : row.has_attendance ? `${row.missing} missing` : 'Not started'" :status="row.complete ? 'complete' : row.has_attendance ? 'partial' : 'missing'" :tone="row.complete ? 'success' : row.has_attendance ? 'warning' : 'danger'" />
							</button>
						</div>
						<small v-if="context.counts.attendance_incomplete_groups" class="operations-helper">{{ context.counts.attendance_incomplete_groups }} incomplete group register(s)</small>
					</article>

					<article class="operations-panel">
						<div class="operations-panel-header"><div><p class="edge-eyebrow">Facilities</p><h2>Room usage</h2></div><button v-if="canReadRooms" type="button" class="edge-button" @click="openFocused('/app/eduedge-teaching-schedule', { view: 'rooms' })">Open Rooms</button></div>
						<EdgeEmptyState v-if="!context.room_usage?.length" title="No room usage" description="Room usage appears when sessions are scheduled for the selected date." />
						<div v-else class="operations-list">
							<div v-for="row in context.room_usage" :key="row.room" class="operations-row is-static"><span><strong>{{ row.room }}</strong><small>{{ formatTime(row.first_start) }} – {{ formatTime(row.last_end) }}</small></span><EdgeStatusBadge :label="`${row.sessions} session${row.sessions === 1 ? '' : 's'}`" :status="row.is_unassigned ? 'missing' : 'active'" :tone="row.is_unassigned ? 'warning' : 'neutral'" /></div>
						</div>
					</article>

					<article class="operations-panel operations-panel--wide">
						<div class="operations-panel-header"><div><p class="edge-eyebrow">Attention needed</p><h2>Academic exceptions</h2></div><button type="button" class="edge-button" @click="openRoute('/app/eduedge-academic-readiness')">Readiness</button></div>
						<EdgeEmptyState v-if="!attentionItems.length" title="No immediate exceptions" description="No missing registers or unassigned rooms were found for the selected date." />
						<div v-else class="operations-list">
							<button v-for="item in attentionItems" :key="item.key" type="button" class="operations-row" @click="openFocused(item.route, item.query)"><span><strong>{{ item.title }}</strong><small>{{ item.description }}</small></span><EdgeStatusBadge :label="item.countLabel" status="attention" :tone="item.tone" /></button>
						</div>
					</article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const emptyPermissions = () => ({
	can_read_attendance: false,
	can_create_attendance: false,
	can_write_attendance: false,
	can_submit_attendance: false,
	can_create_student_group: false,
	can_create_course_schedule: false,
	can_read_rooms: false,
	can_read_instructor_assignments: false,
});
const emptyContext = () => ({
	user: {}, current_branch: {}, selected_branch: {}, allowed_branches: [], academic_calendar: {}, filters: {}, permissions: emptyPermissions(),
	counts: { student_groups: 0, assigned_instructors: 0, schedules: 0, attendance_complete_registers: 0, attendance_missing_registers: 0, attendance_missing_groups: 0, attendance_incomplete_groups: 0, unassigned_room_sessions: 0 },
	student_groups: [], schedules: [], attendance_coverage: [], room_usage: [],
});

export default {
	name: "EduEdgeAcademicOperations",
	data() {
		const today = frappe.datetime?.get_today?.() || new Date().toISOString().slice(0, 10);
		return { loading: true, error: "", menuItems: EDUEDGE_MENU_ITEMS, filters: { branch: "", date: today }, context: emptyContext() };
	},
	computed: {
		activeBranchName() { return this.context.selected_branch?.branch_name || this.context.current_branch?.branch_name || ""; },
		activeInstitutionName() { return this.context.selected_branch?.institution_name || ""; },
		calendarReady() { return Boolean(this.context.academic_calendar?.ready && !this.context.academic_calendar?.blocking_issue); },
		permissions() { return this.context.permissions || emptyPermissions(); },
		canCreateStudentGroup() { return Boolean(this.permissions.can_create_student_group); },
		canCreateCourseSchedule() { return Boolean(this.permissions.can_create_course_schedule); },
		canReadRooms() { return Boolean(this.permissions.can_read_rooms); },
		canReadInstructorAssignments() { return Boolean(this.permissions.can_read_instructor_assignments); },
		canReadAttendance() { return Boolean(this.permissions.can_read_attendance); },
		canManageAttendance() { return Boolean(this.permissions.can_create_attendance || this.permissions.can_write_attendance); },
		canSubmitAttendance() { return Boolean(this.permissions.can_submit_attendance); },
		attentionItems() {
			const items = [];
			const missing = Number(this.context.counts.attendance_missing_registers || this.context.counts.attendance_missing_groups || 0);
			const roomGaps = Number(this.context.counts.unassigned_room_sessions || 0);
			if (missing) items.push({ key: "attendance", title: "Missing attendance registers", description: "Scheduled sessions have no submitted attendance.", countLabel: `${missing} missing`, tone: "danger", route: "/app/eduedge-attendance", query: { tab: "missing" } });
			if (roomGaps) items.push({ key: "rooms", title: "Room allocation gaps", description: "Some scheduled sessions do not have rooms assigned.", countLabel: `${roomGaps} sessions`, tone: "warning", route: "/app/eduedge-teaching-schedule", query: { view: "rooms" } });
			return items;
		},
	},
	mounted() { this.loadContext(); },
	methods: {
		openRoute: openEduEdgeRoute,
		term(key, plural = false, fallback = "") { return frappe.eduedge?.term?.(key, { plural, context: this.context, fallback }) || fallback; },
		formatTime(value) { return String(value || "").slice(0, 5) || "—"; },
		classArmsRoute(createMode = false) {
			const params = new URLSearchParams();
			if (this.filters.branch) params.set("branch", this.filters.branch);
			if (this.context.filters?.academic_year) params.set("academic_year", this.context.filters.academic_year);
			if (this.context.filters?.academic_term) params.set("academic_term", this.context.filters.academic_term);
			if (createMode) params.set("mode", "create");
			const query = params.toString();
			return `/app/eduedge-class-arms${query ? `?${query}` : ""}`;
		},
		openClassArms(createMode = false) { window.location.href = this.classArmsRoute(createMode); },
		openFocused(route, extra = {}) {
			const params = new URLSearchParams({ date: this.filters.date, ...extra });
			openEduEdgeRoute(`${route}?${params.toString()}`);
		},
		openAttendanceCoverage(row) {
			if (!row?.course_schedule) return;
			const params = new URLSearchParams({ date: this.filters.date, course_schedule: row.course_schedule, tab: "take" });
			openEduEdgeRoute(`/app/eduedge-attendance?${params.toString()}`);
		},
		openSchedule(name) { if (name) window.location.href = `/app/course-schedule/${encodeURIComponent(name)}`; },
		async loadContext() {
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.academic_operations.get_operations_context", { branch: this.filters.branch || undefined, date: this.filters.date });
				this.context = response.message || emptyContext();
				this.filters.branch = this.context.filters?.branch || this.filters.branch;
				this.filters.date = this.context.filters?.date || this.filters.date;
			} catch (error) { this.error = error?.message || "Academic operations context could not be loaded."; }
			finally { this.loading = false; }
		},
		async changeBranch() {
			if (!this.filters.branch) return;
			try {
				await frappe.call("eduedge.api.branch_context.switch_school_branch", { branch: this.filters.branch });
				await this.loadContext();
			} catch (error) { frappe.msgprint({ title: __("Unable to switch Branch"), message: error?.message || __("The selected Branch could not be activated."), indicator: "red" }); }
		},
	},
};
</script>

<style scoped>
.operations-filter-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(14rem,1fr)); gap:.75rem; width:100%; }
.operations-filter-grid label { display:grid; gap:.35rem; font-weight:600; }
.operations-context-strip { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)) auto; gap:1rem; align-items:center; padding:1rem; margin:1rem 0; border:1px solid var(--edge-color-border,var(--border-color)); border-radius:var(--edge-radius-lg,12px); background:var(--edge-color-surface,var(--card-bg)); }
.operations-context-strip > div { display:grid; gap:.2rem; }
.operations-context-strip span { color:var(--edge-color-ink-500,var(--text-muted)); font-size:.8rem; }
.operations-actions { display:grid; grid-template-columns:repeat(auto-fit,minmax(13rem,1fr)); gap:.75rem; margin-top:1rem; }
.operation-action { display:grid; gap:.25rem; padding:.9rem; text-align:left; border:1px solid var(--edge-color-border,var(--border-color)); border-radius:var(--edge-radius-md,8px); background:var(--edge-color-surface-muted,var(--control-bg)); color:var(--edge-color-ink-800,var(--text-color)); }
.operation-action:hover { border-color:var(--primary); }
.operation-action span { color:var(--edge-color-ink-500,var(--text-muted)); font-size:.78rem; line-height:1.35; }
.operations-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1rem; margin-top:1rem; }
.operations-panel { padding:1rem; border:1px solid var(--edge-color-border,var(--border-color)); border-radius:var(--edge-radius-lg,12px); background:var(--edge-color-surface,var(--card-bg)); }
.operations-panel--wide { grid-column:1/-1; }
.operations-panel-header { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:1rem; }
.operations-panel-header h2 { margin:.2rem 0 0; }
.operations-list { display:grid; gap:.65rem; }
.operations-row { display:flex; justify-content:space-between; align-items:center; gap:1rem; width:100%; padding:.8rem; text-align:left; border:1px solid var(--edge-color-border,var(--border-color)); border-radius:var(--edge-radius-md,8px); background:var(--edge-color-surface-muted,var(--control-bg)); color:var(--edge-color-ink-800,var(--text-color)); }
.operations-row:not(.is-static):hover { border-color:var(--primary); }
.operations-row > span { display:grid; gap:.2rem; }
.operations-row small,.operations-helper { color:var(--edge-color-ink-500,var(--text-muted)); }
.operations-row-meta { text-align:right; }
.operations-helper { display:block; margin-top:.75rem; }
@media (max-width:900px) { .operations-context-strip,.operations-grid { grid-template-columns:1fr; } .operations-panel--wide { grid-column:auto; } .operations-row-meta { text-align:left; } }
</style>
