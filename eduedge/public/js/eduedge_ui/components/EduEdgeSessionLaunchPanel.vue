<template>
	<section class="session-launch-shell">
		<div class="session-launch-header">
			<div>
				<p class="edge-eyebrow">Guided Academic Setup</p>
				<h2>Academic Session Launch</h2>
				<p class="session-launch-subtitle">
					Prepare a new Academic Session in one guided flow. Progress is saved against the Institution and Session so another authorised user can resume later.
				</p>
			</div>
			<div v-if="launch" class="session-launch-status-block">
				<span class="session-launch-status">{{ launch.status }}</span>
				<strong>{{ foundationProgressPercent }}% foundation ready</strong>
				<small>Saved step: {{ launch.current_step_label }}</small>
			</div>
		</div>

		<div v-if="loading" class="session-launch-message">Loading Session Launch...</div>
		<div v-else-if="error" class="session-launch-message session-launch-message--error">{{ error }}</div>
		<template v-else>
			<div class="session-launch-context-grid">
				<label>
					<span>Target Academic Session</span>
					<select v-model="targetAcademicYear" class="form-control" @change="targetChanged">
						<option value="">Select Academic Session</option>
						<option v-for="row in sessions" :key="row.name" :value="row.name">
							{{ row.academic_year_name || row.name }} · {{ row.status }}
						</option>
					</select>
					<small>Create a new Session here if the next Session does not yet exist.</small>
				</label>
				<label>
					<span>Source Academic Session</span>
					<select v-model="sourceAcademicYear" class="form-control" :disabled="!targetAcademicYear">
						<option value="">No previous Session / Not required</option>
						<option v-for="row in sourceSessions" :key="row.name" :value="row.name">
							{{ row.academic_year_name || row.name }}
						</option>
					</select>
					<small>Used later for Class Arm rollover and returning Student Progression.</small>
				</label>
				<div class="session-launch-context-card">
					<span>Institution</span>
					<strong>{{ institutionName }}</strong>
					<small>{{ context.branch_name || "Institution-wide Session preparation" }}</small>
				</div>
			</div>

			<div class="session-launch-actions">
				<button type="button" class="edge-button" :disabled="saving" @click="newSession">New Academic Session</button>
				<button type="button" class="edge-button" :disabled="!targetAcademicYear || saving" @click="newTerm">Add Term to Selected Session</button>
				<button v-if="!launch" type="button" class="edge-button edge-button--primary" :disabled="!targetAcademicYear || saving" @click="startOrResume">
					{{ saving ? "Starting..." : "Start Session Launch" }}
				</button>
				<button v-else type="button" class="edge-button edge-button--primary" :disabled="saving" @click="startOrResume">
					{{ saving ? "Resuming..." : "Resume Session Launch" }}
				</button>
				<button v-if="launch" type="button" class="edge-button" :disabled="saving" @click="saveForLater">Save & Continue Later</button>
				<button type="button" class="edge-button" @click="openManualSetup">Manual Management</button>
			</div>

			<div v-if="launch" class="session-launch-progress">
				<div class="session-launch-progress-track">
					<div class="session-launch-progress-value" :style="{ width: `${foundationProgressPercent}%` }"></div>
				</div>
				<div class="session-launch-progress-meta">
					<span>{{ foundationReadyCount }} of 4 foundation stages ready</span>
					<span v-if="!readiness.summary.branch_scope_complete" class="session-launch-warning">
						Your current Branch scope covers {{ readiness.summary.accessible_branch_count || 0 }} of {{ readiness.summary.institution_branch_count || 0 }} enabled Branches.
					</span>
				</div>
			</div>

			<div v-if="launch" class="session-launch-step-grid">
				<article
					v-for="step in overviewSteps"
					:key="step.key"
					:class="['session-launch-step', { 'is-current': step.key === launch.current_step_key, 'is-ready': step.ready, 'is-planned': !step.implemented }]"
				>
					<div class="session-launch-step-heading">
						<span class="session-launch-step-number">{{ stepNumber(step) }}</span>
						<div><strong>{{ step.label }}</strong><small>{{ step.status }}</small></div>
					</div>
					<p>{{ step.description }}</p>
					<p v-if="step.message" class="session-launch-step-message">{{ step.message }}</p>
					<div v-if="metricEntries(step).length" class="session-launch-metrics">
						<span v-for="metric in metricEntries(step)" :key="metric.key"><small>{{ metric.label }}</small><strong>{{ metric.value }}</strong></span>
					</div>
					<div class="session-launch-step-actions">
						<button v-if="step.key === 'session_terms' && step.implemented" type="button" class="edge-button edge-button--primary" :disabled="saving || step.ready" @click="prepareFoundation">
							{{ step.ready ? "Foundation Ready" : "Prepare Session Foundation" }}
						</button>
						<button v-if="step.key === 'session_terms'" type="button" class="edge-button" :disabled="saving" @click="newTerm">Add Term</button>
						<button v-if="step.implemented && step.key !== 'session_terms'" type="button" class="edge-button" @click="openStep(step)">Review {{ step.label }} in new tab</button>
						<button v-if="step.implemented" type="button" class="edge-button" :disabled="saving" @click="saveCurrentStep(step.key)">Save here</button>
						<span v-else class="session-launch-planned-label">Planned next slice</span>
					</div>
				</article>
			</div>

			<EduEdgeSessionStructurePanel
				v-if="launch?.name"
				:launch-name="launch.name"
				:academic-year="targetAcademicYear"
				:source-academic-year="sourceAcademicYear"
				:institution="institution"
				:branch="context.branch || ''"
				@structure-updated="handleStructureUpdated"
			/>

			<EduEdgeSessionLearnersPanel
				v-if="launch?.name"
				:launch-name="launch.name"
				:academic-year="targetAcademicYear"
				:source-academic-year="sourceAcademicYear"
				:institution="institution"
				:branch="context.branch || ''"
				@save-step="saveCurrentStep"
				@learners-updated="handleLearnersUpdated"
			/>

			<div v-if="launch" class="session-launch-resume-note">
				<strong>Resume behaviour</strong>
				<span>Leaving this page does not reset the launch. EduEdge stores the current step, source Session, status and resume audit; readiness is recalculated from the real academic records when you return.</span>
				<small v-if="launch.last_resumed_by">Last resumed by {{ launch.last_resumed_by }} · {{ formatDateTime(launch.last_resumed_on) }}</small>
			</div>
		</template>
	</section>
</template>

<script>
import EduEdgeSessionStructurePanel from "./EduEdgeSessionStructurePanel.vue";
import EduEdgeSessionLearnersPanel from "./EduEdgeSessionLearnersPanel.vue";

const GET_METHOD = "eduedge.api.session_launch.get_session_launch_context";
const START_METHOD = "eduedge.api.session_launch.start_or_resume_session_launch";
const SAVE_METHOD = "eduedge.api.session_launch.save_session_launch_progress";
const PREPARE_METHOD = "eduedge.api.session_launch.prepare_session_foundation";
const SAVE_SESSION_METHOD = "eduedge.api.academic_sessions.save_academic_session";
const SAVE_TERM_METHOD = "eduedge.api.academic_sessions.save_academic_term";
const EMBEDDED_WORKFLOW_STEPS = new Set(["class_structure", "class_intakes", "class_arms", "student_progression", "admissions_enrollment"]);

export default {
	name: "EduEdgeSessionLaunchPanel",
	components: { EduEdgeSessionStructurePanel, EduEdgeSessionLearnersPanel },
	data() {
		return {
			loading: true,
			saving: false,
			error: "",
			context: {},
			institution: "",
			sessions: [],
			targetAcademicYear: "",
			sourceAcademicYear: "",
			launch: null,
			readiness: { steps: [], summary: {} },
			structureSummary: {},
			learnersSummary: {},
		};
	},
	computed: {
		institutionName() { return this.context.institution_name || this.institution || "Institution"; },
		sourceSessions() {
			const target = this.sessions.find((row) => row.name === this.targetAcademicYear);
			if (!target?.year_start_date) return [];
			const targetStart = new Date(target.year_start_date);
			return this.sessions.filter((row) => row.name !== this.targetAcademicYear && row.year_start_date && new Date(row.year_start_date) < targetStart);
		},
		overviewSteps() { return (this.readiness.steps || []).filter((step) => !EMBEDDED_WORKFLOW_STEPS.has(step.key)); },
		foundationReadyCount() {
			const sessionReady = Boolean((this.readiness.steps || []).find((step) => step.key === "session_terms")?.ready);
			return [
				sessionReady,
				Boolean(this.structureSummary.class_structure_ready),
				Boolean(this.structureSummary.intakes_ready),
				Boolean(this.structureSummary.arms_structure_ready),
			].filter(Boolean).length;
		},
		foundationProgressPercent() { return Math.round((this.foundationReadyCount / 4) * 100); },
	},
	mounted() { this.load(); },
	methods: {
		async load(academicYear = "") {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call(GET_METHOD, academicYear ? { academic_year: academicYear } : {});
				this.applyPayload(response.message || {});
			} catch (error) {
				this.error = error?.message || "Academic Session Launch could not be loaded.";
			} finally { this.loading = false; }
		},
		applyPayload(payload) {
			this.context = payload.active_context || {};
			this.institution = payload.institution || this.context.institution || "";
			this.sessions = payload.sessions || [];
			this.targetAcademicYear = payload.academic_year || this.targetAcademicYear || "";
			this.launch = payload.launch || null;
			this.readiness = payload.readiness || { steps: [], summary: {} };
			this.sourceAcademicYear = this.launch?.source_academic_year || payload.suggested_source_academic_year || "";
			if (!this.launch) { this.structureSummary = {}; this.learnersSummary = {}; }
		},
		async targetChanged() {
			this.launch = null;
			this.structureSummary = {};
			this.learnersSummary = {};
			this.readiness = { steps: [], summary: {} };
			if (!this.targetAcademicYear) return;
			await this.load(this.targetAcademicYear);
		},
		async startOrResume() {
			if (!this.targetAcademicYear) return;
			const hadLaunch = Boolean(this.launch?.name);
			this.saving = true;
			this.error = "";
			try {
				const response = await frappe.call({ method: START_METHOD, type: "POST", args: { academic_year: this.targetAcademicYear, institution: this.institution || undefined, source_academic_year: this.sourceAcademicYear || undefined } });
				this.applyPayload(response.message || {});
				frappe.show_alert({ message: __(hadLaunch ? "Session Launch ready to continue" : "Session Launch started"), indicator: "green" });
			} catch (error) {
				this.error = error?.message || "Session Launch could not be started or resumed.";
			} finally { this.saving = false; }
		},
		async saveCurrentStep(stepKey) {
			if (!this.launch?.name) return false;
			this.saving = true;
			this.error = "";
			try {
				const response = await frappe.call({ method: SAVE_METHOD, type: "POST", args: { launch: this.launch.name, current_step: stepKey, source_academic_year: this.sourceAcademicYear || undefined } });
				this.launch = response.message?.launch || this.launch;
				this.readiness = response.message?.readiness || this.readiness;
				frappe.show_alert({ message: __("Session Launch progress saved"), indicator: "green" });
				return true;
			} catch (error) {
				this.error = error?.message || "Session Launch progress could not be saved.";
				return false;
			} finally { this.saving = false; }
		},
		saveForLater() { return this.saveCurrentStep(this.launch?.current_step_key || "session_terms"); },
		async prepareFoundation() {
			if (!this.launch?.name) return;
			this.saving = true;
			this.error = "";
			try {
				const response = await frappe.call({ method: PREPARE_METHOD, type: "POST", args: { launch: this.launch.name } });
				this.launch = response.message?.launch || this.launch;
				this.readiness = response.message?.readiness || this.readiness;
				frappe.show_alert({ message: __("Session foundation prepared"), indicator: "green" });
			} catch (error) {
				this.error = error?.message || "Session foundation could not be prepared.";
			} finally { this.saving = false; }
		},
		handleStructureUpdated(summary) { this.structureSummary = summary || {}; },
		handleLearnersUpdated(summary) { this.learnersSummary = summary || {}; },
		async openStep(step) {
			if (!step?.route) return;
			const reviewTab = window.open("about:blank", "_blank");
			if (reviewTab) reviewTab.opener = null;
			const saved = await this.saveCurrentStep(step.key);
			if (!saved) { reviewTab?.close(); return; }
			const params = new URLSearchParams();
			if (this.targetAcademicYear) { params.set("academic_year", this.targetAcademicYear); params.set("destination_academic_year", this.targetAcademicYear); }
			if (this.sourceAcademicYear) params.set("source_academic_year", this.sourceAcademicYear);
			if (this.institution) params.set("institution", this.institution);
			if (this.context.branch) params.set("branch", this.context.branch);
			const url = `${step.route}${params.toString() ? `?${params}` : ""}`;
			if (reviewTab) reviewTab.location.href = url;
			else window.open(url, "_blank", "noopener,noreferrer");
		},
		newSession() {
			const dialog = new frappe.ui.Dialog({
				title: __("New Academic Session"),
				fields: [
					{ fieldname: "guidance", fieldtype: "HTML", options: `<div class="session-launch-dialog-guidance">${frappe.utils.escape_html(__("Create the Session here, then add its Terms before preparing the Institution Calendar."))}</div>` },
					{ fieldname: "academic_year_name", fieldtype: "Data", label: __("Academic Session"), reqd: 1 },
					{ fieldtype: "Section Break", label: __("Session Dates") },
					{ fieldname: "start_date", fieldtype: "Date", label: __("Start Date"), reqd: 1 },
					{ fieldtype: "Column Break" },
					{ fieldname: "end_date", fieldtype: "Date", label: __("End Date"), reqd: 1 },
				],
				primary_action_label: __("Create Academic Session"),
				primary_action: async (values) => {
					dialog.disable_primary_action();
					try {
						const response = await frappe.call({ method: SAVE_SESSION_METHOD, type: "POST", args: values });
						const name = response.message?.name || values.academic_year_name;
						dialog.hide();
						frappe.show_alert({ message: __("Academic Session created"), indicator: "green" });
						await this.load(name);
						this.newTerm();
					} catch (error) {
						frappe.msgprint({ title: __("Academic Session could not be created"), message: error?.message || __("Review the Session details and try again."), indicator: "red" });
					} finally { dialog.enable_primary_action(); }
				},
			});
			dialog.$wrapper?.addClass("session-launch-dialog");
			dialog.show();
		},
		newTerm() {
			if (!this.targetAcademicYear) {
				frappe.msgprint({ title: __("Select an Academic Session"), message: __("Select or create the target Academic Session before adding a Term."), indicator: "orange" });
				return;
			}
			const dialog = new frappe.ui.Dialog({
				title: __("New Academic Term"),
				fields: [
					{ fieldname: "guidance", fieldtype: "HTML", options: `<div class="session-launch-dialog-guidance">${frappe.utils.escape_html(__("Term dates must stay inside the selected Session and must not overlap another Term."))}</div>` },
					{ fieldname: "academic_year", fieldtype: "Link", label: __("Academic Session"), options: "Academic Year", reqd: 1, read_only: true, default: this.targetAcademicYear },
					{ fieldname: "term_name", fieldtype: "Data", label: __("Term"), reqd: 1 },
					{ fieldtype: "Section Break", label: __("Term Dates") },
					{ fieldname: "start_date", fieldtype: "Date", label: __("Start Date"), reqd: 1 },
					{ fieldtype: "Column Break" },
					{ fieldname: "end_date", fieldtype: "Date", label: __("End Date"), reqd: 1 },
				],
				primary_action_label: __("Add Term"),
				primary_action: async (values) => {
					dialog.disable_primary_action();
					try {
						await frappe.call({ method: SAVE_TERM_METHOD, type: "POST", args: values });
						dialog.hide();
						frappe.show_alert({ message: __("Academic Term created"), indicator: "green" });
						await this.load(this.targetAcademicYear);
					} catch (error) {
						frappe.msgprint({ title: __("Academic Term could not be created"), message: error?.message || __("Review the Term details and try again."), indicator: "red" });
					} finally { dialog.enable_primary_action(); }
				},
			});
			dialog.$wrapper?.addClass("session-launch-dialog");
			dialog.show();
		},
		stepNumber(step) { return Math.max((this.readiness.steps || []).findIndex((row) => row.key === step.key) + 1, 1); },
		metricEntries(step) {
			const labels = { terms: "Terms", terms_missing_dates: "Terms missing dates", calendar: "Institution Calendar", classes: "Classes", class_intakes: "Class Intakes", class_arms: "Class Arms", submitted: "Submitted Enrollments", draft: "Draft Enrollments", source_session: "Source Session" };
			return Object.entries(step?.metrics || {}).filter(([, value]) => value !== "" && value !== null && value !== undefined).map(([key, value]) => ({ key, label: labels[key] || key.replaceAll("_", " "), value }));
		},
		formatDateTime(value) { return value ? frappe.datetime.str_to_user(value) : ""; },
		openManualSetup() { window.dispatchEvent(new CustomEvent("eduedge:academic-session-tab", { detail: { mode: "manual" } })); },
	},
};
</script>

<style scoped>
.session-launch-shell{display:grid;gap:1rem;margin-bottom:1rem;padding:1rem;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg);color:var(--text-color)}
.session-launch-shell h1,.session-launch-shell h2,.session-launch-shell h3,.session-launch-shell h4,.session-launch-shell strong{color:var(--text-color)}
.session-launch-header{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start}.session-launch-header h2{margin:.1rem 0 .35rem}.session-launch-subtitle{max-width:58rem;margin:0;color:var(--text-muted)}
.session-launch-status-block{display:grid;gap:.25rem;min-width:14rem;text-align:right}.session-launch-status{justify-self:end;padding:.2rem .55rem;border-radius:999px;background:var(--control-bg);border:1px solid var(--border-color);font-size:.78rem}.session-launch-status-block small{color:var(--text-muted)}
.session-launch-context-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.75rem}.session-launch-context-grid label,.session-launch-context-card{display:grid;gap:.35rem}.session-launch-context-grid label>span,.session-launch-context-card>span{font-weight:600}.session-launch-context-grid small,.session-launch-context-card small{color:var(--text-muted)}.session-launch-context-card{padding:.75rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}
.session-launch-actions,.session-launch-step-actions{display:flex;flex-wrap:wrap;gap:.5rem}.session-launch-progress{display:grid;gap:.45rem}.session-launch-progress-track{height:.55rem;overflow:hidden;border-radius:999px;background:var(--control-bg);border:1px solid var(--border-color)}.session-launch-progress-value{height:100%;background:var(--primary)}.session-launch-progress-meta{display:flex;justify-content:space-between;gap:1rem;color:var(--text-muted);font-size:.8rem}.session-launch-warning{color:var(--orange-600,#b54708)}
.session-launch-step-grid{display:grid;grid-template-columns:minmax(0,1fr);gap:.75rem}.session-launch-step{display:grid;gap:.65rem;padding:.95rem;border:1px solid var(--border-color);border-radius:10px;background:var(--control-bg)}.session-launch-step.is-current{box-shadow:inset 3px 0 0 var(--primary)}.session-launch-step.is-ready{border-style:solid}.session-launch-step.is-planned{opacity:.72}.session-launch-step-heading{display:flex;gap:.65rem;align-items:center}.session-launch-step-heading>div{display:grid;gap:.1rem}.session-launch-step-heading small{color:var(--text-muted)}.session-launch-step-number{display:grid;place-items:center;width:1.8rem;height:1.8rem;border-radius:999px;border:1px solid var(--border-color);font-weight:700}.session-launch-step p{margin:0;color:var(--text-muted)}.session-launch-step-message{font-size:.82rem}.session-launch-metrics{display:flex;flex-wrap:wrap;gap:.5rem}.session-launch-metrics>span{display:grid;gap:.1rem;min-width:8rem;padding:.45rem .55rem;border:1px solid var(--border-color);border-radius:8px;background:var(--card-bg)}.session-launch-metrics small{color:var(--text-muted)}.session-launch-planned-label{align-self:center;color:var(--text-muted);font-size:.8rem}
.session-launch-resume-note{display:grid;gap:.25rem;padding:.8rem;border:1px dashed var(--border-color);border-radius:8px}.session-launch-resume-note span,.session-launch-resume-note small{color:var(--text-muted)}.session-launch-message{padding:.75rem;border-radius:8px;background:var(--control-bg)}.session-launch-message--error{color:var(--red-600,#b42318)}
:global(.session-launch-dialog .modal-content){border-radius:12px}:global(.session-launch-dialog-guidance){padding:.75rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg);color:var(--text-muted)}
@media(max-width:1000px){.session-launch-context-grid{grid-template-columns:1fr}.session-launch-header,.session-launch-progress-meta{align-items:stretch;flex-direction:column}.session-launch-status-block{text-align:left}.session-launch-status{justify-self:start}}
</style>
