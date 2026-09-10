<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="selectedBranch?.institution_name || ''"
		:branch-name="selectedBranch?.branch_name || 'Academic Readiness'"
		:menu-items="menuItems"
		active-route="/app/eduedge-academic-readiness"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Academic Intelligence"
					title="Academic Readiness"
					subtitle="See whether teaching responsibilities, Instructor identity, approved curriculum plans and delivery evidence are ready for the selected academic period."
				/>
			</template>

			<EdgeFilterBar title="Academic period">
				<div class="readiness-filters">
					<label>
						<span>Branch / Campus</span>
						<select v-model="filters.school_branch" class="form-control" @change="branchChanged">
							<option v-for="row in report.allowed_branches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option>
						</select>
					</label>
					<label>
						<span>Academic Session</span>
						<select v-model="filters.academic_year" class="form-control" @change="sessionChanged">
							<option value="">Current / Active</option>
							<option v-for="value in report.options.academic_years" :key="value" :value="value">{{ value }}</option>
						</select>
					</label>
					<label>
						<span>Term / Semester</span>
						<select v-model="filters.academic_term" class="form-control" @change="load(true)">
							<option value="">All Terms</option>
							<option v-for="value in report.options.academic_terms" :key="value" :value="value">{{ value }}</option>
						</select>
					</label>
					<label>
						<span>Attention Type</span>
						<select v-model="filters.attention_type" class="form-control" @change="load(true)">
							<option value="">All Attention</option>
							<option v-for="value in report.options.attention_types" :key="value" :value="value">{{ value }}</option>
						</select>
					</label>
					<label class="history-toggle">
						<input v-model="filters.include_historical" type="checkbox" @change="load(true)" />
						<span>Include historical periods</span>
					</label>
				</div>
				<template #actions>
					<button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="load(true)">Refresh</button>
				</template>
			</EdgeFilterBar>

			<EdgeLoadingState v-if="loading && !loaded" message="Reviewing academic readiness..." :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loaded" title="Academic Readiness could not load" :message="error" action-label="Try again" @retry="load(true)" />
			<template v-else>
				<p v-if="error" class="readiness-error">{{ error }}</p>

				<section class="summary-grid">
					<article>
						<span>Teaching Assignment Coverage</span>
						<strong>{{ report.summary.teaching_assignment_coverage }}%</strong>
						<small>{{ report.summary.assigned_teaching_contexts }} of {{ report.summary.expected_teaching_contexts }} Class / Subject contexts assigned</small>
						<div class="metric-track"><i :style="barWidth(report.summary.teaching_assignment_coverage)"></i></div>
					</article>
					<article>
						<span>Instructor Identity</span>
						<strong>{{ report.summary.identity_ready }} / {{ report.summary.instructors_in_scope }}</strong>
						<small>{{ report.summary.identity_attention }} teaching identities need attention</small>
					</article>
					<article>
						<span>Approved Scheme Coverage</span>
						<strong>{{ report.summary.scheme_approval_coverage }}%</strong>
						<small>{{ report.summary.approved_scheme_contexts }} of {{ report.summary.expected_teaching_contexts }} contexts governed by an Approved Scheme</small>
						<div class="metric-track"><i :style="barWidth(report.summary.scheme_approval_coverage)"></i></div>
					</article>
					<article>
						<span>Curriculum Delivery</span>
						<strong>{{ report.summary.average_delivery_coverage }}%</strong>
						<small>{{ report.summary.delivery_completed_contexts }} complete · {{ report.summary.delivery_deferred_contexts }} deferred · {{ report.summary.delivery_no_data_contexts }} no data</small>
						<div class="metric-track"><i :style="barWidth(report.summary.average_delivery_coverage)"></i></div>
					</article>
			</section>

			<section class="context-grid">
				<article><span>Classes / Offerings</span><strong>{{ report.summary.offerings }}</strong></article>
				<article><span>Class Arms</span><strong>{{ report.summary.class_groups }}</strong></article>
				<article><span>Students in Scope</span><strong>{{ report.summary.students }}</strong></article>
				<article><span>Unassigned Teaching Contexts</span><strong>{{ report.summary.unassigned_teaching_contexts }}</strong></article>
			</section>

			<section class="assessment-panel">
				<div>
					<p class="edge-eyebrow">Assessment planning activity</p>
					<h3>Recorded Assessment Plans</h3>
					<small>{{ report.notes.assessment_planning }}</small>
				</div>
				<div class="assessment-counts">
					<div><span>Total</span><strong>{{ report.summary.assessment_plans }}</strong></div>
					<div><span>Submitted</span><strong>{{ report.summary.submitted_assessment_plans }}</strong></div>
					<div><span>Draft</span><strong>{{ report.summary.draft_assessment_plans }}</strong></div>
				</div>
				<button type="button" class="edge-button" @click="openRoute('/app/eduedge-assessment-operations')">Open Assessments</button>
			</section>

			<EdgeActionBar :label="report.notes.readiness_score" />

			<section class="attention-panel">
				<div class="attention-heading">
					<div>
						<p class="edge-eyebrow">Management action queue</p>
						<h3>Needs Attention</h3>
						<small>{{ report.paging.total }} actionable readiness item{{ report.paging.total === 1 ? '' : 's' }} in the current filter.</small>
					</div>
					<div class="quick-actions">
						<button type="button" class="edge-button" @click="openRoute('/app/eduedge-instructor-assignments')">Instructor Assignments</button>
						<button type="button" class="edge-button" @click="openRoute('/app/eduedge-scheme-of-work')">Scheme of Work</button>
					</div>
				</div>

				<EdgeEmptyState
					v-if="!report.attention.length"
					title="No readiness attention items"
					description="No teaching assignment, Instructor identity, Scheme approval or curriculum delivery attention item matches the current filters."
				/>
				<div v-else class="attention-list">
					<article v-for="(row,index) in report.attention" :key="`${row.type}:${row.title}:${index}`" class="attention-row">
						<div class="attention-icon" :class="`severity-${row.severity}`">{{ row.severity === 'high' ? '!' : '•' }}</div>
						<div>
							<div class="attention-meta"><EdgeStatusBadge :label="row.type" :status="row.type" :tone="attentionTone(row.severity)" /><small>{{ row.severity }} priority</small></div>
							<strong>{{ row.title }}</strong>
							<p>{{ row.detail }}</p>
						</div>
						<button type="button" class="edge-button" @click="openAttention(row)">Open</button>
					</article>
				</div>

				<div class="paging">
					<button type="button" class="edge-button" :disabled="loading || report.paging.start <= 0" @click="previousPage">Previous</button>
					<span>{{ report.paging.total ? report.paging.start + 1 : 0 }}–{{ Math.min(report.paging.start + report.attention.length, report.paging.total) }} of {{ report.paging.total }}</span>
					<button type="button" class="edge-button" :disabled="loading || !report.paging.has_more" @click="nextPage">Next</button>
				</div>
			</section>
		</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const blankReport = () => ({
	filters: {},
	allowed_branches: [],
	options: { academic_years: [], academic_terms: [], attention_types: [] },
	summary: {
		offerings: 0, class_groups: 0, students: 0, expected_teaching_contexts: 0,
		assigned_teaching_contexts: 0, unassigned_teaching_contexts: 0, teaching_assignment_coverage: 0,
		instructors_in_scope: 0, identity_ready: 0, identity_attention: 0,
		approved_scheme_contexts: 0, scheme_approval_coverage: 0, average_delivery_coverage: 0,
		delivery_completed_contexts: 0, delivery_deferred_contexts: 0, delivery_no_data_contexts: 0,
		assessment_plans: 0, draft_assessment_plans: 0, submitted_assessment_plans: 0,
	},
	attention: [],
	paging: { start: 0, page_length: 50, has_more: false, total: 0 },
	notes: { assessment_planning: "", readiness_score: "" },
});

export default {
	name: "EduEdgeAcademicReadiness",
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS,
			report: blankReport(),
			filters: { school_branch: "", academic_year: "", academic_term: "", attention_type: "", include_historical: false },
			loading: true,
			loaded: false,
			error: "",
		};
	},
	computed: {
		selectedBranch() { return this.report.allowed_branches.find((row) => row.name === this.filters.school_branch) || null; },
	},
	mounted() { this.load(true); },
	methods: {
		openRoute: openEduEdgeRoute,
		barWidth(value) { return { width: `${Math.min(Math.max(Number(value || 0), 0), 100)}%` }; },
		attentionTone(severity) { return severity === "high" ? "danger" : severity === "medium" ? "warning" : "neutral"; },
		async load(reset = false) {
			if (reset) this.report.paging.start = 0;
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.academic_readiness.get_academic_readiness", {
					school_branch: this.filters.school_branch || undefined,
					academic_year: this.filters.academic_year || undefined,
					academic_term: this.filters.academic_term || undefined,
					attention_type: this.filters.attention_type || undefined,
					include_historical: this.filters.include_historical ? 1 : 0,
					start: reset ? 0 : this.report.paging.start,
					page_length: this.report.paging.page_length || 50,
				});
				this.report = response.message || blankReport();
				this.filters = {
					...this.filters,
					school_branch: this.report.filters.school_branch || this.filters.school_branch,
					academic_year: this.report.filters.academic_year || "",
					academic_term: this.report.filters.academic_term || "",
					attention_type: this.report.filters.attention_type || "",
					include_historical: Boolean(this.report.filters.include_historical),
				};
				this.loaded = true;
			} catch (error) {
				this.error = error?.message || "Academic Readiness could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		branchChanged() {
			this.filters.academic_year = "";
			this.filters.academic_term = "";
			this.filters.attention_type = "";
			this.load(true);
		},
		sessionChanged() {
			this.filters.academic_term = "";
			this.load(true);
		},
		openAttention(row) {
			const params = new URLSearchParams();
			for (const [key, value] of Object.entries(row.query || {})) {
				if (value) params.set(key, value);
			}
			const route = params.toString() ? `${row.route}?${params.toString()}` : row.route;
			openEduEdgeRoute(route);
		},
		previousPage() {
			this.report.paging.start = Math.max(0, this.report.paging.start - this.report.paging.page_length);
			this.load(false);
		},
		nextPage() {
			this.report.paging.start += this.report.paging.page_length;
			this.load(false);
		},
	},
};
</script>

<style scoped>
.readiness-filters { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:.65rem; width:100%; }.readiness-filters label { display:grid; gap:.3rem; font-weight:600; }.readiness-filters .history-toggle { display:flex; align-items:center; align-self:end; min-height:2.4rem; gap:.5rem; font-weight:500; }.summary-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.75rem; margin-top:1rem; }.summary-grid article,.context-grid article,.assessment-panel,.attention-panel { border:1px solid var(--border-color); border-radius:10px; background:var(--card-bg); }.summary-grid article { display:grid; gap:.3rem; padding:.85rem; }.summary-grid span,.context-grid span,.assessment-counts span { color:var(--text-muted); font-size:.78rem; }.summary-grid strong { font-size:1.45rem; }.summary-grid small,.assessment-panel small,.attention-heading small { color:var(--text-muted); }.metric-track { height:.4rem; overflow:hidden; border-radius:999px; background:var(--control-bg); }.metric-track i { display:block; height:100%; background:var(--primary); }.context-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.65rem; margin-top:.75rem; }.context-grid article { display:grid; gap:.2rem; padding:.7rem .8rem; }.context-grid strong { font-size:1.1rem; }.assessment-panel { display:grid; grid-template-columns:minmax(0,1.4fr) minmax(18rem,.8fr) auto; gap:1rem; align-items:center; padding:1rem; margin-top:1rem; }.assessment-panel h3,.attention-heading h3 { margin:0; }.assessment-counts { display:grid; grid-template-columns:repeat(3,1fr); gap:.5rem; }.assessment-counts div { display:grid; gap:.1rem; padding:.55rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); }.attention-panel { display:grid; gap:.85rem; padding:1rem; margin-top:1rem; }.attention-heading { display:flex; justify-content:space-between; align-items:center; gap:.75rem; flex-wrap:wrap; }.quick-actions { display:flex; gap:.5rem; flex-wrap:wrap; }.attention-list { display:grid; gap:.55rem; }.attention-row { display:grid; grid-template-columns:auto minmax(0,1fr) auto; gap:.75rem; align-items:center; padding:.75rem; border:1px solid var(--border-color); border-radius:9px; background:var(--control-bg); }.attention-row > div:nth-child(2) { display:grid; gap:.25rem; }.attention-row p { margin:0; color:var(--text-muted); }.attention-meta { display:flex; gap:.5rem; align-items:center; flex-wrap:wrap; }.attention-meta small { text-transform:capitalize; color:var(--text-muted); }.attention-icon { display:grid; place-items:center; width:2rem; height:2rem; border-radius:50%; font-weight:800; border:1px solid var(--border-color); }.attention-icon.severity-high { color:var(--red-600,#b42318); }.attention-icon.severity-medium { color:var(--orange-600,#b54708); }.paging { display:flex; justify-content:space-between; align-items:center; gap:.75rem; }.readiness-error { color:var(--red-600,#b42318); } @media (max-width:1100px) { .readiness-filters { grid-template-columns:repeat(2,minmax(0,1fr)); }.summary-grid,.context-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }.assessment-panel { grid-template-columns:1fr; } } @media (max-width:650px) { .readiness-filters,.summary-grid,.context-grid,.assessment-counts { grid-template-columns:1fr; }.attention-row { grid-template-columns:auto minmax(0,1fr); }.attention-row > button { grid-column:2; justify-self:start; } }
</style>
