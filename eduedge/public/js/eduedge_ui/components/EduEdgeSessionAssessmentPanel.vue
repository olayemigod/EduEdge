<template>
	<section class="session-assessment-shell">
		<header class="session-assessment-header">
			<div>
				<p class="edge-eyebrow">Step 8</p>
				<h3>Assessment & CBT Readiness</h3>
				<p>Confirm term assessment planning and review any CBT sittings configured for this Session. CBT remains optional unless a sitting has been planned.</p>
			</div>
			<button type="button" class="edge-button" :disabled="loading" @click="load">{{ loading ? "Refreshing..." : "Refresh readiness" }}</button>
		</header>

		<div v-if="error" class="session-assessment-message is-error">{{ error }}</div>
		<div v-else-if="loading && !payload" class="session-assessment-message">Loading Assessment and CBT readiness...</div>
		<template v-else-if="payload">
			<div class="session-assessment-summary">
				<article>
					<small>Assessment</small>
					<strong>{{ payload.assessment.status }}</strong>
					<span>{{ payload.assessment.submitted_plans }} submitted · {{ payload.assessment.draft_plans }} draft plans</span>
				</article>
				<article>
					<small>CBT</small>
					<strong>{{ payload.cbt.status }}</strong>
					<span>{{ payload.cbt.schedules }} schedules · {{ payload.cbt.approved_templates }} approved templates</span>
				</article>
				<article>
					<small>Question Bank</small>
					<strong>{{ payload.cbt.approved_question_bank_questions }}</strong>
					<span>approved school questions in accessible Branches</span>
				</article>
			</div>

			<div class="session-assessment-note" :class="{ 'is-ready': payload.overall.ready }">
				<strong>{{ payload.overall.status }}</strong>
				<span>{{ payload.overall.message }}</span>
			</div>

			<div class="session-assessment-grid">
				<article class="session-assessment-card">
					<div class="session-assessment-card-heading">
						<div><strong>Assessment planning by Term</strong><small>Every active Class Arm should have at least one submitted Assessment Plan in each Term.</small></div>
					</div>
					<div v-if="!payload.assessment.term_rows.length" class="session-assessment-message">No Terms are configured for this Session.</div>
					<div v-for="row in payload.assessment.term_rows" :key="`assessment-${row.academic_term}`" class="session-assessment-term-row">
						<div>
							<strong>{{ row.term_name }}</strong>
							<small>{{ row.message }}</small>
						</div>
						<span :class="['session-assessment-badge', statusClass(row.status)]">{{ row.status }}</span>
						<div class="session-assessment-metrics">
							<span><small>Submitted</small><strong>{{ row.submitted_plans }}</strong></span>
							<span><small>Draft</small><strong>{{ row.draft_plans }}</strong></span>
							<span><small>Class Arms covered</small><strong>{{ row.covered_class_arms }}/{{ row.class_arms }}</strong></span>
							<span><small>Missing examiner</small><strong>{{ row.missing_examiner }}</strong></span>
						</div>
						<small v-if="row.missing_class_arm_names?.length" class="session-assessment-issues">Missing: {{ row.missing_class_arm_names.join(", ") }}</small>
					</div>
				</article>

				<article class="session-assessment-card">
					<div class="session-assessment-card-heading">
						<div><strong>CBT readiness by Term</strong><small>No planned CBT is neutral. Once a CBT Schedule exists, its governed operational requirements must be complete.</small></div>
					</div>
					<div v-for="row in payload.cbt.term_rows" :key="`cbt-${row.academic_term}`" class="session-assessment-term-row">
						<div>
							<strong>{{ row.term_name }}</strong>
							<small>{{ row.message }}</small>
						</div>
						<span :class="['session-assessment-badge', statusClass(row.status)]">{{ row.status }}</span>
						<div class="session-assessment-metrics">
							<span><small>Schedules</small><strong>{{ row.schedules }}</strong></span>
							<span><small>Ready</small><strong>{{ row.ready_schedules }}</strong></span>
							<span><small>Candidates</small><strong>{{ row.assigned_candidates }}/{{ row.expected_candidates }}</strong></span>
							<span><small>Gap</small><strong>{{ row.candidate_gap }}</strong></span>
						</div>
						<ul v-if="row.issues?.length" class="session-assessment-issues"><li v-for="issue in row.issues" :key="issue">{{ issue }}</li></ul>
					</div>
				</article>
			</div>

			<div class="session-assessment-actions">
				<button v-for="action in payload.actions" :key="action.key" type="button" class="edge-button" @click="openAction(action.route)">{{ action.label }}</button>
				<button type="button" class="edge-button edge-button--primary" @click="$emit('save-step', 'assessment_cbt')">Save Step 8 here</button>
			</div>
		</template>
	</section>
</template>

<script>
const GET_METHOD = "eduedge.api.session_launch_assessment.get_assessment_cbt_readiness";

export default {
	name: "EduEdgeSessionAssessmentPanel",
	props: {
		launchName: { type: String, required: true },
		academicYear: { type: String, default: "" },
		institution: { type: String, default: "" },
		branch: { type: String, default: "" },
	},
	emits: ["save-step", "assessment-updated"],
	data() {
		return { loading: false, error: "", payload: null };
	},
	watch: {
		launchName() { this.load(); },
		academicYear() { this.load(); },
	},
	mounted() { this.load(); },
	methods: {
		async load() {
			if (!this.launchName) return;
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call(GET_METHOD, { launch: this.launchName });
				this.payload = response.message || null;
				this.$emit("assessment-updated", this.payload?.overall || {});
			} catch (error) {
				this.error = error?.message || "Assessment and CBT readiness could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		statusClass(status) {
			if (status === "Ready") return "is-ready";
			if (status === "Not Planned") return "is-neutral";
			return "is-attention";
		},
		openAction(route) {
			const params = new URLSearchParams();
			if (this.academicYear) params.set("academic_year", this.academicYear);
			if (this.institution) params.set("institution", this.institution);
			if (this.branch) params.set("branch", this.branch);
			window.open(`${route}${params.toString() ? `?${params}` : ""}`, "_blank", "noopener,noreferrer");
		},
	},
};
</script>

<style scoped>
.session-assessment-shell{display:grid;gap:1rem;padding:1rem;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg);color:var(--text-color)}
.session-assessment-header{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start}.session-assessment-header h3{margin:.1rem 0 .3rem;color:var(--text-color)}.session-assessment-header p{margin:0;max-width:58rem;color:var(--text-muted)}
.session-assessment-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.75rem}.session-assessment-summary article{display:grid;gap:.2rem;padding:.75rem;border:1px solid var(--border-color);border-radius:9px;background:var(--control-bg)}.session-assessment-summary small,.session-assessment-summary span{color:var(--text-muted)}
.session-assessment-note{display:flex;gap:.6rem;align-items:center;padding:.7rem .8rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.session-assessment-note.is-ready{border-color:var(--green-500,#16803c)}.session-assessment-note span{color:var(--text-muted)}
.session-assessment-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.8rem}.session-assessment-card{display:grid;align-content:start;gap:.7rem;padding:.8rem;border:1px solid var(--border-color);border-radius:10px;background:var(--control-bg)}.session-assessment-card-heading>div{display:grid;gap:.15rem}.session-assessment-card-heading small{color:var(--text-muted)}
.session-assessment-term-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:.5rem;padding:.7rem;border:1px solid var(--border-color);border-radius:8px;background:var(--card-bg)}.session-assessment-term-row>div:first-child{display:grid;gap:.1rem}.session-assessment-term-row small{color:var(--text-muted)}
.session-assessment-badge{align-self:start;padding:.18rem .5rem;border-radius:999px;border:1px solid var(--border-color);font-size:.76rem}.session-assessment-badge.is-ready{color:var(--green-600,#16803c)}.session-assessment-badge.is-attention{color:var(--orange-600,#b54708)}.session-assessment-badge.is-neutral{color:var(--text-muted)}
.session-assessment-metrics{grid-column:1/-1;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.4rem}.session-assessment-metrics>span{display:grid;gap:.1rem;padding:.4rem;border:1px solid var(--border-color);border-radius:6px}.session-assessment-issues{grid-column:1/-1;margin:0;padding-left:1.1rem;color:var(--orange-600,#b54708)}small.session-assessment-issues{padding-left:0}.session-assessment-actions{display:flex;flex-wrap:wrap;gap:.5rem}.session-assessment-message{padding:.7rem;border-radius:8px;background:var(--control-bg);color:var(--text-muted)}.session-assessment-message.is-error{color:var(--red-600,#b42318)}
@media(max-width:1000px){.session-assessment-header{flex-direction:column}.session-assessment-summary,.session-assessment-grid{grid-template-columns:1fr}.session-assessment-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
