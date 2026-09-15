<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="selectedBranch?.institution_name || ''"
		:branch-name="selectedBranch?.branch_name || 'Result Intelligence'"
		:menu-items="menuItems"
		active-route="/app/eduedge-result-intelligence"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="School Intelligence"
					title="Result Intelligence"
					subtitle="Use approved published results to identify class performance, subject strengths, weak areas and students needing academic review."
				/>
			</template>

			<EdgeFilterBar title="Published result scope">
				<div class="result-filters">
					<label><span>Branch / Campus</span><select v-model="filters.school_branch" class="form-control" @change="branchChanged"><option v-for="row in report.allowed_branches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option></select></label>
					<label><span>Academic Year</span><select v-model="filters.academic_year" class="form-control" @change="load"><option value="">All</option><option v-for="value in report.options.academic_years" :key="value" :value="value">{{ value }}</option></select></label>
					<label><span>Term / Semester</span><select v-model="filters.academic_term" class="form-control" @change="load"><option value="">All</option><option v-for="value in report.options.academic_terms" :key="value" :value="value">{{ value }}</option></select></label>
					<label><span>Class / Group</span><select v-model="filters.student_group" class="form-control" @change="load"><option value="">All</option><option v-for="value in report.options.student_groups" :key="value" :value="value">{{ value }}</option></select></label>
					<label><span>Result Type</span><select v-model="filters.result_mode" class="form-control" @change="load"><option value="">All</option><option v-for="value in report.options.result_modes" :key="value" :value="value">{{ value }}</option></select></label>
				</div>
				<template #actions><button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="load">Refresh</button></template>
			</EdgeFilterBar>

			<EdgeLoadingState v-if="loading && !loaded" message="Analysing published results..." :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loaded" title="Result Intelligence could not load" :message="error" action-label="Try again" @retry="load" />
			<template v-else>
				<p v-if="error" class="intelligence-error">{{ error }}</p>

				<EdgeDashboardLayout min-column-width="10rem">
					<EdgeStatCard label="Students" :value="report.summary.students" helper="Published students in scope" />
					<EdgeStatCard label="Overall Average" :value="formatPercent(report.summary.overall_average)" helper="Mean of published student averages" />
					<EdgeStatCard label="Highest" :value="formatPercent(report.summary.overall_highest)" helper="Highest published average" />
					<EdgeStatCard label="Lowest" :value="formatPercent(report.summary.overall_lowest)" helper="Lowest published average" />
					<EdgeStatCard label="Attendance Average" :value="formatPercent(report.summary.attendance_average)" helper="Published attendance average" />
					<EdgeStatCard label="Below Cohort Average" :value="report.summary.below_cohort_average" helper="Review queue, not a fail label" />
				</EdgeDashboardLayout>

				<section class="intelligence-grid">
					<article class="intel-panel">
						<div class="panel-heading"><div><p class="edge-eyebrow">Action queue</p><h3>Weakest Subjects by Published Average</h3></div><span>{{ report.subject_performance.length }} subjects</span></div>
						<EdgeEmptyState v-if="!report.weak_subjects.length" title="No published subject data" description="Publish results to populate academic intelligence." />
						<div v-else class="rank-list">
							<div v-for="(row,index) in report.weak_subjects" :key="row.course" class="rank-row">
								<span class="rank-number">{{ index + 1 }}</span>
								<div><strong>{{ row.course_name }}</strong><small>{{ row.students }} students · spread {{ formatPercent(row.spread) }}</small></div>
								<strong>{{ formatPercent(row.average) }}</strong>
							</div>
						</div>
					</article>

					<article class="intel-panel">
						<div class="panel-heading"><div><p class="edge-eyebrow">Published trend</p><h3>Cohort Average by Result Publication</h3></div></div>
						<EdgeEmptyState v-if="!report.publication_trend.length" title="No trend yet" description="More than one published period gives a stronger trend view." />
						<div v-else class="trend-list">
							<div v-for="row in report.publication_trend" :key="row.publication" class="trend-row">
								<div><strong>{{ row.label }}</strong><small>{{ row.student_group }} · {{ row.students }} students</small></div>
								<div class="trend-bar"><i :style="{ width: clampPercent(row.average) }"></i></div>
								<strong>{{ formatPercent(row.average) }}</strong>
							</div>
						</div>
					</article>
				</section>

				<section class="intel-panel">
					<div class="panel-heading">
						<div><p class="edge-eyebrow">Subject analysis</p><h3>Subject Performance</h3></div>
						<button type="button" class="edge-button" @click="openRoute('/app/eduedge-report-cards')">Open Report Cards</button>
					</div>
					<div class="table-wrap">
						<table class="intel-table">
							<thead><tr><th>Subject</th><th>Students</th><th>Average</th><th>Highest</th><th>Lowest</th><th>Spread</th></tr></thead>
							<tbody>
								<tr v-for="row in report.subject_performance" :key="row.course"><td><strong>{{ row.course_name }}</strong></td><td>{{ row.students }}</td><td>{{ formatPercent(row.average) }}</td><td>{{ formatPercent(row.highest) }}</td><td>{{ formatPercent(row.lowest) }}</td><td>{{ formatPercent(row.spread) }}</td></tr>
							</tbody>
						</table>
					</div>
				</section>

				<section class="intel-panel">
					<div class="panel-heading"><div><p class="edge-eyebrow">Student review</p><h3>Published Student Performance</h3></div><span>{{ report.student_performance.length }} records</span></div>
					<div class="table-wrap">
						<table class="intel-table">
							<thead><tr><th>Student</th><th>Class</th><th>Period</th><th>Average</th><th>Grade</th><th>Attendance</th><th>Relative View</th></tr></thead>
							<tbody>
								<tr v-for="row in report.student_performance" :key="`${row.publication}:${row.student}`" @click="openStudent(row)">
									<td><strong>{{ row.student_name }}</strong><small>{{ row.student }}</small></td><td>{{ row.student_group }}</td><td>{{ row.period_label }}</td><td>{{ formatPercent(row.average) }}</td><td>{{ row.grade || '-' }}</td><td>{{ formatPercent(row.attendance) }}</td><td><EdgeStatusBadge :label="row.comparison" :status="row.comparison" :tone="row.comparison.startsWith('Below') ? 'warning' : 'success'" /></td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>

				<section class="intel-notes"><p>{{ report.notes.source }}</p><p>{{ report.notes.pass_rate }}</p></section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const blankReport = () => ({
	filters: {},
	allowed_branches: [],
	current_branch: null,
	options: { academic_years: [], academic_terms: [], student_groups: [], result_modes: [] },
	summary: { students: 0, publications: 0, result_records: 0, overall_average: 0, overall_highest: 0, overall_lowest: 0, attendance_average: 0, below_cohort_average: 0 },
	subject_performance: [],
	student_performance: [],
	weak_subjects: [],
	grade_distribution: [],
	publication_trend: [],
	notes: { pass_rate: "", source: "" },
});

export default {
	name: "EduEdgeResultIntelligence",
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS,
			report: blankReport(),
			filters: { school_branch: "", academic_year: "", academic_term: "", student_group: "", result_mode: "" },
			loading: true,
			loaded: false,
			error: "",
		};
	},
	computed: {
		selectedBranch() { return this.report.allowed_branches.find((row) => row.name === this.filters.school_branch) || null; },
	},
	mounted() { this.load(); },
	methods: {
		openRoute: openEduEdgeRoute,
		formatPercent(value) { const number = Number(value); return Number.isFinite(number) ? `${number.toFixed(2)}%` : "-"; },
		clampPercent(value) { return `${Math.min(Math.max(Number(value || 0), 0), 100)}%`; },
		async load() {
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.result_intelligence.get_result_intelligence", {
					school_branch: this.filters.school_branch || undefined,
					academic_year: this.filters.academic_year || undefined,
					academic_term: this.filters.academic_term || undefined,
					student_group: this.filters.student_group || undefined,
					result_mode: this.filters.result_mode || undefined,
				});
				this.report = response.message || blankReport();
				this.filters = { ...this.filters, ...(this.report.filters || {}) };
				this.loaded = true;
			} catch (error) {
				this.error = error?.message || "Result Intelligence could not be loaded.";
			} finally { this.loading = false; }
		},
		branchChanged() {
			this.filters.academic_year = ""; this.filters.academic_term = ""; this.filters.student_group = ""; this.filters.result_mode = "";
			this.load();
		},
		openStudent(row) {
			const params = new URLSearchParams({ publication: row.publication, student: row.student });
			openEduEdgeRoute(`/app/eduedge-report-cards?${params.toString()}`);
		},
	},
};
</script>

<style scoped>
.result-filters{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.65rem;width:100%}.result-filters label{display:grid;gap:.3rem;font-weight:600}.intelligence-grid{display:grid;grid-template-columns:1fr 1fr;gap:.75rem;margin-top:1rem}.intel-panel{padding:1rem;margin-top:1rem;border:1px solid var(--border-color);border-radius:10px;background:var(--card-bg)}.intelligence-grid .intel-panel{margin-top:0}.panel-heading{display:flex;justify-content:space-between;align-items:center;gap:.75rem;margin-bottom:.75rem}.panel-heading h3{margin:.15rem 0 0}.panel-heading>span,.rank-row small,.trend-row small,.intel-table small,.intel-notes{color:var(--text-muted)}.rank-list,.trend-list{display:grid;gap:.55rem}.rank-row{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:.65rem;padding:.6rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.rank-row>div{display:grid}.rank-number{display:grid;place-items:center;width:1.7rem;height:1.7rem;border-radius:50%;background:var(--card-bg);font-weight:700}.trend-row{display:grid;grid-template-columns:minmax(9rem,.7fr) minmax(10rem,1.3fr) auto;align-items:center;gap:.65rem}.trend-row>div:first-child{display:grid}.trend-bar{height:.45rem;border-radius:999px;background:var(--control-bg);overflow:hidden}.trend-bar i{display:block;height:100%;background:var(--primary)}.table-wrap{overflow:auto;border:1px solid var(--border-color);border-radius:8px}.intel-table{width:100%;border-collapse:collapse;min-width:650px}.intel-table th,.intel-table td{padding:.6rem;border-bottom:1px solid var(--border-color);text-align:left}.intel-table th{background:var(--control-bg);font-size:.78rem}.intel-table tbody tr:last-child td{border-bottom:0}.intel-table tbody tr{cursor:pointer}.intel-table tbody tr:hover{background:var(--control-bg)}.intel-table td:first-child{display:grid}.intel-notes{padding:.75rem 0;font-size:.82rem}.intel-notes p{margin:.25rem 0}.intelligence-error{color:var(--red-600,#b42318)}@media(max-width:1050px){.result-filters{grid-template-columns:repeat(2,minmax(0,1fr))}.intelligence-grid{grid-template-columns:1fr}}@media(max-width:650px){.result-filters{grid-template-columns:1fr}.panel-heading{align-items:flex-start;flex-direction:column}}
</style>
