<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="context.tenant_name || ''"
		:branch-name="activeBranchName"
		:user-name="context.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-teaching-schedule"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Academic Operations"
					title="Teaching Schedule"
					subtitle="Plan and review class sessions without mixing timetable work with attendance and other academic operations."
					:action-label="canCreateCourseSchedule ? 'Add Schedule' : ''"
					@action="addSchedule"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading teaching schedule..." :skeleton="true" />
			<EdgeErrorState v-else-if="error" title="Teaching Schedule could not load" :message="error" action-label="Try again" @retry="load" />
			<template v-else>
				<EdgeFilterBar title="Schedule context">
					<div class="schedule-filter-grid">
						<label>
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="changeBranch">
								<option v-for="branch in context.allowed_branches" :key="branch.name" :value="branch.name">{{ branch.branch_name }}</option>
							</select>
						</label>
						<label>
							<span>Reference Date</span>
							<input v-model="filters.reference_date" type="date" class="form-control" @change="load" />
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" @click="openNativeList">Native Schedule List</button>
						<button type="button" class="edge-button edge-button--primary" @click="load">Refresh</button>
					</template>
				</EdgeFilterBar>

				<div class="schedule-tabs" role="tablist" aria-label="Teaching Schedule views">
					<button v-for="tab in tabs" :key="tab.key" type="button" class="edge-button" :class="{ 'edge-button--primary': filters.view === tab.key }" @click="selectView(tab.key)">{{ tab.label }}</button>
				</div>

				<EdgeActionBar v-if="!calendarReady" label="A valid Academic Session and Term / Semester must cover the reference date before a new schedule can be created.">
					<template #actions><button type="button" class="edge-button" @click="openRoute('/app/eduedge-academic-foundation')">Review Academic Calendar</button></template>
				</EdgeActionBar>

				<EdgeDashboardLayout min-column-width="11rem">
					<EdgeStatCard label="Sessions" :value="context.counts.schedules || 0" :helper="rangeLabel" />
					<EdgeStatCard label="Instructors" :value="context.counts.instructors || 0" helper="Distinct scheduled instructors" />
					<EdgeStatCard label="Classes" :value="context.counts.student_groups || 0" helper="Distinct scheduled class arms / groups" />
					<EdgeStatCard label="Rooms" :value="context.counts.rooms || 0" :helper="`${context.counts.unassigned_rooms || 0} sessions without rooms`" />
				</EdgeDashboardLayout>

				<section v-if="filters.view === 'rooms'" class="schedule-panel">
					<div class="schedule-panel-header"><div><p class="edge-eyebrow">Facilities</p><h2>Room usage for {{ context.start_date }}</h2></div></div>
					<EdgeEmptyState v-if="!context.room_usage.length" title="No rooms scheduled" description="Room usage will appear when Course Schedules exist for the selected date." />
					<div v-else class="schedule-room-list">
						<div v-for="row in context.room_usage" :key="row.room" class="schedule-room-row">
							<span><strong>{{ row.room }}</strong><small>{{ formatTime(row.first_start) }} – {{ formatTime(row.last_end) }}</small></span>
							<EdgeStatusBadge :label="`${row.sessions} session${row.sessions === 1 ? '' : 's'}`" :status="row.is_unassigned ? 'missing' : 'active'" :tone="row.is_unassigned ? 'warning' : 'neutral'" />
						</div>
					</div>
				</section>

				<section v-else class="schedule-panel">
					<div class="schedule-panel-header">
						<div><p class="edge-eyebrow">{{ activeTabLabel }}</p><h2>{{ rangeLabel }}</h2></div>
						<button v-if="canCreateCourseSchedule" type="button" class="edge-button edge-button--primary" @click="addSchedule">Add Schedule</button>
					</div>
					<EdgeEmptyState v-if="!context.schedules.length" title="No scheduled sessions" description="Choose another date or add a Course Schedule for this Branch." />
					<div v-else class="schedule-list">
						<button v-for="row in context.schedules" :key="row.name" type="button" class="schedule-card" @click="openSchedule(row.name)">
							<div class="schedule-card-date"><strong>{{ row.schedule_date }}</strong><span>{{ formatTime(row.from_time) }} – {{ formatTime(row.to_time) }}</span></div>
							<div class="schedule-card-main"><strong>{{ row.course || 'Subject not set' }}</strong><span>{{ row.student_group_name || row.student_group || 'Class not set' }}</span><small>{{ row.instructor_name || row.instructor || 'Instructor not assigned' }}</small></div>
							<div class="schedule-card-room"><span>{{ row.room || 'Room not assigned' }}</span><small>Open schedule →</small></div>
						</button>
					</div>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const emptyContext = () => ({
	user: {}, selected_branch: {}, current_branch: {}, allowed_branches: [], permissions: {}, academic_calendar: {},
	counts: { schedules: 0, instructors: 0, student_groups: 0, rooms: 0, unassigned_rooms: 0 }, schedules: [], room_usage: [],
});

export default {
	name: "EduEdgeTeachingSchedule",
	data() {
		const today = frappe.datetime?.get_today?.() || new Date().toISOString().slice(0, 10);
		return {
			loading: true,
			error: "",
			menuItems: EDUEDGE_MENU_ITEMS,
			filters: { branch: "", reference_date: today, view: "day" },
			context: emptyContext(),
			tabs: [
				{ key: "day", label: "Day" },
				{ key: "week", label: "Week" },
				{ key: "upcoming", label: "Upcoming" },
				{ key: "rooms", label: "Rooms" },
			],
		};
	},
	computed: {
		activeBranchName() { return this.context.selected_branch?.branch_name || this.context.current_branch?.branch_name || ""; },
		calendarReady() { return Boolean(this.context.academic_calendar?.ready); },
		canCreateCourseSchedule() {
			const serverAllows = Boolean(this.context.permissions?.can_create_course_schedule);
			const clientAllows = typeof frappe.model?.can_create === "function" ? Boolean(frappe.model.can_create("Course Schedule")) : false;
			return serverAllows || clientAllows;
		},
		activeTabLabel() { return this.tabs.find((tab) => tab.key === this.filters.view)?.label || "Schedule"; },
		rangeLabel() {
			if (!this.context.start_date) return "Selected period";
			return this.context.start_date === this.context.end_date ? this.context.start_date : `${this.context.start_date} – ${this.context.end_date}`;
		},
	},
	mounted() {
		const params = new URLSearchParams(window.location.search || "");
		if (params.get("date")) this.filters.reference_date = params.get("date");
		if (["day", "week", "upcoming", "rooms"].includes(params.get("view"))) this.filters.view = params.get("view");
		this.load();
	},
	methods: {
		openRoute: openEduEdgeRoute,
		formatTime(value) { return String(value || "").slice(0, 5) || "—"; },
		async load() {
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.teaching_schedule.get_teaching_schedule_context", {
					branch: this.filters.branch || undefined,
					reference_date: this.filters.reference_date,
					view: this.filters.view,
				});
				this.context = response.message || emptyContext();
				this.filters.branch = this.context.selected_branch?.name || this.filters.branch;
				this.filters.reference_date = this.context.reference_date || this.filters.reference_date;
			} catch (error) { this.error = error?.message || "Teaching Schedule could not be loaded."; }
			finally { this.loading = false; }
		},
		async changeBranch() {
			if (!this.filters.branch) return;
			try {
				await frappe.call("eduedge.api.branch_context.switch_school_branch", { branch: this.filters.branch });
				await this.load();
			} catch (error) { frappe.msgprint({ title: __("Unable to switch Branch"), message: error?.message || __("The selected Branch could not be activated."), indicator: "red" }); }
		},
		selectView(view) { this.filters.view = view; this.load(); },
		addSchedule() {
			if (!this.canCreateCourseSchedule) return;
			if (!this.calendarReady) {
				frappe.msgprint({ title: __("Academic Calendar required"), message: __("Configure an Academic Session and Term / Semester covering the selected date before adding a Schedule."), indicator: "orange" });
				return;
			}
			window.location.href = "/app/course-schedule/new-course-schedule";
		},
		openSchedule(name) { if (name) window.location.href = `/app/course-schedule/${encodeURIComponent(name)}`; },
		openNativeList() { window.location.href = "/app/course-schedule"; },
	},
};
</script>

<style scoped>
.schedule-filter-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(14rem,1fr)); gap:.75rem; width:100%; }
.schedule-filter-grid label { display:grid; gap:.35rem; font-weight:600; }
.schedule-tabs { display:flex; flex-wrap:wrap; gap:.5rem; margin:1rem 0; }
.schedule-panel { margin-top:1rem; padding:1rem; border:1px solid var(--edge-color-border,var(--border-color)); border-radius:var(--edge-radius-lg,12px); background:var(--edge-color-surface,var(--card-bg)); }
.schedule-panel-header { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:1rem; }
.schedule-panel-header h2 { margin:.2rem 0 0; }
.schedule-list,.schedule-room-list { display:grid; gap:.65rem; }
.schedule-card { display:grid; grid-template-columns:minmax(9rem,.65fr) minmax(15rem,1.5fr) minmax(9rem,.7fr); gap:1rem; align-items:center; width:100%; padding:.85rem; text-align:left; border:1px solid var(--edge-color-border,var(--border-color)); border-radius:var(--edge-radius-md,8px); background:var(--edge-color-surface-muted,var(--control-bg)); color:var(--edge-color-ink-800,var(--text-color)); }
.schedule-card:hover { border-color:var(--primary); }
.schedule-card-date,.schedule-card-main,.schedule-card-room,.schedule-room-row span { display:grid; gap:.2rem; }
.schedule-card span,.schedule-card small,.schedule-room-row small { color:var(--edge-color-ink-500,var(--text-muted)); }
.schedule-card-room { text-align:right; }
.schedule-room-row { display:flex; justify-content:space-between; gap:1rem; align-items:center; padding:.8rem; border:1px solid var(--edge-color-border,var(--border-color)); border-radius:var(--edge-radius-md,8px); background:var(--edge-color-surface-muted,var(--control-bg)); }
@media (max-width:780px) { .schedule-card { grid-template-columns:1fr; } .schedule-card-room { text-align:left; } }
</style>
