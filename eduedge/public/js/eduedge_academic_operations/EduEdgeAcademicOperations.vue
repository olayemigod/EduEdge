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
					action-label="Teaching Schedule"
					@action="openFocused('/app/eduedge-teaching-schedule')"
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
					<EdgeStatusBadge :label="calendarReady ? 'Calendar ready' : 'Calendar attention'" :status="calendarReady ? 'ready' : 'warning'" :tone="calendarReady ? 'success' : 'warning'" />
				</section>

				<EdgeActionBar v-if="context.academic_calendar?.blocking_issue" :label="context.academic_calendar.blocking_issue">
					<template #actions><button type="button" class="edge-button" @click="openRoute('/app/eduedge-academic-foundation')">Review Academic Calendar</button></template>
				</EdgeActionBar>

				<EdgeDashboardLayout min-column-width="11rem">
					<EdgeStatCard label="Classes" :value="context.counts.student_groups || 0" helper="Active groups in the resolved academic period" />
					<EdgeStatCard label="Scheduled Sessions" :value="context.counts.schedules || 0" helper="Teaching sessions for selected date" />
					<EdgeStatCard label="Assigned Instructors" :value="context.counts.assigned_instructors || 0" helper="Current Branch assignment coverage" />
					<EdgeStatCard label="Attendance Complete" :value="context.counts.attendance_complete_registers || 0" tone="success" helper="Scheduled registers completed" />
					<EdgeStatCard label="Missing Registers" :value="context.counts.attendance_missing_registers || 0" :tone="context.counts.attendance_missing_registers ? 'danger' : 'success'" helper="Sessions with no submitted attendance" />
					<EdgeStatCard label="Room Gaps" :value="context.counts.unassigned_room_sessions || 0" :tone="context.counts.unassigned_room_sessions ? 'warning' : 'success'" helper="Scheduled sessions without rooms" />
				</EdgeDashboardLayout>

				<section class="operations-actions" aria-label="Academic operation areas">
					<button type="button" class="operation-action" @click="openFocused('/app/eduedge-teaching-schedule')"><strong>Teaching Schedule</strong><span>Day, week, upcoming sessions and rooms</span></button>
					<button type="button" class="operation-action" @click="openFocused('/app/eduedge-attendance')"><strong>Attendance</strong><span>Take attendance and resolve missing registers</span></button>
					<button type="button" class="operation-action" @click="openRoute('/app/eduedge-instructor-assignments')"><strong>Instructor Assignments</strong><span>Teaching responsibility and Branch eligibility</span></button>
					<button type="button" class="operation-action" @click="openRoute('/app/eduedge-schemes-of-work')"><strong>Scheme of Work</strong><span>Approved curriculum delivery plan</span></button>
					<button type="button" class="operation-action" @click="openRoute('/app/eduedge-lesson-plans')"><strong>Lesson Plans</strong><span>Teaching preparation and evidence</span></button>
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
								<span><strong>{{ schedule.course || 'Subject not set' }}</strong><small>{{ schedule.student_group }} · {{ schedule.instructor_name || schedule.instructor || 'No Instructor' }}</small></span>
								<span class="operations-row-meta"><strong>{{ formatTime(schedule.from_time) }} – {{ formatTime(schedule.to_time) }}</strong><small>{{ schedule.room || 'Room not assigned' }}</small></span>
							</button>
						</div>
					</article>

					<article class="operations-panel">
						<div class="operations-panel-header">
							<div><p class="edge-eyebrow">Attention needed</p><h2>Academic exceptions</h2></div>
							<button type="button" class="edge-button" @click="openRoute('/app/eduedge-academic-readiness')">Readiness</button>
						</div>
						<EdgeEmptyState v-if="!attentionItems.length" title="No immediate exceptions" description="No missing registers or unassigned rooms were found for the selected date." />
						<div v-else class="operations-list">
							<button v-for="item in attentionItems" :key="item.key" type="button" class="operations-row" @click="openFocused(item.route)">
								<span><strong>{{ item.title }}</strong><small>{{ item.description }}</small></span>
								<EdgeStatusBadge :label="item.countLabel" status="attention" :tone="item.tone" />
							</button>
						</div>
					</article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const emptyContext = () => ({
	user: {}, current_branch: {}, selected_branch: {}, allowed_branches: [], academic_calendar: {}, filters: {}, permissions: {},
	counts: { student_groups: 0, assigned_instructors: 0, schedules: 0, attendance_complete_registers: 0, attendance_missing_registers: 0, unassigned_room_sessions: 0 },
	schedules: [], attendance_coverage: [], room_usage: [],
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
		attentionItems() {
			const items = [];
			const missing = Number(this.context.counts.attendance_missing_registers || 0);
			const roomGaps = Number(this.context.counts.unassigned_room_sessions || 0);
			if (missing) items.push({ key: "attendance", title: "Missing attendance registers", description: "Scheduled sessions have no submitted attendance.", countLabel: `${missing} missing`, tone: "danger", route: "/app/eduedge-attendance" });
			if (roomGaps) items.push({ key: "rooms", title: "Room allocation gaps", description: "Some scheduled sessions do not have rooms assigned.", countLabel: `${roomGaps} sessions`, tone: "warning", route: "/app/eduedge-teaching-schedule" });
			return items;
		},
	},
	mounted() { this.loadContext(); },
	methods: {
		openRoute: openEduEdgeRoute,
		formatTime(value) { return String(value || "").slice(0, 5) || "—"; },
		openFocused(route) {
			const query = new URLSearchParams({ date: this.filters.date }).toString();
			openEduEdgeRoute(`${route}?${query}`);
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
.operations-panel-header { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:1rem; }
.operations-panel-header h2 { margin:.2rem 0 0; }
.operations-list { display:grid; gap:.65rem; }
.operations-row { display:flex; justify-content:space-between; align-items:center; gap:1rem; width:100%; padding:.8rem; text-align:left; border:1px solid var(--edge-color-border,var(--border-color)); border-radius:var(--edge-radius-md,8px); background:var(--edge-color-surface-muted,var(--control-bg)); color:var(--edge-color-ink-800,var(--text-color)); }
.operations-row:hover { border-color:var(--primary); }
.operations-row > span { display:grid; gap:.2rem; }
.operations-row small { color:var(--edge-color-ink-500,var(--text-muted)); }
.operations-row-meta { text-align:right; }
@media (max-width:900px) { .operations-context-strip,.operations-grid { grid-template-columns:1fr; } .operations-row-meta { text-align:left; } }
</style>
