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
				<strong>{{ readiness.summary.foundation_progress_percent || 0 }}% foundation ready</strong>
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
				<button
					v-if="!launch"
					type="button"
					class="edge-button edge-button--primary"
					:disabled="!targetAcademicYear || saving"
					@click="startOrResume"
				>
					{{ saving ? "Starting..." : "Start Session Launch" }}
				</button>
				<button
					v-else
					type="button"
					class="edge-button edge-button--primary"
					:disabled="saving"
					@click="startOrResume"
				>
					{{ saving ? "Resuming..." : "Resume Session Launch" }}
				</button>
				<button v-if="launch" type="button" class="edge-button" :disabled="saving" @click="saveForLater">
					Save & Continue Later
				</button>
				<button type="button" class="edge-button" @click="scrollToManualSetup">Manual Session & Term Management</button>
			</div>

			<div v-if="launch" class="session-launch-progress">
				<div class="session-launch-progress-track">
					<div class="session-launch-progress-value" :style="{ width: `${readiness.summary.foundation_progress_percent || 0}%` }"></div>
				</div>
				<div class="session-launch-progress-meta">
					<span>{{ readiness.summary.implemented_ready || 0 }} of {{ readiness.summary.implemented_steps || 0 }} foundation checks ready</span>
					<span v-if="!readiness.summary.branch_scope_complete" class="session-launch-warning">
						Your current Branch scope covers {{ readiness.summary.accessible_branch_count || 0 }} of {{ readiness.summary.institution_branch_count || 0 }} enabled Branches.
					</span>
				</div>
			</div>

			<div v-if="launch" class="session-launch-step-grid">
				<article
					v-for="(step, index) in readiness.steps"
					:key="step.key"
					:class="['session-launch-step', { 'is-current': step.key === launch.current_step_key, 'is-ready': step.ready, 'is-planned': !step.implemented }]"
				>
					<div class="session-launch-step-heading">
						<span class="session-launch-step-number">{{ index + 1 }}</span>
						<div>
							<strong>{{ step.label }}</strong>
							<small>{{ step.status }}</small>
						</div>
					</div>
					<p>{{ step.description }}</p>
					<p v-if="step.message" class="session-launch-step-message">{{ step.message }}</p>
					<div v-if="metricEntries(step).length" class="session-launch-metrics">
						<span v-for="metric in metricEntries(step)" :key="metric.key">
							<small>{{ metric.label }}</small>
							<strong>{{ metric.value }}</strong>
						</span>
					</div>
					<div class="session-launch-step-actions">
						<button
							v-if="step.key === 'session_terms' && step.implemented"
							type="button"
							class="edge-button edge-button--primary"
							:disabled="saving || step.ready"
							@click="prepareFoundation"
						>
							{{ step.ready ? "Foundation Ready" : "Prepare Session Foundation" }}
						</button>
						<button v-if="step.implemented && step.key !== 'session_terms'" type="button" class="edge-button" @click="openStep(step)">
							Review {{ step.label }}
						</button>
						<button v-if="step.implemented" type="button" class="edge-button" :disabled="saving" @click="saveCurrentStep(step.key)">
							Save here
						</button>
						<span v-else class="session-launch-planned-label">Planned next slice</span>
					</div>
				</article>
			</div>

			<div v-if="launch" class="session-launch-resume-note">
				<strong>Resume behaviour</strong>
				<span>
					Leaving this page does not reset the launch. EduEdge stores the current step, source Session, status and resume audit; readiness is recalculated from the real academic records when you return.
				</span>
				<small v-if="launch.last_resumed_by">Last resumed by {{ launch.last_resumed_by }} · {{ formatDateTime(launch.last_resumed_on) }}</small>
			</div>
		</template>
	</section>
</template>

<script>
const GET_METHOD = "eduedge.api.session_launch.get_session_launch_context";
const START_METHOD = "eduedge.api.session_launch.start_or_resume_session_launch";
const SAVE_METHOD = "eduedge.api.session_launch.save_session_launch_progress";
const PREPARE_METHOD = "eduedge.api.session_launch.prepare_session_foundation";

export default {
	name: "EduEdgeSessionLaunch",
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
		};
	},
	computed: {
		institutionName() {
			return this.context.institution_name || this.institution || "Institution";
		},
		sourceSessions() {
			const target = this.sessions.find((row) => row.name === this.targetAcademicYear);
			if (!target?.year_start_date) return [];
			const targetStart = new Date(target.year_start_date);
			return this.sessions.filter((row) => row.name !== this.targetAcademicYear && row.year_start_date && new Date(row.year_start_date) < targetStart);
		},
	},
	mounted() {
		this.load();
	},
	methods: {
		async load(academicYear = "") {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call(GET_METHOD, academicYear ? { academic_year: academicYear } : {});
				this.applyPayload(response.message || {});
			} catch (error) {
				this.error = error?.message || "Academic Session Launch could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		applyPayload(payload) {
			this.context = payload.active_context || {};
			this.institution = payload.institution || this.context.institution || "";
			this.sessions = payload.sessions || [];
			this.targetAcademicYear = payload.academic_year || this.targetAcademicYear || "";
			this.launch = payload.launch || null;
			this.readiness = payload.readiness || { steps: [], summary: {} };
			this.sourceAcademicYear = this.launch?.source_academic_year || payload.suggested_source_academic_year || "";
		},
		async targetChanged() {
			this.launch = null;
			this.readiness = { steps: [], summary: {} };
			if (!this.targetAcademicYear) return;
			await this.load(this.targetAcademicYear);
		},
		async startOrResume() {
			if (!this.targetAcademicYear) return;
			this.saving = true;
			this.error = "";
			try {
				const response = await frappe.call({
					method: START_METHOD,
					type: "POST",
					args: {
						academic_year: this.targetAcademicYear,
						institution: this.institution || undefined,
						source_academic_year: this.sourceAcademicYear || undefined,
					},
				});
				this.applyPayload(response.message || {});
				frappe.show_alert({ message: __(this.launch ? "Session Launch ready to continue" : "Session Launch started"), indicator: "green" });
			} catch (error) {
				this.error = error?.message || "Session Launch could not be started or resumed.";
			} finally {
				this.saving = false;
			}
		},
		async saveCurrentStep(stepKey) {
			if (!this.launch?.name) return;
			this.saving = true;
			this.error = "";
			try {
				const response = await frappe.call({
					method: SAVE_METHOD,
					type: "POST",
					args: {
						launch: this.launch.name,
						current_step: stepKey,
						source_academic_year: this.sourceAcademicYear || undefined,
					},
				});
				this.launch = response.message?.launch || this.launch;
				this.readiness = response.message?.readiness || this.readiness;
				frappe.show_alert({ message: __("Session Launch progress saved"), indicator: "green" });
			} catch (error) {
				this.error = error?.message || "Session Launch progress could not be saved.";
			} finally {
				this.saving = false;
			}
		},
		saveForLater() {
			return this.saveCurrentStep(this.launch?.current_step_key || "session_terms");
		},
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
			} finally {
				this.saving = false;
			}
		},
		openStep(step) {
			if (!step?.route) return;
			this.saveCurrentStep(step.key).finally(() => {
				const params = new URLSearchParams();
				if (this.targetAcademicYear) params.set("academic_year", this.targetAcademicYear);
				if (this.sourceAcademicYear) params.set("source_academic_year", this.sourceAcademicYear);
				window.location.href = `${step.route}${params.toString() ? `?${params}` : ""}`;
			});
		},
		metricEntries(step) {
			const labels = {
				terms: "Terms",
				terms_missing_dates: "Terms missing dates",
				calendar: "Institution Calendar",
				classes: "Classes",
				class_intakes: "Class Intakes",
				class_arms: "Class Arms",
				submitted: "Submitted Enrollments",
				draft: "Draft Enrollments",
				source_session: "Source Session",
			};
			return Object.entries(step?.metrics || {})
				.filter(([, value]) => value !== "" && value !== null && value !== undefined)
				.map(([key, value]) => ({ key, label: labels[key] || key.replaceAll("_", " "), value }));
		},
		formatDateTime(value) {
			return value ? frappe.datetime.str_to_user(value) : "";
		},
		scrollToManualSetup() {
			const root = document.querySelector(".eduedge-academic-sessions-root");
			root?.scrollIntoView({ behavior: "smooth", block: "start" });
		},
	},
};
</script>

<style scoped>
.session-launch-shell{display:grid;gap:1rem;margin-bottom:1rem;padding:1rem;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}
.session-launch-header{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start}.session-launch-header h2{margin:.1rem 0 .35rem}.session-launch-subtitle{max-width:58rem;margin:0;color:var(--text-muted)}
.session-launch-status-block{display:grid;gap:.25rem;min-width:14rem;text-align:right}.session-launch-status{justify-self:end;padding:.2rem .55rem;border-radius:999px;background:var(--control-bg);border:1px solid var(--border-color);font-size:.78rem}.session-launch-status-block small{color:var(--text-muted)}
.session-launch-context-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.75rem}.session-launch-context-grid label,.session-launch-context-card{display:grid;gap:.35rem}.session-launch-context-grid label>span,.session-launch-context-card>span{font-weight:600}.session-launch-context-grid small,.session-launch-context-card small{color:var(--text-muted)}.session-launch-context-card{padding:.75rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}
.session-launch-actions,.session-launch-step-actions{display:flex;flex-wrap:wrap;gap:.5rem}.session-launch-progress{display:grid;gap:.45rem}.session-launch-progress-track{height:.55rem;overflow:hidden;border-radius:999px;background:var(--control-bg);border:1px solid var(--border-color)}.session-launch-progress-value{height:100%;background:var(--primary)}.session-launch-progress-meta{display:flex;justify-content:space-between;gap:1rem;color:var(--text-muted);font-size:.8rem}.session-launch-warning{color:var(--orange-600,#b54708)}
.session-launch-step-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem}.session-launch-step{display:grid;gap:.65rem;padding:.85rem;border:1px solid var(--border-color);border-radius:10px;background:var(--control-bg)}.session-launch-step.is-current{box-shadow:inset 3px 0 0 var(--primary)}.session-launch-step.is-ready{border-style:solid}.session-launch-step.is-planned{opacity:.72}.session-launch-step-heading{display:flex;gap:.65rem;align-items:center}.session-launch-step-heading>div{display:grid;gap:.1rem}.session-launch-step-heading small{color:var(--text-muted)}.session-launch-step-number{display:grid;place-items:center;width:1.8rem;height:1.8rem;border-radius:999px;border:1px solid var(--border-color);font-weight:700}.session-launch-step p{margin:0;color:var(--text-muted)}.session-launch-step-message{font-size:.82rem}.session-launch-metrics{display:flex;flex-wrap:wrap;gap:.5rem}.session-launch-metrics>span{display:grid;gap:.1rem;min-width:7rem;padding:.45rem .55rem;border:1px solid var(--border-color);border-radius:8px;background:var(--card-bg)}.session-launch-metrics small{color:var(--text-muted)}.session-launch-planned-label{align-self:center;color:var(--text-muted);font-size:.8rem}
.session-launch-resume-note{display:grid;gap:.25rem;padding:.8rem;border:1px dashed var(--border-color);border-radius:8px}.session-launch-resume-note span,.session-launch-resume-note small{color:var(--text-muted)}.session-launch-message{padding:.75rem;border-radius:8px;background:var(--control-bg)}.session-launch-message--error{color:var(--red-600,#b42318)}
@media(max-width:1000px){.session-launch-context-grid,.session-launch-step-grid{grid-template-columns:1fr}.session-launch-header,.session-launch-progress-meta{align-items:stretch;flex-direction:column}.session-launch-status-block{text-align:left}.session-launch-status{justify-self:start}}
</style>
