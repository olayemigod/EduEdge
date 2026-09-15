<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:branch-name="selectedBranch?.branch_name || 'Result Broadsheet'"
		:menu-items="menuItems"
		active-route="/app/eduedge-result-broadsheet"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Assessments & Results"
					title="Result Broadsheet"
					subtitle="Review a class result matrix from the latest approved published result version and export the same immutable values."
				/>
			</template>

			<EdgeFilterBar title="Published result scope">
				<div class="broadsheet-filters">
					<label><span>Branch / Campus</span><select v-model="filters.school_branch" class="form-control" @change="branchChanged"><option v-for="row in report.allowed_branches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option></select></label>
					<label><span>Academic Year</span><select v-model="filters.academic_year" class="form-control" @change="load"><option value="">Select year</option><option v-for="value in report.options.academic_years" :key="value" :value="value">{{ value }}</option></select></label>
					<label><span>Result Type</span><select v-model="filters.result_mode" class="form-control" @change="modeChanged"><option value="Terminal">Terminal</option><option value="Annual">Annual</option></select></label>
					<label v-if="filters.result_mode !== 'Annual'"><span>Term / Semester</span><select v-model="filters.academic_term" class="form-control" @change="load"><option value="">Select term</option><option v-for="value in report.options.academic_terms" :key="value" :value="value">{{ value }}</option></select></label>
					<label><span>Class / Group</span><select v-model="filters.student_group" class="form-control" @change="load"><option value="">Select class</option><option v-for="value in report.options.student_groups" :key="value" :value="value">{{ value }}</option></select></label>
				</div>
				<template #actions>
					<button type="button" class="edge-button" :disabled="loading" @click="load">Refresh</button>
					<a v-if="report.publication" class="edge-button edge-button--primary" :href="downloadUrl">Export CSV</a>
				</template>
			</EdgeFilterBar>

			<EdgeLoadingState v-if="loading && !loaded" message="Loading published broadsheet..." :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loaded" title="Result Broadsheet could not load" :message="error" action-label="Try again" @retry="load" />
			<template v-else>
				<p v-if="error" class="broadsheet-error">{{ error }}</p>
				<div v-if="report.publication" class="publication-summary">
					<div><span>Publication</span><strong>v{{ report.publication.publication_version || 1 }}</strong></div>
					<div><span>Students</span><strong>{{ report.student_count }}</strong></div>
					<div><span>Subjects</span><strong>{{ report.subject_count }}</strong></div>
					<div><span>Mode</span><strong>{{ report.publication.result_mode }}</strong></div>
				</div>

				<EdgeEmptyState
					v-if="!report.publication"
					title="Select a published result scope"
					description="Choose Academic Year, Class and Result Type. Terminal broadsheets also require a Term / Semester."
				/>
				<section v-else class="broadsheet-panel">
					<div class="broadsheet-note">{{ report.note }}</div>
					<div class="table-wrap">
						<table class="broadsheet-table">
							<thead>
								<tr>
									<th class="sticky-col sticky-1">Roll</th>
									<th class="sticky-col sticky-2">Student</th>
									<th v-for="subject in report.subjects" :key="subject.course">{{ subject.course_name }}</th>
									<th>Overall %</th>
									<th>Grade</th>
									<th>Attendance %</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="row in report.rows" :key="row.student">
									<td class="sticky-col sticky-1">{{ row.roll_number || '-' }}</td>
									<td class="sticky-col sticky-2"><strong>{{ row.student_name }}</strong><small>{{ row.student }}</small></td>
									<td v-for="subject in report.subjects" :key="subject.course">{{ score(row.scores[subject.course]) }}</td>
									<td><strong>{{ score(row.overall_percentage) }}</strong></td>
									<td>{{ row.overall_grade || '-' }}</td>
									<td>{{ score(row.attendance_percentage) }}</td>
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

const blankReport = () => ({
	filters: {},
	allowed_branches: [],
	options: { academic_years: [], academic_terms: [], student_groups: [], result_modes: [] },
	publication: null,
	subjects: [],
	rows: [],
	student_count: 0,
	subject_count: 0,
	note: "",
});

export default {
	name: "EduEdgeResultBroadsheet",
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS,
			report: blankReport(),
			filters: { school_branch: "", academic_year: "", academic_term: "", student_group: "", result_mode: "Terminal" },
			loading: true,
			loaded: false,
			error: "",
		};
	},
	computed: {
		selectedBranch() { return this.report.allowed_branches.find((row) => row.name === this.filters.school_branch) || null; },
		downloadUrl() {
			if (!this.report.publication) return "#";
			const params = new URLSearchParams({ publication: this.report.publication.name });
			return `/api/method/eduedge.api.result_broadsheet.download_broadsheet_csv?${params.toString()}`;
		},
	},
	mounted() { this.load(); },
	methods: {
		openRoute: openEduEdgeRoute,
		score(value) { const number = Number(value); return value === null || value === undefined || !Number.isFinite(number) ? "-" : number.toFixed(2); },
		async load() {
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.result_broadsheet.get_broadsheet_context", {
					school_branch: this.filters.school_branch || undefined,
					academic_year: this.filters.academic_year || undefined,
					academic_term: this.filters.result_mode === "Annual" ? undefined : (this.filters.academic_term || undefined),
					student_group: this.filters.student_group || undefined,
					result_mode: this.filters.result_mode || "Terminal",
				});
				this.report = response.message || blankReport();
				this.filters = { ...this.filters, ...(this.report.filters || {}) };
				this.loaded = true;
			} catch (error) {
				this.error = error?.message || "Result Broadsheet could not be loaded.";
			} finally { this.loading = false; }
		},
		branchChanged() {
			this.filters.academic_year = ""; this.filters.academic_term = ""; this.filters.student_group = "";
			this.load();
		},
		modeChanged() {
			if (this.filters.result_mode === "Annual") this.filters.academic_term = "";
			this.load();
		},
	},
};
</script>

<style scoped>
.broadsheet-filters{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.65rem;width:100%}.broadsheet-filters label{display:grid;gap:.3rem;font-weight:600}.publication-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.65rem;margin-top:1rem}.publication-summary div{padding:.7rem;border:1px solid var(--border-color);border-radius:9px;background:var(--card-bg)}.publication-summary span{display:block;color:var(--text-muted);font-size:.78rem}.publication-summary strong{display:block;margin-top:.15rem}.broadsheet-panel{margin-top:1rem}.broadsheet-note{padding:.7rem;margin-bottom:.65rem;border:1px solid var(--border-color);border-radius:9px;background:var(--control-bg);color:var(--text-muted)}.table-wrap{overflow:auto;max-height:68vh;border:1px solid var(--border-color);border-radius:10px}.broadsheet-table{border-collapse:separate;border-spacing:0;min-width:100%;width:max-content;background:var(--card-bg)}.broadsheet-table th,.broadsheet-table td{padding:.58rem .65rem;border-right:1px solid var(--border-color);border-bottom:1px solid var(--border-color);white-space:nowrap;text-align:right}.broadsheet-table th{position:sticky;top:0;z-index:3;background:var(--control-bg);font-size:.78rem}.broadsheet-table th:nth-child(1),.broadsheet-table th:nth-child(2),.broadsheet-table td:nth-child(1),.broadsheet-table td:nth-child(2){text-align:left}.broadsheet-table td small{display:block;color:var(--text-muted)}.sticky-col{position:sticky;z-index:2;background:var(--card-bg)}.sticky-1{left:0;min-width:4rem}.sticky-2{left:4rem;min-width:13rem}.broadsheet-table th.sticky-col{z-index:4;background:var(--control-bg)}.broadsheet-error{color:var(--red-600,#b42318)}@media(max-width:950px){.broadsheet-filters{grid-template-columns:repeat(2,minmax(0,1fr))}.publication-summary{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:620px){.broadsheet-filters,.publication-summary{grid-template-columns:1fr}.sticky-2{min-width:11rem}}
</style>
