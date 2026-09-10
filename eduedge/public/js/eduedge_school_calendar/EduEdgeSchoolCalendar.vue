<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="context.institution_name || ''"
		:branch-name="selectedBranchLabel"
		:menu-items="menuItems"
		active-route="/app/eduedge-school-calendar"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<section class="school-calendar-shell">
				<header class="school-calendar-header">
					<div>
						<p class="edge-eyebrow">Academic & School Operations</p>
						<h2>School Calendar</h2>
						<p>One calendar for academic periods, assessments, CBT schedules, teaching schedules and managed school events.</p>
					</div>
					<div class="school-calendar-actions">
						<button type="button" class="edge-button" :disabled="loading" @click="load">Refresh</button>
						<button v-if="context.permissions?.event_create" type="button" class="edge-button edge-button--primary" @click="openEventDialog()">New School Event</button>
					</div>
				</header>

				<div class="school-calendar-filters">
					<label><span>Branch / Campus</span><select v-model="branch" class="form-control" @change="contextChanged"><option v-for="row in context.branches || []" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option></select></label>
					<label><span>Academic Session</span><select v-model="academicYear" class="form-control" @change="sessionChanged"><option v-for="row in context.sessions || []" :key="row.name" :value="row.name">{{ row.academic_year_name || row.name }}</option></select></label>
					<label><span>Term / Semester</span><select v-model="academicTerm" class="form-control" @change="load"><option value="">All Terms</option><option v-for="row in context.terms || []" :key="row.name" :value="row.name">{{ row.term_name || row.name }}</option></select></label>
					<label><span>Event Type</span><select v-model="eventType" class="form-control" @change="load"><option value="">All Event Types</option><option v-for="value in eventTypes" :key="value" :value="value">{{ value }}</option></select></label>
					<label><span>Audience</span><select v-model="audience" class="form-control" @change="load"><option value="">All Audiences</option><option v-for="value in audiences" :key="value" :value="value">{{ value }}</option></select></label>
					<label class="school-calendar-toggle"><input v-model="includeTeaching" type="checkbox" @change="load" /><span>Show Teaching Schedule</span></label>
				</div>

				<div class="school-calendar-toolbar">
					<div class="school-calendar-view-tabs">
						<button v-for="mode in viewModes" :key="mode.value" type="button" :class="['edge-button', { 'is-active': viewMode === mode.value }]" @click="setView(mode.value)">{{ mode.label }}</button>
					</div>
					<div class="school-calendar-nav">
						<button type="button" class="edge-button" @click="move(-1)">Previous</button>
						<button type="button" class="edge-button" @click="goToday">Today</button>
						<strong>{{ periodLabel }}</strong>
						<button type="button" class="edge-button" @click="move(1)">Next</button>
					</div>
				</div>

				<div v-if="error" class="school-calendar-message is-error">{{ error }}</div>
				<div v-else-if="loading" class="school-calendar-message">Loading calendar...</div>
				<template v-else>
					<div v-if="viewMode === 'month'" class="school-calendar-month">
						<div v-for="name in weekNames" :key="name" class="school-calendar-week-name">{{ name }}</div>
						<article v-for="day in monthDays" :key="day.key" :class="['school-calendar-day', { 'is-outside': !day.currentMonth, 'is-today': day.isToday }]">
							<header><strong>{{ day.date.getDate() }}</strong><small>{{ shortDate(day.date) }}</small></header>
							<button v-for="item in itemsForDate(day.key).slice(0, 5)" :key="item.id" type="button" :class="['school-calendar-item', categoryClass(item.category)]" @click="openItem(item)">
								<strong>{{ item.title }}</strong><small>{{ item.all_day ? 'All day' : timeLabel(item.starts_on) }} · {{ item.category }}</small>
							</button>
							<small v-if="itemsForDate(day.key).length > 5" class="school-calendar-more">+{{ itemsForDate(day.key).length - 5 }} more</small>
						</article>
					</div>

					<div v-else-if="viewMode === 'week'" class="school-calendar-week">
						<article v-for="day in weekDays" :key="day.key" :class="['school-calendar-week-day', { 'is-today': day.isToday }]">
							<header><strong>{{ weekdayLabel(day.date) }}</strong><small>{{ shortDate(day.date) }}</small></header>
							<div v-if="!itemsForDate(day.key).length" class="school-calendar-empty">No calendar items</div>
							<button v-for="item in itemsForDate(day.key)" :key="item.id" type="button" :class="['school-calendar-item', categoryClass(item.category)]" @click="openItem(item)">
								<strong>{{ item.title }}</strong><small>{{ item.all_day ? 'All day' : `${timeLabel(item.starts_on)} – ${timeLabel(item.ends_on)}` }}</small><small>{{ item.category }}<template v-if="item.venue"> · {{ item.venue }}</template></small>
							</button>
						</article>
					</div>

					<div v-else class="school-calendar-agenda">
						<article v-for="group in agendaGroups" :key="group.key" class="school-calendar-agenda-day">
							<header><strong>{{ fullDate(group.date) }}</strong><span>{{ group.items.length }} item{{ group.items.length === 1 ? '' : 's' }}</span></header>
							<button v-for="item in group.items" :key="item.id" type="button" class="school-calendar-agenda-item" @click="openItem(item)">
								<div><strong>{{ item.title }}</strong><small>{{ item.category }} · {{ item.status || item.source_type }}</small></div>
								<div><span>{{ item.all_day ? 'All day' : `${timeLabel(item.starts_on)} – ${timeLabel(item.ends_on)}` }}</span><small v-if="item.venue">{{ item.venue }}</small><small v-if="item.audience">{{ item.audience }}</small></div>
							</button>
						</article>
						<div v-if="!agendaGroups.length" class="school-calendar-message">No calendar items in this period.</div>
					</div>
				</template>
			</section>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const GET_METHOD = "eduedge.api.school_calendar.get_school_calendar_context";
const GET_EVENT_METHOD = "eduedge.api.school_calendar.get_school_event";
const GET_OPTIONS_METHOD = "eduedge.api.school_calendar.get_event_form_options";
const SAVE_EVENT_METHOD = "eduedge.api.school_calendar.save_school_event";
const SET_STATUS_METHOD = "eduedge.api.school_calendar.set_school_event_status";

const EVENT_TYPES = ["Academic", "Examination", "PTA / Parent Meeting", "Open Day", "Sports", "Cultural", "Graduation", "Excursion / Trip", "Staff Meeting / Training", "Boarding", "Holiday / Closure", "Special Assembly", "Other"];
const AUDIENCES = ["Everyone", "Students", "Parents / Guardians", "Staff", "Teachers / Instructors", "Specific Class", "Specific Class Arm", "Specific Programme", "Boarding Students"];

function isoDate(date) {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, "0");
	const day = String(date.getDate()).padStart(2, "0");
	return `${year}-${month}-${day}`;
}

function startOfWeek(date) {
	const value = new Date(date);
	const offset = (value.getDay() + 6) % 7;
	value.setDate(value.getDate() - offset);
	value.setHours(0, 0, 0, 0);
	return value;
}

export default {
	name: "EduEdgeSchoolCalendar",
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS,
			loading: true,
			error: "",
			context: {},
			branch: "",
			academicYear: "",
			academicTerm: "",
			eventType: "",
			audience: "",
			includeTeaching: false,
			viewMode: "month",
			anchorDate: new Date(),
			items: [],
			eventTypes: EVENT_TYPES,
			audiences: AUDIENCES,
			viewModes: [
				{ value: "month", label: "Month" },
				{ value: "week", label: "Week" },
				{ value: "agenda", label: "Agenda" },
			],
			weekNames: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
		};
	},
	computed: {
		selectedBranchLabel() {
			const row = (this.context.branches || []).find((item) => item.name === this.branch);
			return row?.branch_name || this.branch || "School Calendar";
		},
		requestRange() {
			if (this.viewMode === "week") {
				const start = startOfWeek(this.anchorDate);
				const end = new Date(start); end.setDate(end.getDate() + 6);
				return { start, end };
			}
			const first = new Date(this.anchorDate.getFullYear(), this.anchorDate.getMonth(), 1);
			const start = startOfWeek(first);
			const end = new Date(start); end.setDate(end.getDate() + 41);
			return { start, end };
		},
		periodLabel() {
			if (this.viewMode === "week") return `${this.shortDate(this.requestRange.start)} – ${this.shortDate(this.requestRange.end)}`;
			return this.anchorDate.toLocaleDateString(undefined, { month: "long", year: "numeric" });
		},
		monthDays() {
			const days = [];
			const currentMonth = this.anchorDate.getMonth();
			const today = isoDate(new Date());
			const cursor = new Date(this.requestRange.start);
			for (let index = 0; index < 42; index += 1) {
				const date = new Date(cursor);
				const key = isoDate(date);
				days.push({ date, key, currentMonth: date.getMonth() === currentMonth, isToday: key === today });
				cursor.setDate(cursor.getDate() + 1);
			}
			return days;
		},
		weekDays() {
			const days = [];
			const today = isoDate(new Date());
			const cursor = new Date(this.requestRange.start);
			for (let index = 0; index < 7; index += 1) {
				const date = new Date(cursor); const key = isoDate(date);
				days.push({ date, key, isToday: key === today });
				cursor.setDate(cursor.getDate() + 1);
			}
			return days;
		},
		agendaGroups() {
			const grouped = new Map();
			for (const item of this.items) {
				const key = String(item.starts_on || "").slice(0, 10);
				if (!key) continue;
				if (!grouped.has(key)) grouped.set(key, []);
				grouped.get(key).push(item);
			}
			return [...grouped.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([key, items]) => ({ key, date: new Date(`${key}T00:00:00`), items }));
		},
	},
	mounted() { this.load(); },
	methods: {
		openRoute: openEduEdgeRoute,
		async load() {
			this.loading = true; this.error = "";
			try {
				const range = this.requestRange;
				const response = await frappe.call(GET_METHOD, {
					branch: this.branch || undefined,
					academic_year: this.academicYear || undefined,
					academic_term: this.academicTerm || undefined,
					start: isoDate(range.start), end: isoDate(range.end),
					event_type: this.eventType || undefined, audience: this.audience || undefined,
					include_teaching: this.includeTeaching ? 1 : 0,
				});
				const payload = response.message || {};
				this.context = payload;
				this.branch = payload.branch || this.branch;
				this.academicYear = payload.academic_year || this.academicYear;
				this.academicTerm = payload.academic_term || this.academicTerm;
				this.items = payload.items || [];
			} catch (error) {
				this.error = error?.message || "School Calendar could not be loaded.";
			} finally { this.loading = false; }
		},
		async contextChanged() { this.academicTerm = ""; await this.load(); },
		async sessionChanged() { this.academicTerm = ""; await this.load(); },
		setView(mode) { this.viewMode = mode; this.load(); },
		move(direction) {
			const next = new Date(this.anchorDate);
			if (this.viewMode === "week") next.setDate(next.getDate() + (7 * direction));
			else next.setMonth(next.getMonth() + direction);
			this.anchorDate = next; this.load();
		},
		goToday() { this.anchorDate = new Date(); this.load(); },
		itemsForDate(key) { return this.items.filter((item) => String(item.starts_on || "").slice(0, 10) === key); },
		shortDate(date) { return date.toLocaleDateString(undefined, { day: "numeric", month: "short" }); },
		fullDate(date) { return date.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long", year: "numeric" }); },
		weekdayLabel(date) { return date.toLocaleDateString(undefined, { weekday: "short" }); },
		timeLabel(value) { if (!value) return ""; const date = new Date(String(value).replace(" ", "T")); return Number.isNaN(date.getTime()) ? String(value).slice(11, 16) : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); },
		categoryClass(category) { return `category-${String(category || "other").toLowerCase().replace(/[^a-z0-9]+/g, "-")}`; },
		openItem(item) {
			if (item.source_type === "School Event" && item.editable) { this.openEventDialog(item.source_name); return; }
			if (item.route) window.open(item.route, "_blank", "noopener,noreferrer");
		},
		async openEventDialog(name = "") {
			let values = {
				school_branch: this.branch, academic_year: this.academicYear, academic_term: this.academicTerm,
				event_type: "Other", audience_scope: "Everyone", visibility: "Internal", all_day: 0,
				registration_required: 0, attendance_required: 0, reminder_minutes_before: 0,
			};
			if (name) {
				const response = await frappe.call(GET_EVENT_METHOD, { name });
				values = { ...values, ...(response.message?.values || {}) };
			}
			const optionsResponse = await frappe.call(GET_OPTIONS_METHOD, { branch: values.school_branch, academic_year: values.academic_year, program: values.program || undefined });
			let options = optionsResponse.message || { terms: [], programs: [], class_arms: [] };
			const termOptions = () => ["", ...(options.terms || []).map((row) => row.name)];
			const programOptions = () => ["", ...(options.programs || []).map((row) => row.value)];
			const armOptions = (program = "") => ["", ...(options.class_arms || []).filter((row) => !program || row.program === program).map((row) => row.value)];
			const dialog = new frappe.ui.Dialog({
				title: __(name ? "Edit School Event" : "New School Event"),
				fields: [
					{ fieldname: "event_title", fieldtype: "Data", label: __("Event Title"), reqd: 1 },
					{ fieldname: "event_type", fieldtype: "Select", label: __("Event Type"), options: EVENT_TYPES.join("\n"), reqd: 1 },
					{ fieldtype: "Section Break", label: __("Academic Context") },
					{ fieldname: "school_branch", fieldtype: "Link", label: __("School Branch / Campus"), options: "EduEdge School Branch", reqd: 1, read_only: 1 },
					{ fieldname: "academic_year", fieldtype: "Link", label: __("Academic Session"), options: "Academic Year", reqd: 1, read_only: 1 },
					{ fieldname: "academic_term", fieldtype: "Select", label: __("Term / Semester"), options: termOptions().join("\n") },
					{ fieldtype: "Section Break", label: __("Date, Time and Venue") },
					{ fieldname: "starts_on", fieldtype: "Datetime", label: __("Starts On"), reqd: 1 },
					{ fieldname: "ends_on", fieldtype: "Datetime", label: __("Ends On"), reqd: 1 },
					{ fieldname: "all_day", fieldtype: "Check", label: __("All-day Event") },
					{ fieldname: "venue", fieldtype: "Data", label: __("Venue") },
					{ fieldtype: "Section Break", label: __("Audience") },
					{ fieldname: "audience_scope", fieldtype: "Select", label: __("Audience"), options: AUDIENCES.join("\n"), reqd: 1 },
					{ fieldname: "program", fieldtype: "Select", label: __("Class / Programme"), options: programOptions().join("\n") },
					{ fieldname: "student_group", fieldtype: "Select", label: __("Class Arm"), options: armOptions(values.program).join("\n") },
					{ fieldname: "visibility", fieldtype: "Select", label: __("Visibility"), options: "Internal\nPortal\nPublic", reqd: 1 },
					{ fieldname: "registration_required", fieldtype: "Check", label: __("Registration Required") },
					{ fieldname: "attendance_required", fieldtype: "Check", label: __("Attendance Tracking Required") },
					{ fieldtype: "Section Break", label: __("Publishing and Details") },
					{ fieldname: "reminder_minutes_before", fieldtype: "Int", label: __("Reminder Minutes Before") },
					{ fieldname: "publish_from", fieldtype: "Datetime", label: __("Publish From") },
					{ fieldname: "publish_until", fieldtype: "Datetime", label: __("Publish Until") },
					{ fieldname: "description", fieldtype: "Text Editor", label: __("Description") },
				],
				primary_action_label: __(name ? "Save Event" : "Create Event"),
				primary_action: async (formValues) => {
					dialog.disable_primary_action();
					try {
						await frappe.call({ method: SAVE_EVENT_METHOD, type: "POST", args: { values: formValues, name: name || undefined } });
						dialog.hide(); frappe.show_alert({ message: __("School Event saved"), indicator: "green" }); await this.load();
					} catch (error) { frappe.msgprint({ title: __("School Event could not be saved"), message: error?.message || __("Review the Event details and try again."), indicator: "red" }); }
					finally { dialog.enable_primary_action(); }
				},
			});
			dialog.show(); dialog.set_values(values);
			const refreshAudience = () => {
				const scope = dialog.get_value("audience_scope");
				const needsProgram = ["Specific Class", "Specific Class Arm", "Specific Programme"].includes(scope);
				dialog.set_df_property("program", "hidden", !needsProgram);
				dialog.set_df_property("student_group", "hidden", scope !== "Specific Class Arm");
				if (!needsProgram) { dialog.set_value("program", ""); dialog.set_value("student_group", ""); }
				if (scope !== "Specific Class Arm") dialog.set_value("student_group", "");
			};
			dialog.fields_dict.audience_scope.df.onchange = refreshAudience;
			dialog.fields_dict.program.df.onchange = async () => {
				const program = dialog.get_value("program") || "";
				const response = await frappe.call(GET_OPTIONS_METHOD, { branch: this.branch, academic_year: this.academicYear, program: program || undefined });
				options = response.message || options;
				dialog.set_df_property("student_group", "options", armOptions(program).join("\n"));
				const current = dialog.get_value("student_group");
				if (current && !armOptions(program).includes(current)) dialog.set_value("student_group", "");
			};
			refreshAudience();
			if (name) this.addLifecycleButtons(dialog, name, values.status || "Draft");
		},
		addLifecycleButtons(dialog, name, status) {
			const transitions = {
				Draft: ["Scheduled", "Published", "Cancelled"], Scheduled: ["Published", "Cancelled", "Draft"],
				Published: ["Completed", "Cancelled"], Cancelled: ["Scheduled"], Completed: ["Archived"], Archived: [],
			};
			const actions = transitions[status] || [];
			if (!actions.length) return;
			const $row = $('<div class="school-event-lifecycle"></div>').appendTo(dialog.$wrapper.find(".modal-body"));
			$('<small></small>').text(__(`Current status: ${status}`)).appendTo($row);
			for (const next of actions) {
				const $button = $('<button type="button" class="btn btn-default btn-sm"></button>').text(__(next)).appendTo($row);
				$button.on("click", async () => {
					let reason = "";
					if (next === "Cancelled") {
						reason = await new Promise((resolve) => frappe.prompt([{ fieldname: "reason", fieldtype: "Small Text", label: __("Cancellation / Postponement Reason"), reqd: 1 }], (values) => resolve(values.reason), __("Cancel School Event"), __("Continue")));
					}
					await frappe.call({ method: SET_STATUS_METHOD, type: "POST", args: { name, status: next, reason: reason || undefined } });
					dialog.hide(); frappe.show_alert({ message: __(`School Event moved to ${next}`), indicator: "green" }); await this.load();
				});
			}
		},
	},
};
</script>

<style scoped>
.school-calendar-shell{display:grid;gap:1rem;color:var(--text-color)}.school-calendar-header{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start}.school-calendar-header h2{margin:.1rem 0 .3rem}.school-calendar-header p{margin:0;color:var(--text-muted);max-width:60rem}.school-calendar-actions,.school-calendar-view-tabs,.school-calendar-nav{display:flex;gap:.45rem;flex-wrap:wrap;align-items:center}
.school-calendar-filters{display:grid;grid-template-columns:repeat(5,minmax(0,1fr)) auto;gap:.65rem;padding:.75rem;border:1px solid var(--border-color);border-radius:10px;background:var(--control-bg)}.school-calendar-filters label{display:grid;gap:.25rem}.school-calendar-filters label>span{font-size:.8rem;font-weight:600}.school-calendar-toggle{align-content:center;grid-template-columns:auto 1fr!important;align-items:center;padding-top:1rem}
.school-calendar-toolbar{display:flex;justify-content:space-between;gap:1rem;align-items:center}.school-calendar-view-tabs .is-active{border-color:var(--primary);box-shadow:inset 0 -2px 0 var(--primary)}
.school-calendar-month{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));border-top:1px solid var(--border-color);border-left:1px solid var(--border-color)}.school-calendar-week-name{padding:.45rem;text-align:center;font-weight:700;background:var(--control-bg);border-right:1px solid var(--border-color);border-bottom:1px solid var(--border-color)}.school-calendar-day{min-height:9.5rem;padding:.45rem;border-right:1px solid var(--border-color);border-bottom:1px solid var(--border-color);background:var(--card-bg)}.school-calendar-day.is-outside{opacity:.55}.school-calendar-day.is-today{box-shadow:inset 0 0 0 2px var(--primary)}.school-calendar-day>header{display:flex;justify-content:space-between;gap:.3rem;margin-bottom:.35rem}.school-calendar-day>header small{color:var(--text-muted)}
.school-calendar-item{display:grid;width:100%;gap:.05rem;margin:.22rem 0;padding:.3rem .4rem;text-align:left;border:1px solid var(--border-color);border-radius:6px;background:var(--control-bg);color:var(--text-color)}.school-calendar-item strong{font-size:.78rem}.school-calendar-item small{font-size:.7rem;color:var(--text-muted)}.school-calendar-more{color:var(--text-muted)}
.school-calendar-week{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:.55rem}.school-calendar-week-day{display:grid;align-content:start;gap:.35rem;min-height:20rem;padding:.55rem;border:1px solid var(--border-color);border-radius:8px;background:var(--card-bg)}.school-calendar-week-day.is-today{border-color:var(--primary)}.school-calendar-week-day>header{display:grid;gap:.1rem}.school-calendar-week-day>header small,.school-calendar-empty{color:var(--text-muted)}
.school-calendar-agenda{display:grid;gap:.75rem}.school-calendar-agenda-day{display:grid;gap:.4rem}.school-calendar-agenda-day>header{display:flex;justify-content:space-between;gap:1rem;padding:.4rem 0;border-bottom:1px solid var(--border-color)}.school-calendar-agenda-day>header span{color:var(--text-muted)}.school-calendar-agenda-item{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:1rem;padding:.65rem .75rem;text-align:left;border:1px solid var(--border-color);border-radius:8px;background:var(--card-bg);color:var(--text-color)}.school-calendar-agenda-item>div{display:grid;gap:.12rem}.school-calendar-agenda-item>div:last-child{text-align:right}.school-calendar-agenda-item small{color:var(--text-muted)}
.school-calendar-message{padding:.75rem;border-radius:8px;background:var(--control-bg);color:var(--text-muted)}.school-calendar-message.is-error{color:var(--red-600,#b42318)}
:global(.school-event-lifecycle){display:flex;flex-wrap:wrap;gap:.4rem;align-items:center;margin:1rem 0 0;padding:.75rem;border-top:1px solid var(--border-color)}:global(.school-event-lifecycle small){margin-right:auto;color:var(--text-muted)}
@media(max-width:1100px){.school-calendar-filters{grid-template-columns:repeat(2,minmax(0,1fr))}.school-calendar-week{grid-template-columns:1fr}.school-calendar-month{min-width:800px}.school-calendar-shell{overflow-x:auto}.school-calendar-header,.school-calendar-toolbar{flex-direction:column;align-items:stretch}}
</style>
