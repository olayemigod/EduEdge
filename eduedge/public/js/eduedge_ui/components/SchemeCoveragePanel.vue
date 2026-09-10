<template>
	<section class="coverage-panel">
		<div class="coverage-heading">
			<div>
				<p class="edge-eyebrow">Curriculum intelligence</p>
				<h3>Coverage & Attention</h3>
				<small>See where a Scheme is missing, still Draft, not yet taught, deferred, in progress, or complete.</small>
			</div>
			<button type="button" class="edge-button" :disabled="loading" @click="load(true)">Refresh Coverage</button>
		</div>

		<div class="coverage-filters">
			<label>
				<span>Academic Session</span>
				<select v-model="filters.academic_year" class="form-control" @change="sessionChanged">
					<option value="">All Sessions</option>
					<option v-for="value in yearOptions" :key="value" :value="value">{{ value }}</option>
				</select>
			</label>
			<label>
				<span>Term / Semester</span>
				<select v-model="filters.academic_term" class="form-control" @change="load(true)">
					<option value="">All Terms</option>
					<option v-for="value in termOptions" :key="value" :value="value">{{ value }}</option>
				</select>
			</label>
			<label v-if="isManager">
				<span>Instructor</span>
				<select v-model="filters.instructor" class="form-control" @change="load(true)">
					<option value="">All Instructors</option>
					<option v-for="row in instructorOptions" :key="row.value" :value="row.value">{{ row.label }}</option>
				</select>
			</label>
			<label>
				<span>Coverage Status</span>
				<select v-model="filters.coverage_status" class="form-control" @change="load(true)">
					<option value="">All Statuses</option>
					<option v-for="value in statusOptions" :key="value" :value="value">{{ value }}</option>
				</select>
			</label>
			<label class="history-toggle">
				<input v-model="filters.include_historical" type="checkbox" @change="load(true)" />
				<span>Include historical academic periods</span>
			</label>
		</div>

		<EdgeLoadingState v-if="loading && !loaded" message="Loading curriculum coverage..." />
		<EdgeErrorState v-else-if="error && !loaded" title="Curriculum coverage could not load" :message="error" action-label="Try again" @retry="load(true)" />
		<template v-else>
			<p v-if="error" class="coverage-error">{{ error }}</p>
			<div class="coverage-summary">
				<button type="button" @click="applyStatus('')"><span>Contexts</span><strong>{{ report.summary.contexts }}</strong></button>
				<button type="button" @click="showAttention"><span>Needs Attention</span><strong>{{ report.summary.attention }}</strong></button>
				<button type="button" @click="applyStatus('Missing Scheme')"><span>Missing Schemes</span><strong>{{ report.summary.missing_schemes }}</strong></button>
				<button type="button" @click="applyStatus('In Progress')"><span>In Progress</span><strong>{{ report.summary.in_progress || 0 }}</strong></button>
				<button type="button" @click="applyStatus('Completed')"><span>Completed</span><strong>{{ report.summary.completed }}</strong></button>
				<button type="button" @click="applyStatus('Deferred')"><span>Deferred</span><strong>{{ report.summary.deferred || 0 }}</strong></button>
				<div><span>Average Coverage</span><strong>{{ report.summary.average_coverage }}%</strong></div>
			</div>

			<EdgeActionBar
				v-if="attentionOnly"
				label="Attention view shows missing Schemes, Draft Schemes, approved Schemes with no delivery data, and deferred delivery."
			/>
			<EdgeEmptyState
				v-if="!visibleRows.length"
				title="No curriculum coverage rows"
				description="No expected Subject context matches the current Branch, academic period, assignment and coverage filters."
			/>
			<div v-else class="coverage-table-wrap">
				<table class="coverage-table">
					<thead>
						<tr>
							<th>Class / Subject</th>
							<th>Academic Period</th>
							<th>Status</th>
							<th>Topics</th>
							<th>Periods</th>
							<th>Coverage</th>
							<th>Instructor</th>
							<th></th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="row in visibleRows" :key="rowKey(row)">
							<td>
								<strong>{{ row.offering_label }}</strong>
								<small>{{ row.course_label }}{{ row.student_group && row.student_group_label !== 'Class-wide' ? ` · ${row.student_group_label}` : '' }}</small>
							</td>
							<td><strong>{{ row.academic_year || '—' }}</strong><small>{{ row.academic_term || 'No Term' }}</small></td>
							<td><EdgeStatusBadge :label="row.coverage_status" :status="row.coverage_status" :tone="coverageTone(row.coverage_status)" /><small v-if="row.scheme">{{ row.scheme_status }} · V{{ row.version_no }}</small></td>
							<td><strong>{{ row.completed_topics }} / {{ row.planned_topics }}</strong><small v-if="row.deferred_topics">{{ row.deferred_topics }} deferred</small></td>
							<td><strong>{{ formatNumber(row.delivered_periods) }} / {{ row.estimated_periods }}</strong><small>{{ row.delivery_log_count }} update{{ row.delivery_log_count === 1 ? '' : 's' }}</small></td>
							<td class="coverage-cell"><strong>{{ row.coverage_percent }}%</strong><span class="row-track"><i :style="{ width: `${Math.min(Math.max(row.coverage_percent || 0, 0), 100)}%` }"></i></span></td>
							<td><small>{{ row.delivery_instructor_labels?.length ? row.delivery_instructor_labels.join(', ') : 'No delivery recorded' }}</small></td>
							<td><button type="button" class="edge-button" @click="openRow(row)">{{ row.scheme ? 'Open Scheme' : 'Open Context' }}</button></td>
						</tr>
					</tbody>
				</table>
			</div>
			<div class="coverage-paging">
				<button type="button" class="edge-button" :disabled="loading || report.paging.start <= 0" @click="previousPage">Previous</button>
				<span>{{ report.paging.total ? report.paging.start + 1 : 0 }}–{{ Math.min(report.paging.start + report.rows.length, report.paging.total) }} of {{ report.paging.total }}</span>
				<button type="button" class="edge-button" :disabled="loading || !report.paging.has_more" @click="nextPage">Next</button>
			</div>
		</template>
	</section>
</template>

<script>
const blankReport = () => ({
	filters: {},
	summary: { contexts: 0, attention: 0, missing_schemes: 0, completed: 0, in_progress: 0, deferred: 0, average_coverage: 0 },
	rows: [],
	paging: { start: 0, page_length: 50, has_more: false, total: 0 },
	options: { academic_years: [], academic_terms: [], instructors: [], coverage_statuses: [] },
});

export default {
	name: "SchemeCoveragePanel",
	props: {
		branch: { type: String, default: "" },
		programOffering: { type: String, default: "" },
		studentGroup: { type: String, default: "" },
		course: { type: String, default: "" },
		isManager: { type: Boolean, default: false },
	},
	emits: ["open-scheme", "open-context"],
	data() {
		return {
			report: blankReport(),
			filters: { academic_year: "", academic_term: "", instructor: "", coverage_status: "", include_historical: false },
			yearOptions: [], termOptions: [], instructorOptions: [], statusOptions: [],
			attentionOnly: false, loading: false, loaded: false, error: "",
		};
	},
	computed: {
		visibleRows() { return this.attentionOnly ? this.report.rows.filter((row) => row.needs_attention) : this.report.rows; },
	},
	watch: {
		branch: {
			immediate: true,
			handler(value, previous) {
				if (!value) return;
				if (previous && value !== previous) this.resetLocalFilters();
				this.load(true);
			},
		},
		programOffering(value, previous) { if (value !== previous && this.branch) this.load(true); },
		studentGroup(value, previous) { if (value !== previous && this.branch) this.load(true); },
		course(value, previous) { if (value !== previous && this.branch) this.load(true); },
	},
	methods: {
		formatNumber(value) { const number = Number(value || 0); return Number.isInteger(number) ? String(number) : number.toFixed(1); },
		rowKey(row) { return `${row.program_offering}:${row.student_group || 'class'}:${row.course}:${row.scheme || 'missing'}`; },
		coverageTone(status) {
			if (status === "Completed") return "success";
			if (["Missing Scheme", "Deferred"].includes(status)) return "danger";
			if (["Draft Scheme", "No Delivery Data", "In Progress"].includes(status)) return "warning";
			return "neutral";
		},
		resetLocalFilters() {
			this.filters = { academic_year: "", academic_term: "", instructor: "", coverage_status: "", include_historical: false };
			this.yearOptions = []; this.termOptions = []; this.instructorOptions = []; this.attentionOnly = false;
		},
		mergeOptions(target, values) {
			return [...new Set([...(target || []), ...(values || [])].filter(Boolean))].sort().reverse();
		},
		async load(reset = false) {
			if (!this.branch) return;
			if (reset) this.report.paging.start = 0;
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.scheme_coverage.get_scheme_coverage_report", {
					school_branch: this.branch,
					academic_year: this.filters.academic_year || undefined,
					academic_term: this.filters.academic_term || undefined,
					program_offering: this.programOffering || undefined,
					student_group: this.studentGroup || undefined,
					course: this.course || undefined,
					instructor: this.filters.instructor || undefined,
					coverage_status: this.filters.coverage_status || undefined,
					include_historical: this.filters.include_historical ? 1 : 0,
					start: reset ? 0 : this.report.paging.start,
					page_length: this.report.paging.page_length || 50,
				});
				this.report = response.message || blankReport();
				this.yearOptions = this.mergeOptions(this.yearOptions, this.report.options?.academic_years);
				this.termOptions = this.mergeOptions(this.termOptions, this.report.options?.academic_terms);
				this.statusOptions = this.report.options?.coverage_statuses || [];
				const known = new Map(this.instructorOptions.map((row) => [row.value, row]));
				for (const row of this.report.options?.instructors || []) known.set(row.value, row);
				this.instructorOptions = [...known.values()].sort((a, b) => String(a.label).localeCompare(String(b.label)));
				this.loaded = true;
			} catch (error) { this.error = error?.message || "Curriculum coverage could not be loaded."; }
			finally { this.loading = false; }
		},
		sessionChanged() { this.filters.academic_term = ""; this.load(true); },
		applyStatus(status) { this.attentionOnly = false; this.filters.coverage_status = status; this.load(true); },
		showAttention() { this.attentionOnly = true; this.filters.coverage_status = ""; this.load(true); },
		openRow(row) { this.$emit(row.scheme ? "open-scheme" : "open-context", row); },
		previousPage() { this.report.paging.start = Math.max(0, this.report.paging.start - this.report.paging.page_length); this.load(); },
		nextPage() { this.report.paging.start += this.report.paging.page_length; this.load(); },
	},
};
</script>

<style scoped>
.coverage-panel { display:grid; gap:1rem; padding:1rem; margin-top:1rem; border:1px solid var(--border-color); border-radius:12px; background:var(--card-bg); }.coverage-heading { display:flex; justify-content:space-between; align-items:center; gap:.75rem; flex-wrap:wrap; }.coverage-heading > div { display:grid; gap:.15rem; }.coverage-heading h3 { margin:0; }.coverage-heading small { color:var(--text-muted); }.coverage-filters { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:.65rem; }.coverage-filters label { display:grid; gap:.3rem; font-weight:600; }.coverage-filters .history-toggle { display:flex; align-items:center; align-self:end; min-height:2.4rem; gap:.5rem; font-weight:500; }.coverage-summary { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:.55rem; }.coverage-summary button,.coverage-summary div { display:grid; gap:.1rem; padding:.65rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); text-align:left; }.coverage-summary button:hover { border-color:var(--primary); }.coverage-summary span { font-size:.75rem; color:var(--text-muted); }.coverage-summary strong { font-size:1.1rem; }.coverage-table-wrap { overflow:auto; border:1px solid var(--border-color); border-radius:9px; }.coverage-table { width:100%; border-collapse:collapse; min-width:68rem; }.coverage-table th,.coverage-table td { padding:.65rem; border-bottom:1px solid var(--border-color); vertical-align:top; text-align:left; }.coverage-table th { font-size:.75rem; color:var(--text-muted); background:var(--control-bg); position:sticky; top:0; }.coverage-table td { font-size:.86rem; }.coverage-table td > strong,.coverage-table td > small { display:block; }.coverage-table small { margin-top:.18rem; color:var(--text-muted); }.coverage-cell { min-width:7rem; }.row-track { display:block; height:.35rem; margin-top:.35rem; overflow:hidden; border-radius:999px; background:var(--control-bg); }.row-track i { display:block; height:100%; background:var(--primary); }.coverage-paging { display:flex; justify-content:space-between; align-items:center; gap:.75rem; }.coverage-error { color:var(--red-600,#b42318); } @media (max-width:1050px) { .coverage-filters { grid-template-columns:repeat(2,minmax(0,1fr)); }.coverage-summary { grid-template-columns:repeat(3,minmax(0,1fr)); } } @media (max-width:620px) { .coverage-filters,.coverage-summary { grid-template-columns:1fr; } }
</style>
