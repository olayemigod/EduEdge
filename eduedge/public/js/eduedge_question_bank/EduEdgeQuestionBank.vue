<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="state.tenant_name || ''"
		:branch-name="state.current_branch?.branch_name || 'Question Bank'"
		:user-name="state.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-question-bank"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="CBT Question Governance"
					title="Question Bank"
					subtitle="Find and review permitted questions without exposing answer keys or internal marking content."
					:action-label="state.permissions?.can_create ? 'Create Question' : null"
					@action="openRoute('/app/eduedge-question-builder')"
				/>
			</template>

			<EdgeLoadingState v-if="initialLoading" message="Loading Question Bank..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="loadError"
				title="Question Bank could not load"
				:message="loadError"
				action-label="Try again"
				@retry="loadQuestions"
			/>
			<template v-else>
				<EdgeFilterBar title="Question filters">
					<div class="eduedge-question-bank-filters">
						<label class="eduedge-question-bank-field eduedge-question-bank-field--search">
							<span>Search</span>
							<input
								v-model.trim="filters.search"
								type="search"
								class="form-control"
								placeholder="Question code, question, subject, topic or curriculum"
								@input="scheduleSearch"
							/>
						</label>

						<label class="eduedge-question-bank-field">
							<span>Question Bank</span>
							<select v-model="filters.ownership_scope" class="form-control" @change="scopeChanged">
								<option v-for="option in state.options.ownership_scopes" :key="option.value" :value="option.value">
									{{ option.label }}
								</option>
							</select>
						</label>

						<label v-if="isSchoolBank" class="eduedge-question-bank-field">
							<span>Institution</span>
							<select v-model="filters.institution" class="form-control" @change="institutionChanged">
								<option value="">All permitted Institutions</option>
								<option v-for="option in state.options.institutions" :key="option.value" :value="option.value">
									{{ option.label }}
								</option>
							</select>
						</label>

						<label v-if="isSchoolBank" class="eduedge-question-bank-field">
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="filterChanged">
								<option value="">All permitted Branches</option>
								<option v-for="option in state.options.branches" :key="option.value" :value="option.value">
									{{ option.label }}
								</option>
							</select>
						</label>

						<div class="eduedge-question-bank-field">
							<span>Subject / Course</span>
							<EdgeLinkField
								:model-value="filters.course"
								:selected-label="courseLabel"
								:searcher="searchCourses"
								:context="{ institution: filters.institution }"
								placeholder="Search Subject or Course"
								:allow-clear="true"
								:open-on-focus="true"
								@update:model-value="courseValueChanged"
								@select="courseSelected"
								@clear="courseCleared"
							/>
						</div>

						<label class="eduedge-question-bank-field">
							<span>Status</span>
							<select v-model="filters.status" class="form-control" @change="filterChanged">
								<option value="">All statuses</option>
								<option v-for="option in state.options.statuses" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<label class="eduedge-question-bank-field">
							<span>Difficulty</span>
							<select v-model="filters.difficulty" class="form-control" @change="filterChanged">
								<option value="">All difficulties</option>
								<option v-for="option in state.options.difficulties" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<label class="eduedge-question-bank-field">
							<span>Question Type</span>
							<select v-model="filters.question_type" class="form-control" @change="filterChanged">
								<option value="">All question types</option>
								<option v-for="option in state.options.question_types" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<label class="eduedge-question-bank-field">
							<span>Exam Body / Source</span>
							<select v-model="filters.exam_body" class="form-control" @change="filterChanged">
								<option value="">All sources</option>
								<option v-for="option in state.options.exam_bodies" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<label class="eduedge-question-bank-field">
							<span>Sort</span>
							<select v-model="filters.sort_by" class="form-control" @change="filterChanged">
								<option v-for="option in state.options.sort" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" :disabled="loading" @click="clearFilters">Clear</button>
						<button
							v-if="state.permissions?.can_import"
							type="button"
							class="edge-button"
							@click="openRoute('/app/eduedge-question-batch')"
						>
							Batch Import
						</button>
						<button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="loadQuestions">Refresh</button>
					</template>
				</EdgeFilterBar>

				<section class="eduedge-question-bank-stats" aria-label="Question status summary">
					<button
						v-for="item in statusCards"
						:key="item.status || 'Total'"
						type="button"
						class="eduedge-question-bank-stat"
						:class="{ active: filters.status === item.status }"
						@click="selectStatus(item.status)"
					>
						<span>{{ item.label }}</span>
						<strong>{{ item.value }}</strong>
					</button>
				</section>

				<div v-if="loading" class="eduedge-question-bank-refreshing" role="status">Refreshing Question Bank…</div>

				<section class="eduedge-question-bank-panel">
					<div class="eduedge-question-bank-heading">
						<div>
							<p class="edge-eyebrow">Governed records</p>
							<h2>{{ resultHeading }}</h2>
							<p>{{ pagination.total }} question{{ pagination.total === 1 ? '' : 's' }} match the current filters.</p>
						</div>
						<button type="button" class="edge-button" @click="openRoute('/app/eduedge-cbt-operations')">Back to CBT Operations</button>
					</div>

					<EdgeEmptyState
						v-if="!state.rows.length && !loading"
						title="No questions match these filters"
						description="Clear one or more filters, or create a new question for the selected Question Bank."
						:action-label="state.permissions?.can_create ? 'Create Question' : null"
						@action="openRoute('/app/eduedge-question-builder')"
					/>

					<div v-else class="eduedge-question-bank-table" role="table" aria-label="Question Bank records">
						<div class="eduedge-question-bank-table__head" role="row">
							<span role="columnheader">Question</span>
							<span role="columnheader">Subject / Course</span>
							<span role="columnheader">Scope</span>
							<span role="columnheader">Type</span>
							<span role="columnheader">Status</span>
						</div>
						<button
							v-for="row in state.rows"
							:key="row.name"
							type="button"
							class="eduedge-question-bank-row"
							role="row"
							@click="openQuestion(row)"
						>
							<span class="eduedge-question-bank-question" role="cell">
								<strong>{{ row.question_code }}</strong>
								<span>{{ row.question_preview || 'No question preview available' }}</span>
								<small>Version {{ row.version_number || 1 }} · Updated {{ formatDate(row.modified) }}</small>
							</span>
							<span class="eduedge-question-bank-cell" role="cell">
								<strong>{{ row.course_label || row.course }}</strong>
								<small>{{ row.topic_label || row.topic || row.curriculum || 'No topic' }}</small>
							</span>
							<span class="eduedge-question-bank-cell" role="cell">
								<strong>{{ row.institution_label || row.ownership_scope }}</strong>
								<small>{{ row.branch_label || row.ownership_scope }}</small>
							</span>
							<span class="eduedge-question-bank-cell" role="cell">
								<strong>{{ row.question_type }}</strong>
								<small>{{ row.difficulty }} · {{ row.exam_body || 'No source' }}</small>
							</span>
							<span class="eduedge-question-bank-status" role="cell">
								<EdgeStatusBadge :label="row.status" :status="row.status" :tone="statusTone(row.status)" />
							</span>
						</button>
					</div>

					<div v-if="state.rows.length" class="eduedge-question-bank-pagination">
						<span>{{ paginationLabel }}</span>
						<div>
							<button type="button" class="edge-button" :disabled="loading || !pagination.has_previous" @click="previousPage">Previous</button>
							<button type="button" class="edge-button" :disabled="loading || !pagination.has_next" @click="nextPage">Next</button>
						</div>
					</div>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const SCHOOL_BANK = "School Question Bank";
const DEFAULT_FILTERS = Object.freeze({
	search: "",
	ownership_scope: SCHOOL_BANK,
	institution: "",
	branch: "",
	course: "",
	status: "",
	difficulty: "",
	question_type: "",
	exam_body: "",
	sort_by: "modified_desc",
});

export default {
	name: "EduEdgeQuestionBank",
	data() {
		return {
			initialLoading: true,
			loading: false,
			loadError: "",
			searchTimer: null,
			courseLabel: "",
			menuItems: EDUEDGE_MENU_ITEMS,
			filters: { ...DEFAULT_FILTERS },
			pagination: { start: 0, page_length: 20, total: 0, has_previous: false, has_next: false },
			state: {
				rows: [],
				counts: { Total: 0, Draft: 0, "Under Review": 0, Approved: 0, Retired: 0 },
				options: {
					ownership_scopes: [{ value: SCHOOL_BANK, label: SCHOOL_BANK }],
					institutions: [], branches: [], statuses: [], difficulties: [], question_types: [], exam_bodies: [], sort: [],
				},
				permissions: {}, user: {}, current_branch: null, tenant_name: "",
			},
		};
	},
	computed: {
		isSchoolBank() {
			return this.filters.ownership_scope === SCHOOL_BANK;
		},
		statusCards() {
			return [
				{ label: "All", status: "", value: this.state.counts.Total || 0 },
				{ label: "Draft", status: "Draft", value: this.state.counts.Draft || 0 },
				{ label: "Under Review", status: "Under Review", value: this.state.counts["Under Review"] || 0 },
				{ label: "Approved", status: "Approved", value: this.state.counts.Approved || 0 },
				{ label: "Retired", status: "Retired", value: this.state.counts.Retired || 0 },
			];
		},
		resultHeading() {
			if (this.filters.status) return `${this.filters.status} Questions`;
			return this.isSchoolBank ? "School Question Bank" : "EduEdge Examination Bank";
		},
		paginationLabel() {
			if (!this.pagination.total) return "No questions";
			const first = this.pagination.start + 1;
			const last = Math.min(this.pagination.total, this.pagination.start + this.state.rows.length);
			return `Showing ${first}–${last} of ${this.pagination.total}`;
		},
	},
	mounted() {
		this.loadQuestions();
	},
	beforeUnmount() {
		if (this.searchTimer) window.clearTimeout(this.searchTimer);
	},
	methods: {
		openRoute: openEduEdgeRoute,
		async loadQuestions() {
			if (this.loading) return;
			this.loading = true;
			this.loadError = "";
			try {
				const response = await frappe.call("eduedge.api.question_bank.get_question_bank", {
					...this.filters,
					start: this.pagination.start,
					page_length: this.pagination.page_length,
				});
				const next = response.message || {};
				this.state = { ...this.state, ...next, options: { ...this.state.options, ...(next.options || {}) } };
				this.filters = { ...this.filters, ...(next.filters || {}) };
				this.pagination = { ...this.pagination, ...(next.pagination || {}) };
				if (!this.filters.course) this.courseLabel = "";
			} catch (error) {
				this.loadError = error?.message || "Question Bank records could not be loaded.";
			} finally {
				this.loading = false;
				this.initialLoading = false;
			}
		},
		scheduleSearch() {
			if (this.searchTimer) window.clearTimeout(this.searchTimer);
			this.searchTimer = window.setTimeout(() => this.filterChanged(), 320);
		},
		filterChanged() {
			this.pagination.start = 0;
			this.loadQuestions();
		},
		scopeChanged() {
			this.filters.institution = "";
			this.filters.branch = "";
			this.filters.course = "";
			this.courseLabel = "";
			this.filterChanged();
		},
		institutionChanged() {
			this.filters.branch = "";
			this.filters.course = "";
			this.courseLabel = "";
			this.filterChanged();
		},
		selectStatus(status) {
			this.filters.status = status;
			this.filterChanged();
		},
		clearFilters() {
			const scope = this.state.options.ownership_scopes?.[0]?.value || SCHOOL_BANK;
			this.filters = { ...DEFAULT_FILTERS, ownership_scope: scope };
			this.courseLabel = "";
			this.pagination.start = 0;
			this.loadQuestions();
		},
		async searchCourses(query) {
			const response = await frappe.call("eduedge.api.question_bank.search_courses", {
				txt: query || "",
				institution: this.filters.institution || undefined,
				page_length: 20,
			});
			return response.message || [];
		},
		courseValueChanged(value) {
			this.filters.course = value || "";
			if (!value) this.courseLabel = "";
		},
		courseSelected(option) {
			this.filters.course = option?.value || "";
			this.courseLabel = option?.label || option?.value || "";
			this.filterChanged();
		},
		courseCleared() {
			this.filters.course = "";
			this.courseLabel = "";
			this.filterChanged();
		},
		openQuestion(row) {
			if (!row?.name) return;
			this.openRoute(`/app/eduedge-question-builder?question=${encodeURIComponent(row.name)}`);
		},
		previousPage() {
			this.pagination.start = Math.max(0, this.pagination.start - this.pagination.page_length);
			this.loadQuestions();
		},
		nextPage() {
			this.pagination.start += this.pagination.page_length;
			this.loadQuestions();
		},
		statusTone(status) {
			if (status === "Approved") return "success";
			if (status === "Under Review") return "warning";
			if (status === "Retired") return "danger";
			return "neutral";
		},
		formatDate(value) {
			if (!value) return "Unknown";
			if (frappe.datetime?.prettyDate) return frappe.datetime.prettyDate(value);
			return String(value);
		},
	},
};
</script>

<style scoped>
.eduedge-question-bank-filters {
	display: grid;
	gap: .8rem;
	grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
	width: 100%;
}
.eduedge-question-bank-field { display: flex; flex-direction: column; gap: .35rem; min-width: 0; }
.eduedge-question-bank-field > span { color: var(--edge-color-ink-700, var(--text-color)); font-size: .76rem; font-weight: 650; }
.eduedge-question-bank-field--search { grid-column: span 2; }
.eduedge-question-bank-stats {
	display: grid;
	gap: .75rem;
	grid-template-columns: repeat(auto-fit, minmax(8.5rem, 1fr));
	margin: 1rem 0;
}
.eduedge-question-bank-stat {
	background: var(--edge-color-surface, var(--card-bg));
	border: 1px solid var(--edge-color-border, var(--border-color));
	border-radius: var(--edge-radius-lg, .75rem);
	color: inherit;
	display: flex;
	flex-direction: column;
	gap: .25rem;
	padding: .85rem 1rem;
	text-align: left;
}
.eduedge-question-bank-stat:hover,
.eduedge-question-bank-stat.active { border-color: var(--edge-color-brand-400, #4b8fd5); box-shadow: 0 0 0 2px var(--edge-color-brand-50, #edf5ff); }
.eduedge-question-bank-stat span { color: var(--edge-color-ink-500, var(--text-muted)); font-size: .75rem; }
.eduedge-question-bank-stat strong { font-size: 1.45rem; }
.eduedge-question-bank-refreshing {
	background: var(--edge-color-brand-50, #edf5ff);
	border: 1px solid var(--edge-color-brand-100, #dcecff);
	border-radius: .6rem;
	color: var(--edge-color-brand-700, #174ea6);
	margin-bottom: .75rem;
	padding: .65rem .8rem;
}
.eduedge-question-bank-panel {
	background: var(--edge-color-surface, var(--card-bg));
	border: 1px solid var(--edge-color-border, var(--border-color));
	border-radius: var(--edge-radius-lg, .8rem);
	overflow: hidden;
}
.eduedge-question-bank-heading {
	align-items: flex-start;
	display: flex;
	gap: 1rem;
	justify-content: space-between;
	padding: 1rem 1.1rem;
}
.eduedge-question-bank-heading h2 { margin: .15rem 0 .25rem; }
.eduedge-question-bank-heading p { color: var(--edge-color-ink-500, var(--text-muted)); margin: 0; }
.eduedge-question-bank-table__head,
.eduedge-question-bank-row {
	display: grid;
	gap: .8rem;
	grid-template-columns: minmax(18rem, 2.2fr) minmax(10rem, 1.2fr) minmax(10rem, 1.1fr) minmax(9rem, 1fr) minmax(7rem, .7fr);
}
.eduedge-question-bank-table__head {
	background: var(--edge-color-surface-soft, var(--control-bg));
	border-bottom: 1px solid var(--edge-color-border, var(--border-color));
	color: var(--edge-color-ink-500, var(--text-muted));
	font-size: .7rem;
	font-weight: 700;
	letter-spacing: .04em;
	padding: .7rem 1rem;
	text-transform: uppercase;
}
.eduedge-question-bank-row {
	align-items: center;
	background: transparent;
	border: 0;
	border-bottom: 1px solid var(--edge-color-border, var(--border-color));
	color: inherit;
	padding: .9rem 1rem;
	text-align: left;
	width: 100%;
}
.eduedge-question-bank-row:hover { background: var(--edge-color-surface-soft, var(--control-bg)); }
.eduedge-question-bank-row:last-child { border-bottom: 0; }
.eduedge-question-bank-question,
.eduedge-question-bank-cell { display: flex; flex-direction: column; gap: .18rem; min-width: 0; }
.eduedge-question-bank-question > span { color: var(--edge-color-ink-700, var(--text-color)); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.eduedge-question-bank-question small,
.eduedge-question-bank-cell small { color: var(--edge-color-ink-500, var(--text-muted)); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.eduedge-question-bank-status { justify-self: start; }
.eduedge-question-bank-pagination {
	align-items: center;
	border-top: 1px solid var(--edge-color-border, var(--border-color));
	display: flex;
	justify-content: space-between;
	padding: .8rem 1rem;
}
.eduedge-question-bank-pagination > div { display: flex; gap: .5rem; }
@media (max-width: 900px) {
	.eduedge-question-bank-field--search { grid-column: auto; }
	.eduedge-question-bank-table__head { display: none; }
	.eduedge-question-bank-row { align-items: flex-start; grid-template-columns: 1fr; }
	.eduedge-question-bank-status { justify-self: start; }
}
@media (max-width: 600px) {
	.eduedge-question-bank-heading,
	.eduedge-question-bank-pagination { align-items: stretch; flex-direction: column; }
	.eduedge-question-bank-pagination > div { justify-content: flex-end; }
}
</style>
