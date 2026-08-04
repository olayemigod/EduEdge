<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="activeContext.institution_name || ''"
		:branch-name="activeContext.branch_name || `${sessionPlural} & ${termPlural}`"
		:menu-items="menuItems"
		active-route="/app/eduedge-academic-sessions"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Academic Setup"
					:title="`${sessionPlural} and ${termPlural}`"
					:subtitle="`Create the native ${sessionSingular} and its ${termPlural.toLowerCase()} before mapping them into an Institution calendar. EduEdge keeps Frappe Education as the system of record.`"
					:action-label="canCreateSession ? `New ${sessionSingular}` : ''"
					@action="newSession"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loadedOnce" :message="`Loading ${sessionPlural.toLowerCase()}...`" :skeleton="true" />
			<EdgeErrorState
				v-else-if="error && !loadedOnce"
				:title="`${sessionPlural} could not load`"
				:message="error"
				action-label="Try again"
				@retry="load"
			/>
			<template v-else>
				<EdgeFilterBar :title="`${sessionSingular} context`">
					<div class="eduedge-session-filter-grid">
						<label>
							<span>{{ sessionSingular }}</span>
							<select v-model="filters.academic_year" class="form-control" @change="sessionChanged">
								<option value="">Select {{ sessionSingular }}</option>
								<option v-for="row in data.sessions" :key="row.name" :value="row.name">
									{{ row.academic_year_name || row.name }} · {{ formatDate(row.year_start_date) }} – {{ formatDate(row.year_end_date) }}
								</option>
							</select>
						</label>
						<label>
							<span>Search {{ sessionPlural }}</span>
							<input v-model.trim="filters.search" class="form-control" :placeholder="`Search ${sessionPlural.toLowerCase()}`" @keyup.enter="applySearch" />
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" @click="goToFoundation">Academic Foundation</button>
						<button type="button" class="edge-button" @click="clearSearch">Clear</button>
						<button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="applySearch">{{ loading ? "Loading..." : "Apply" }}</button>
					</template>
				</EdgeFilterBar>

				<EdgeDashboardLayout min-column-width="12rem">
					<EdgeStatCard :label="sessionPlural" :value="data.summary.session_count" helper="Native Frappe Education masters" />
					<EdgeStatCard :label="`${termPlural} in selected ${sessionSingular}`" :value="data.summary.selected_term_count" helper="Used by calendar periods" />
					<EdgeStatCard label="Linked Institution Calendars" :value="data.summary.linked_calendar_count" helper="Calendars using the selected session" />
					<EdgeStatCard label="Current Session" :value="data.summary.current_session || 'Not configured'" :tone="data.summary.current_session ? 'success' : 'warning'" helper="Based on today's date" />
				</EdgeDashboardLayout>

				<p v-if="error && loadedOnce" class="eduedge-session-error">{{ error }}</p>
				<div class="eduedge-session-layout">
					<section class="eduedge-session-panel">
						<div class="eduedge-session-panel-heading">
							<div><p class="edge-eyebrow">Step 1</p><h2>{{ sessionPlural }}</h2></div>
							<div class="eduedge-session-actions">
								<button type="button" class="edge-button" @click="openNativeSessionList">Native list</button>
								<button v-if="canCreateSession" type="button" class="edge-button edge-button--primary" @click="newSession">New {{ sessionSingular }}</button>
							</div>
						</div>
						<EdgeLoadingState v-if="loading" :message="`Refreshing ${sessionPlural.toLowerCase()}...`" />
						<EdgeEmptyState v-else-if="!data.sessions.length" :title="`No ${sessionPlural.toLowerCase()} found`" :description="`Create the first ${sessionSingular}, then add its ${termPlural.toLowerCase()}.`" />
						<div v-else class="eduedge-session-list">
							<article
								v-for="row in data.sessions"
								:key="row.name"
								:class="['eduedge-session-row', { 'is-selected': row.name === filters.academic_year }]"
							>
								<button type="button" class="eduedge-session-main" @click="selectSession(row.name)">
									<span><strong>{{ row.academic_year_name || row.name }}</strong><small>{{ formatDate(row.year_start_date) }} – {{ formatDate(row.year_end_date) }}</small></span>
									<span class="eduedge-session-badges">
										<EdgeStatusBadge :label="row.status" :status="row.status.toLowerCase()" :tone="row.status === 'Current' ? 'success' : row.status === 'Upcoming' ? 'neutral' : 'warning'" />
										<EdgeStatusBadge :label="`${row.term_count} ${termPlural.toLowerCase()}`" status="terms" tone="neutral" />
										<EdgeStatusBadge :label="`${row.calendar_count} calendar(s)`" status="calendars" :tone="row.calendar_count ? 'success' : 'neutral'" />
									</span>
								</button>
								<div class="eduedge-session-actions">
									<button v-if="canWriteSession" type="button" class="edge-button" @click="editSession(row)">Edit</button>
									<button type="button" class="edge-button" @click="openSessionForm(row.name)">Advanced</button>
								</div>
							</article>
						</div>
					</section>

					<section class="eduedge-session-panel">
						<div class="eduedge-session-panel-heading">
							<div><p class="edge-eyebrow">Step 2</p><h2>{{ selectedSessionTitle }}</h2><small>{{ selectedSessionRange }}</small></div>
							<div class="eduedge-session-actions">
								<button type="button" class="edge-button" @click="openNativeTermList">Native list</button>
								<button v-if="canCreateTerm" type="button" class="edge-button edge-button--primary" :disabled="!selectedSession" @click="newTerm">New {{ termSingular }}</button>
							</div>
						</div>
						<EdgeEmptyState v-if="!selectedSession" :title="`Select a ${sessionSingular}`" :description="`Choose a ${sessionSingular.toLowerCase()} to configure its ${termPlural.toLowerCase()}.`" />
						<EdgeEmptyState v-else-if="!data.terms.length" :title="`No ${termPlural.toLowerCase()}`" :description="`Add the first ${termSingular.toLowerCase()} for ${selectedSessionTitle}.`" />
						<div v-else class="eduedge-term-list">
							<article v-for="(row, index) in data.terms" :key="row.name" class="eduedge-term-row">
								<span class="eduedge-term-sequence">{{ index + 1 }}</span>
								<button type="button" class="eduedge-term-main" @click="editTerm(row)">
									<strong>{{ row.term_name || row.name }}</strong>
									<small>{{ formatDate(row.term_start_date) }} – {{ formatDate(row.term_end_date) }}</small>
								</button>
								<div class="eduedge-session-actions">
									<button v-if="canWriteTerm" type="button" class="edge-button" @click="editTerm(row)">Edit</button>
									<button type="button" class="edge-button" @click="openTermForm(row.name)">Advanced</button>
								</div>
							</article>
						</div>

						<div class="eduedge-calendar-handoff">
							<div><p class="edge-eyebrow">Step 3</p><strong>Create the Institution Calendar</strong><small>The Institution Calendar maps this shared Session and its Terms to the selected Institution.</small></div>
							<button type="button" class="edge-button edge-button--primary" :disabled="!selectedSession || !data.terms.length" @click="goToFoundation">Open Academic Foundation</button>
						</div>
					</section>
				</div>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const GET_METHOD = "eduedge.api.academic_sessions.get_academic_sessions_page";
const SAVE_SESSION_METHOD = "eduedge.api.academic_sessions.save_academic_session";
const SAVE_TERM_METHOD = "eduedge.api.academic_sessions.save_academic_term";

export default {
	name: "EduEdgeAcademicSessions",
	data() {
		return {
			loading: true,
			loadedOnce: false,
			error: "",
			menuItems: EDUEDGE_MENU_ITEMS,
			filters: { academic_year: "", search: "" },
			data: {
				active_context: {},
				sessions: [],
				selected_session: null,
				terms: [],
				summary: { session_count: 0, selected_term_count: 0, linked_calendar_count: 0, current_session: "" },
				permissions: { can_create_session: false, can_write_session: false, can_create_term: false, can_write_term: false },
			},
		};
	},
	computed: {
		activeContext() { return this.data.active_context || frappe.boot?.eduedge_institution_context || {}; },
		sessionSingular() { return this.term("academic_year", false, "Academic Session"); },
		sessionPlural() { return this.term("academic_year", true, "Academic Sessions"); },
		termSingular() { return this.term("academic_term", false, "Academic Term"); },
		termPlural() { return this.term("academic_term", true, "Academic Terms"); },
		selectedSession() { return this.data.selected_session || null; },
		selectedSessionTitle() { return this.selectedSession?.academic_year_name || this.selectedSession?.name || `Selected ${this.sessionSingular}`; },
		selectedSessionRange() {
			if (!this.selectedSession) return "";
			return `${this.formatDate(this.selectedSession.year_start_date)} – ${this.formatDate(this.selectedSession.year_end_date)}`;
		},
		canCreateSession() { return Boolean(this.data.permissions.can_create_session); },
		canWriteSession() { return Boolean(this.data.permissions.can_write_session); },
		canCreateTerm() { return Boolean(this.data.permissions.can_create_term); },
		canWriteTerm() { return Boolean(this.data.permissions.can_write_term); },
	},
	mounted() { this.load(); },
	methods: {
		openRoute: openEduEdgeRoute,
		term(key, plural = false, fallback = "") { return frappe.eduedge?.term?.(key, { plural, context: this.activeContext, fallback }) || fallback; },
		formatDate(value) { return value ? frappe.datetime.str_to_user(value) : "Not set"; },
		async load() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call(GET_METHOD, { ...this.filters });
				this.data = response.message || this.data;
				this.filters = { ...this.filters, ...(this.data.filters || {}) };
				this.loadedOnce = true;
			} catch (error) {
				this.error = error?.message || `${this.sessionPlural} could not be loaded.`;
			} finally {
				this.loading = false;
			}
		},
		applySearch() { this.filters.academic_year = ""; this.load(); },
		clearSearch() { this.filters.search = ""; this.filters.academic_year = ""; this.load(); },
		sessionChanged() { this.load(); },
		selectSession(name) { if (name !== this.filters.academic_year) { this.filters.academic_year = name; this.load(); } },
		goToFoundation() { this.openRoute("/app/eduedge-academic-foundation"); },
		openNativeSessionList() { window.open("/app/academic-year", "_blank", "noopener,noreferrer"); },
		openNativeTermList() { window.open("/app/academic-term", "_blank", "noopener,noreferrer"); },
		openSessionForm(name) { frappe.set_route("Form", "Academic Year", name); },
		openTermForm(name) { frappe.set_route("Form", "Academic Term", name); },
		newSession() { if (this.canCreateSession) this.openSessionDialog(); },
		editSession(row) { if (this.canWriteSession) this.openSessionDialog(row); },
		newTerm() { if (this.canCreateTerm && this.selectedSession) this.openTermDialog(); },
		editTerm(row) { if (this.canWriteTerm) this.openTermDialog(row); },
		openSessionDialog(row = null) {
			const isNew = !row?.name;
			const dialog = new frappe.ui.Dialog({
				title: isNew ? __(`New ${this.sessionSingular}`) : __(`Edit ${this.sessionSingular}`),
				fields: [
					{ fieldname: "guidance", fieldtype: "HTML", options: `<div class="eduedge-session-dialog-guidance">${frappe.utils.escape_html(__("The Session name becomes its system identity. Quick edit locks that identity after creation while dates remain editable."))}</div>` },
					{ fieldname: "academic_year_name", fieldtype: "Data", label: this.sessionSingular, reqd: 1, read_only: !isNew, default: row?.academic_year_name || row?.name || "" },
					{ fieldtype: "Section Break", label: __("Session Dates") },
					{ fieldname: "start_date", fieldtype: "Date", label: __("Start Date"), reqd: 1, default: row?.year_start_date || "" },
					{ fieldtype: "Column Break" },
					{ fieldname: "end_date", fieldtype: "Date", label: __("End Date"), reqd: 1, default: row?.year_end_date || "" },
				],
				primary_action_label: __(`Save ${this.sessionSingular}`),
				primary_action: async (values) => {
					dialog.disable_primary_action();
					try {
						const response = await frappe.call({ method: SAVE_SESSION_METHOD, type: "POST", args: { session: row?.name || undefined, ...values } });
						dialog.hide();
						this.filters.academic_year = response.message?.name || row?.name || "";
						frappe.show_alert({ message: __(`${this.sessionSingular} saved`), indicator: "green" });
						await this.load();
					} catch (error) {
						frappe.msgprint({ title: __(`${this.sessionSingular} could not be saved`), message: error?.message || __("Please review the Session details."), indicator: "red" });
					} finally {
						dialog.enable_primary_action();
					}
				},
			});
			dialog.$wrapper?.addClass("eduedge-session-dialog");
			dialog.show();
		},
		openTermDialog(row = null) {
			const isNew = !row?.name;
			const session = row?.academic_year || this.selectedSession?.name || "";
			const dialog = new frappe.ui.Dialog({
				title: isNew ? __(`New ${this.termSingular}`) : __(`Edit ${this.termSingular}`),
				fields: [
					{ fieldname: "guidance", fieldtype: "HTML", options: `<div class="eduedge-session-dialog-guidance">${frappe.utils.escape_html(__("Term dates must remain inside the selected Session and must not overlap another Term."))}</div>` },
					{ fieldname: "academic_year", fieldtype: "Link", label: this.sessionSingular, options: "Academic Year", reqd: 1, read_only: true, default: session },
					{ fieldname: "term_name", fieldtype: "Data", label: this.termSingular, reqd: 1, read_only: !isNew, default: row?.term_name || "" },
					{ fieldtype: "Section Break", label: __("Term Dates") },
					{ fieldname: "start_date", fieldtype: "Date", label: __("Start Date"), reqd: 1, default: row?.term_start_date || "" },
					{ fieldtype: "Column Break" },
					{ fieldname: "end_date", fieldtype: "Date", label: __("End Date"), reqd: 1, default: row?.term_end_date || "" },
				],
				primary_action_label: __(`Save ${this.termSingular}`),
				primary_action: async (values) => {
					dialog.disable_primary_action();
					try {
						await frappe.call({ method: SAVE_TERM_METHOD, type: "POST", args: { term: row?.name || undefined, ...values } });
						dialog.hide();
						frappe.show_alert({ message: __(`${this.termSingular} saved`), indicator: "green" });
						await this.load();
					} catch (error) {
						frappe.msgprint({ title: __(`${this.termSingular} could not be saved`), message: error?.message || __("Please review the Term details."), indicator: "red" });
					} finally {
						dialog.enable_primary_action();
					}
				},
			});
			dialog.$wrapper?.addClass("eduedge-session-dialog");
			dialog.show();
		},
	},
};
</script>

<style scoped>
.eduedge-session-filter-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1rem; width:100%; }
.eduedge-session-filter-grid label { display:grid; gap:.35rem; font-weight:600; }
.eduedge-session-layout { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:1rem; margin-top:1rem; }
.eduedge-session-panel { display:grid; align-content:start; gap:1rem; padding:1rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.eduedge-session-panel-heading,.eduedge-session-row,.eduedge-term-row,.eduedge-calendar-handoff { display:flex; align-items:center; justify-content:space-between; gap:.75rem; }
.eduedge-session-panel-heading h2 { margin:0; }
.eduedge-session-panel-heading small,.eduedge-session-row small,.eduedge-term-row small,.eduedge-calendar-handoff small { color:var(--text-muted); }
.eduedge-session-actions,.eduedge-session-badges { display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; }
.eduedge-session-list,.eduedge-term-list { display:grid; gap:.65rem; }
.eduedge-session-row,.eduedge-term-row { padding:.75rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.eduedge-session-row.is-selected { border-color:var(--primary); box-shadow:0 0 0 1px var(--primary); }
.eduedge-session-main,.eduedge-term-main { display:flex; flex:1; align-items:center; justify-content:space-between; gap:.75rem; padding:0; border:0; background:transparent; text-align:left; }
.eduedge-session-main>span:first-child,.eduedge-term-main { display:grid; gap:.15rem; }
.eduedge-term-sequence { display:grid; place-items:center; width:2rem; height:2rem; border-radius:999px; background:var(--card-bg); font-weight:700; }
.eduedge-calendar-handoff { align-items:flex-start; margin-top:.5rem; padding:1rem; border:1px dashed var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.eduedge-calendar-handoff>div { display:grid; gap:.2rem; }
.eduedge-session-error { color:var(--red-600,#b42318); }
:global(.eduedge-session-dialog .modal-content) { border-radius:var(--edge-radius-lg,12px); }
:global(.eduedge-session-dialog-guidance) { padding:.75rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); color:var(--text-muted); }
@media (max-width:900px) { .eduedge-session-layout,.eduedge-session-filter-grid { grid-template-columns:1fr; } }
@media (max-width:650px) { .eduedge-session-panel-heading,.eduedge-session-row,.eduedge-term-row,.eduedge-calendar-handoff,.eduedge-session-main { align-items:stretch; flex-direction:column; } .eduedge-session-actions { justify-content:flex-start; } }
</style>
