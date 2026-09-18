<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="tenantName"
		:branch-name="branchLabel"
		:menu-items="menuItems"
		active-route="/app/eduedge-result-analytics"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Assessments and Results"
					title="Result Analytics"
					subtitle="Review governed assessment performance by branch, academic period, class and subject."
					action-label="Assessment Results"
					@action="openRoute('/app/eduedge-assessment-results')"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loaded" message="Loading result analytics..." :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loaded" title="Result Analytics could not load" :message="error" action-label="Try again" @retry="load" />
			<template v-else>
				<EdgeFilterBar title="Result filters">
					<div class="analytics-filters">
						<label><span>Branch / Campus</span><select v-model="filters.branch" class="form-control" @change="changeBranch"><option v-for="row in data.allowed_branches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option></select></label>
						<label><span>Academic Year</span><select v-model="filters.academic_year" class="form-control"><option value="">All</option><option v-for="value in data.options.academic_years" :key="value" :value="value">{{ value }}</option></select></label>
						<label><span>Academic Term</span><select v-model="filters.academic_term" class="form-control"><option value="">All</option><option v-for="value in data.options.academic_terms" :key="value" :value="value">{{ value }}</option></select></label>
						<label><span>Class / Student Group</span><select v-model="filters.student_group" class="form-control"><option value="">All</option><option v-for="value in data.options.student_groups" :key="value" :value="value">{{ value }}</option></select></label>
						<label><span>Subject / Course</span><select v-model="filters.course" class="form-control"><option value="">All</option><option v-for="value in data.options.courses" :key="value" :value="value">{{ value }}</option></select></label>
						<label><span>Assessment Group</span><select v-model="filters.assessment_group" class="form-control"><option value="">All</option><option v-for="value in data.options.assessment_groups" :key="value" :value="value">{{ value }}</option></select></label>
						<label><span>Status</span><select v-model="filters.status" class="form-control"><option value="">All</option><option>Draft</option><option>Submitted</option><option>Cancelled</option></select></label>
					</div>
					<template #actions><button type="button" class="edge-button" @click="resetFilters">Reset</button><button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="load">Apply</button></template>
				</EdgeFilterBar>

				<p v-if="error" class="analytics-note">{{ error }}</p>

				<EdgeDashboardLayout min-column-width="10rem">
					<EdgeStatCard label="Results" :value="data.summary.results" helper="Permitted result records" />
					<EdgeStatCard label="Submitted" :value="data.summary.submitted" helper="Final result records" />
					<EdgeStatCard label="Draft" :value="data.summary.draft" helper="Still editable" />
					<EdgeStatCard label="Average" :value="percentageLabel(data.summary.average_percentage)" helper="Average score percentage" />
					<EdgeStatCard label="Highest" :value="percentageLabel(data.summary.highest_percentage)" helper="Highest score percentage" />
					<EdgeStatCard label="Lowest" :value="percentageLabel(data.summary.lowest_percentage)" helper="Lowest score percentage" />
				</EdgeDashboardLayout>

				<section class="analytics-panel">
					<div class="analytics-heading"><div><p class="edge-eyebrow">Grade distribution</p><h2>Performance bands</h2></div><small v-if="data.summary.summary_truncated">Summary is capped at the first 2,000 permitted records for this filter.</small></div>
					<EdgeEmptyState v-if="!data.grade_distribution.length" title="No grade distribution available" description="Adjust the filters or record assessment results first." />
					<div v-else class="grade-grid">
						<article v-for="row in data.grade_distribution" :key="row.grade"><strong>{{ row.grade }}</strong><span>{{ row.count }} result{{ row.count === 1 ? '' : 's' }}</span></article>
					</div>
				</section>

				<section class="analytics-panel">
					<div class="analytics-heading"><div><p class="edge-eyebrow">Result records</p><h2>Assessment results</h2></div><span>Showing up to {{ data.row_limit }} records</span></div>
					<EdgeEmptyState v-if="!data.rows.length" title="No results found" description="No permitted Assessment Results match the selected filters." />
					<div v-else class="analytics-table-wrap">
						<table class="table analytics-table">
							<thead><tr><th>Student</th><th>Subject</th><th>Class</th><th>Assessment</th><th>Score</th><th>%</th><th>Grade</th><th>Status</th><th>Action</th></tr></thead>
							<tbody>
								<tr v-for="row in data.rows" :key="row.name">
									<td><strong>{{ row.student_name || row.student }}</strong><small>{{ row.student }}</small></td>
									<td>{{ row.course || '—' }}</td>
									<td>{{ row.student_group || '—' }}</td>
									<td>{{ row.assessment_plan }}</td>
									<td>{{ numberLabel(row.total_score) }} / {{ numberLabel(row.maximum_score) }}</td>
									<td>{{ percentageLabel(row.percentage) }}</td>
									<td>{{ row.grade || '—' }}</td>
									<td><EdgeStatusBadge :label="row.status_label" :status="row.status_label" :tone="statusTone(row.status_label)" /></td>
									<td><button type="button" class="edge-button" @click="openResult(row.name)">Open</button></td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const blankData = () => ({
	allowed_branches: [],
	branch: "",
	filters: {},
	options: { academic_years: [], academic_terms: [], student_groups: [], courses: [], assessment_groups: [] },
	summary: { results: 0, submitted: 0, draft: 0, average_percentage: 0, highest_percentage: 0, lowest_percentage: 0, summary_truncated: false },
	grade_distribution: [],
	rows: [],
	row_limit: 100,
});

export default {
	name: "EduEdgeResultAnalytics",
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS,
			loading: true,
			loaded: false,
			error: "",
			filters: { branch: "", academic_year: "", academic_term: "", student_group: "", course: "", assessment_group: "", status: "" },
			data: blankData(),
		};
	},
	computed: {
		tenantName() { return frappe.boot?.eduedge_ui_identity?.tenant_name || ""; },
		branchLabel() {
			const branch = this.data.allowed_branches.find((row) => row.name === this.filters.branch);
			return branch?.branch_name || branch?.name || "";
		},
	},
	mounted() {
		const params = new URLSearchParams(window.location.search || "");
		for (const key of Object.keys(this.filters)) this.filters[key] = params.get(key) || "";
		this.load();
	},
	methods: {
		openRoute: openEduEdgeRoute,
		percentageLabel(value) { return `${Number(value || 0).toFixed(2)}%`; },
		numberLabel(value) { return Number(value || 0).toFixed(2); },
		statusTone(status) { return status === "Submitted" ? "success" : status === "Cancelled" ? "danger" : "warning"; },
		async load() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.assessment_workbenches.get_result_analytics", {
					branch: this.filters.branch || undefined,
					academic_year: this.filters.academic_year || undefined,
					academic_term: this.filters.academic_term || undefined,
					student_group: this.filters.student_group || undefined,
					course: this.filters.course || undefined,
					assessment_group: this.filters.assessment_group || undefined,
					status: this.filters.status || undefined,
				});
				this.data = response.message || blankData();
				this.filters.branch = this.data.branch || this.filters.branch;
				this.filters = { ...this.filters, ...(this.data.filters || {}), branch: this.data.branch || this.filters.branch };
				this.loaded = true;
			} catch (error) {
				this.error = error?.message || "Result Analytics could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		async changeBranch() {
			this.filters.academic_year = "";
			this.filters.academic_term = "";
			this.filters.student_group = "";
			this.filters.course = "";
			this.filters.assessment_group = "";
			await this.load();
		},
		resetFilters() {
			const branch = this.filters.branch;
			this.filters = { branch, academic_year: "", academic_term: "", student_group: "", course: "", assessment_group: "", status: "" };
			this.load();
		},
		openResult(name) { window.open(`/app/assessment-result/${encodeURIComponent(name)}`, "_blank", "noopener,noreferrer"); },
	},
};
</script>

<style scoped>
.analytics-filters { display:grid; grid-template-columns:repeat(auto-fit,minmax(11rem,1fr)); gap:.75rem; width:100%; }
.analytics-filters label { display:grid; gap:.35rem; font-weight:600; }
.analytics-panel { margin-top:1rem; padding:1rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.analytics-heading { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; flex-wrap:wrap; margin-bottom:1rem; }
.analytics-heading h2 { margin:.2rem 0 0; }
.analytics-heading small,.analytics-heading span,.analytics-note,.analytics-table td small { color:var(--text-muted); }
.grade-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(8rem,1fr)); gap:.75rem; }
.grade-grid article { display:grid; gap:.2rem; padding:.8rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.grade-grid strong { font-size:1.15rem; }
.analytics-table-wrap { overflow-x:auto; }
.analytics-table { min-width:72rem; margin:0; }
.analytics-table th { white-space:nowrap; }
.analytics-table td { vertical-align:middle; }
.analytics-table td:first-child strong,.analytics-table td:first-child small { display:block; }
.analytics-note { border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); padding:.75rem; }
</style>
