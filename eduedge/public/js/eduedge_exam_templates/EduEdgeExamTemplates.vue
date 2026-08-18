<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="selectedCompanyLabel"
		branch-name="Exam Templates"
		:user-name="state.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-exam-templates"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="CBT Exam Design"
					title="Exam Templates"
					subtitle="Reuse Universal, Institution-wide, Branch-wide, Any-Subject, or Specific-Subject exam designs."
					:action-label="state.permissions?.can_create ? 'Create Template' : null"
					@action="openBuilder()"
				/>
			</template>

			<EdgeLoadingState v-if="initialLoading" message="Loading Exam Templates..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="loadError"
				title="Exam Templates could not load"
				:message="loadError"
				action-label="Try again"
				@retry="loadTemplates"
			/>
			<template v-else>
				<EdgeFilterBar title="Template filters">
					<div class="eduedge-template-filters">
						<label class="eduedge-template-field eduedge-template-field--search">
							<span>Search</span>
							<input
								v-model.trim="filters.search"
								type="search"
								class="form-control"
								placeholder="Title, code, purpose, subject, programme or class"
								@input="scheduleSearch"
							/>
						</label>

						<label class="eduedge-template-field">
							<span>Examination Scope</span>
							<select v-model="filters.exam_scope" class="form-control" @change="scopeChanged">
								<option v-for="option in state.options.scope" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<label v-if="isSchoolScope" class="eduedge-template-field">
							<span>Company</span>
							<select v-model="filters.company" class="form-control" @change="companyChanged">
								<option value="">All permitted Companies</option>
								<option v-for="option in state.options.companies" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<label v-if="isSchoolScope" class="eduedge-template-field">
							<span>Reuse Scope</span>
							<select v-model="filters.template_reuse_scope" class="form-control" @change="filterChanged">
								<option value="">All reuse scopes</option>
								<option v-for="option in state.options.reuse_scopes" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<label v-if="isSchoolScope" class="eduedge-template-field">
							<span>Institution</span>
							<select v-model="filters.institution" class="form-control" @change="institutionChanged">
								<option value="">All permitted Institutions</option>
								<option v-for="option in state.options.institutions" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<label v-if="isSchoolScope" class="eduedge-template-field">
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="branchChanged">
								<option value="">All permitted Branches</option>
								<option v-for="option in state.options.branches" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<label class="eduedge-template-field">
							<span>Subject Applicability</span>
							<select v-model="filters.subject_applicability" class="form-control" @change="subjectScopeChanged">
								<option value="">Any or Specific Subject</option>
								<option v-for="option in state.options.subject_applicability" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<div class="eduedge-template-field">
							<span>Subject / Course</span>
							<EdgeLinkField
								:model-value="filters.course"
								:selected-label="courseLabel"
								:searcher="searchCourses"
								:context="filters"
								placeholder="Search Subject or Course"
								:allow-clear="true"
								:open-on-focus="true"
								:disabled="filters.subject_applicability === 'Any Subject'"
								@update:model-value="courseValueChanged"
								@select="courseSelected"
								@clear="courseCleared"
							/>
						</div>

						<label class="eduedge-template-field">
							<span>Exam Purpose</span>
							<select v-model="filters.exam_purpose" class="form-control" @change="filterChanged">
								<option value="">All purposes</option>
								<option v-for="option in state.options.purposes" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<label class="eduedge-template-field">
							<span>Content Mode</span>
							<select v-model="filters.template_mode" class="form-control" @change="filterChanged">
								<option value="">Blueprint or Fixed Set</option>
								<option v-for="option in state.options.template_modes" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<label class="eduedge-template-field">
							<span>Status</span>
							<select v-model="filters.status" class="form-control" @change="filterChanged">
								<option value="">All statuses</option>
								<option v-for="option in state.options.statuses" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<label class="eduedge-template-field">
							<span>Sort</span>
							<select v-model="filters.sort_by" class="form-control" @change="filterChanged">
								<option value="modified_desc">Recently updated</option>
								<option value="modified_asc">Oldest updated</option>
								<option value="code_asc">Template code A–Z</option>
								<option value="code_desc">Template code Z–A</option>
								<option value="title_asc">Template title A–Z</option>
								<option value="status_asc">Status</option>
							</select>
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" :disabled="loading" @click="clearFilters">Clear</button>
						<button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="loadTemplates">Refresh</button>
					</template>
				</EdgeFilterBar>

				<section class="eduedge-template-stats" aria-label="Template status summary">
					<button
						v-for="card in statusCards"
						:key="card.status || 'Total'"
						type="button"
						class="eduedge-template-stat"
						:class="{ active: filters.status === card.status }"
						@click="selectStatus(card.status)"
					>
						<span>{{ card.label }}</span>
						<strong>{{ card.value }}</strong>
					</button>
				</section>

				<div v-if="loading" class="eduedge-template-refreshing" role="status">Refreshing Exam Templates…</div>

				<section class="eduedge-template-panel">
					<div class="eduedge-template-heading">
						<div>
							<p class="edge-eyebrow">Reusable exam definitions</p>
							<h2>{{ resultHeading }}</h2>
							<p>{{ pagination.total }} template{{ pagination.total === 1 ? '' : 's' }} match the current filters.</p>
						</div>
						<button type="button" class="edge-button" @click="openRoute('/app/eduedge-cbt-operations')">Back to CBT Operations</button>
					</div>

					<EdgeEmptyState
						v-if="!state.rows.length && !loading"
						title="No templates match these filters"
						description="Create a reusable policy blueprint instead of rebuilding the same exam settings for every subject or sitting."
						:action-label="state.permissions?.can_create ? 'Create Template' : null"
						@action="openBuilder()"
					/>

					<div v-else class="eduedge-template-table" role="table" aria-label="Exam Template records">
						<div class="eduedge-template-table__head" role="row">
							<span role="columnheader">Template</span>
							<span role="columnheader">Reuse Scope</span>
							<span role="columnheader">Subject</span>
							<span role="columnheader">Exam Design</span>
							<span role="columnheader">Status</span>
						</div>
						<button
							v-for="row in state.rows"
							:key="row.name"
							type="button"
							class="eduedge-template-row"
							role="row"
							@click="openBuilder(row)"
						>
							<span class="eduedge-template-primary" role="cell">
								<strong>{{ row.template_title }}</strong>
								<span>{{ row.template_code }} · Version {{ row.version_number || 1 }}</span>
								<small>{{ row.exam_purpose }} · Updated {{ formatDate(row.modified) }}</small>
							</span>
							<span class="eduedge-template-cell" role="cell">
								<strong>{{ row.scope_label }}</strong>
								<small>{{ row.exam_scope }}</small>
							</span>
							<span class="eduedge-template-cell" role="cell">
								<strong>{{ row.subject_applicability }}</strong>
								<span>{{ row.course_label }}</span>
							</span>
							<span class="eduedge-template-cell" role="cell">
								<strong>{{ row.template_mode }}</strong>
								<span>{{ row.duration_minutes || 0 }} minutes</span>
								<small>{{ row.question_count || 0 }} fixed questions · {{ row.total_marks || 0 }} marks</small>
							</span>
							<span class="eduedge-template-status" role="cell">
								<EdgeStatusBadge :label="row.status" :status="row.status" :tone="statusTone(row.status)" />
							</span>
						</button>
					</div>

					<div v-if="state.rows.length" class="eduedge-template-pagination">
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

const SCHOOL_EXAM = "School Examination";

function defaultState() {
	return {
		rows: [],
		counts: {},
		filters: {},
		options: {
			scope: [], companies: [], institutions: [], branches: [], reuse_scopes: [], subject_applicability: [], purposes: [], template_modes: [], statuses: [], exam_bodies: [], page_lengths: [],
		},
		pagination: { start: 0, page_length: 20, total: 0, has_previous: false, has_next: false },
		permissions: {},
		user: {},
	};
}

function defaultFilters() {
	return {
		search: "",
		exam_scope: SCHOOL_EXAM,
		company: "",
		institution: "",
		branch: "",
		template_reuse_scope: "",
		subject_applicability: "",
		course: "",
		status: "",
		exam_purpose: "",
		template_mode: "",
		exam_body: "",
		sort_by: "modified_desc",
	};
}

export default {
	name: "EduEdgeExamTemplates",
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS,
			initialLoading: true,
			loading: false,
			loadError: "",
			searchTimer: null,
			requestSequence: 0,
			courseLabel: "",
			filters: defaultFilters(),
			state: defaultState(),
		};
	},
	computed: {
		isSchoolScope() { return this.filters.exam_scope === SCHOOL_EXAM; },
		pagination() { return this.state.pagination || defaultState().pagination; },
		selectedCompanyLabel() {
			return this.state.options.companies.find((row) => row.value === this.filters.company)?.label || "Exam Templates";
		},
		statusCards() {
			return [
				{ label: "All", status: "", value: this.state.counts.Total || 0 },
				...(this.state.options.statuses || []).map((row) => ({ label: row.label, status: row.value, value: this.state.counts[row.value] || 0 })),
			];
		},
		resultHeading() { return this.filters.status ? `${this.filters.status} templates` : "All permitted templates"; },
		paginationLabel() {
			if (!this.pagination.total) return "No records";
			const first = this.pagination.start + 1;
			const last = Math.min(this.pagination.start + this.pagination.page_length, this.pagination.total);
			return `${first}–${last} of ${this.pagination.total}`;
		},
	},
	mounted() { this.loadTemplates(); },
	beforeUnmount() { if (this.searchTimer) clearTimeout(this.searchTimer); },
	methods: {
		openRoute: openEduEdgeRoute,
		async loadTemplates({ resetPage = false } = {}) {
			const sequence = ++this.requestSequence;
			this.loading = true;
			this.loadError = "";
			const start = resetPage ? 0 : this.pagination.start || 0;
			try {
				const response = await frappe.call("eduedge.api.exam_templates.get_exam_templates", { ...this.filters, start, page_length: this.pagination.page_length || 20 });
				if (sequence !== this.requestSequence) return;
				this.state = response.message || defaultState();
				this.filters = { ...this.filters, ...(this.state.filters || {}) };
				if (!this.courseLabel && this.filters.course) this.courseLabel = this.filters.course;
			} catch (error) {
				if (sequence !== this.requestSequence) return;
				this.loadError = error?.message || "Exam Templates could not be loaded.";
			} finally {
				if (sequence === this.requestSequence) {
					this.loading = false;
					this.initialLoading = false;
				}
			}
		},
		scheduleSearch() {
			if (this.searchTimer) clearTimeout(this.searchTimer);
			this.searchTimer = setTimeout(() => this.loadTemplates({ resetPage: true }), 300);
		},
		filterChanged() { this.loadTemplates({ resetPage: true }); },
		scopeChanged() {
			this.filters.company = "";
			this.filters.institution = "";
			this.filters.branch = "";
			this.filters.course = "";
			this.courseLabel = "";
			this.loadTemplates({ resetPage: true });
		},
		companyChanged() {
			this.filters.institution = "";
			this.filters.branch = "";
			this.filters.course = "";
			this.courseLabel = "";
			this.loadTemplates({ resetPage: true });
		},
		institutionChanged() {
			this.filters.branch = "";
			this.filters.course = "";
			this.courseLabel = "";
			this.loadTemplates({ resetPage: true });
		},
		branchChanged() {
			this.filters.course = "";
			this.courseLabel = "";
			this.loadTemplates({ resetPage: true });
		},
		subjectScopeChanged() {
			if (this.filters.subject_applicability === "Any Subject") {
				this.filters.course = "";
				this.courseLabel = "";
			}
			this.loadTemplates({ resetPage: true });
		},
		selectStatus(status) { this.filters.status = status; this.loadTemplates({ resetPage: true }); },
		clearFilters() {
			this.filters = defaultFilters();
			this.courseLabel = "";
			this.loadTemplates({ resetPage: true });
		},
		async searchCourses(query) {
			const response = await frappe.call("eduedge.api.exam_templates.search_template_options", {
				fieldname: "course",
				txt: query || "",
				values: JSON.stringify({ ...this.filters, school_branch: this.filters.branch }),
			});
			return response.message || [];
		},
		courseValueChanged(value) { this.filters.course = value || ""; if (!value) this.courseLabel = ""; },
		courseSelected(option) { this.filters.course = option?.value || ""; this.courseLabel = option?.label || this.filters.course; this.filterChanged(); },
		courseCleared() { this.filters.course = ""; this.courseLabel = ""; this.filterChanged(); },
		previousPage() {
			if (!this.pagination.has_previous) return;
			this.state.pagination.start = Math.max(0, this.pagination.start - this.pagination.page_length);
			this.loadTemplates();
		},
		nextPage() {
			if (!this.pagination.has_next) return;
			this.state.pagination.start = this.pagination.start + this.pagination.page_length;
			this.loadTemplates();
		},
		openBuilder(row = null) {
			const route = row?.name ? `/app/eduedge-exam-template-builder?template=${encodeURIComponent(row.name)}` : "/app/eduedge-exam-template-builder";
			this.openRoute(route);
		},
		formatDate(value) {
			if (!value) return "—";
			try { return frappe.datetime.str_to_user(value); } catch (_error) { return value; }
		},
		statusTone(status) {
			return ({ Draft: "neutral", "Under Review": "warning", Approved: "success", Retired: "danger" })[status] || "neutral";
		},
	},
};
</script>

<style scoped>
.eduedge-template-filters { display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); gap: .8rem; width: 100%; }
.eduedge-template-field { display: grid; gap: .35rem; min-width: 0; }
.eduedge-template-field > span { font-size: .78rem; font-weight: 700; color: var(--edge-text-muted, #64748b); }
.eduedge-template-field--search { grid-column: span 2; }
.eduedge-template-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr)); gap: .7rem; margin: 1rem 0; }
.eduedge-template-stat { border: 1px solid var(--edge-border, #e2e8f0); border-radius: .8rem; background: var(--edge-surface, #fff); padding: .8rem; text-align: left; display: grid; gap: .2rem; }
.eduedge-template-stat.active { box-shadow: 0 0 0 2px var(--edge-accent, #2563eb); }
.eduedge-template-stat span { color: var(--edge-text-muted, #64748b); font-size: .8rem; }
.eduedge-template-stat strong { font-size: 1.35rem; }
.eduedge-template-panel { border: 1px solid var(--edge-border, #e2e8f0); border-radius: 1rem; background: var(--edge-surface, #fff); overflow: hidden; }
.eduedge-template-heading { display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start; padding: 1rem; border-bottom: 1px solid var(--edge-border, #e2e8f0); }
.eduedge-template-heading h2, .eduedge-template-heading p { margin: 0; }
.eduedge-template-table__head, .eduedge-template-row { display: grid; grid-template-columns: minmax(16rem, 2fr) minmax(14rem, 1.3fr) minmax(12rem, 1fr) minmax(12rem, 1fr) minmax(7rem, .6fr); gap: .8rem; align-items: center; }
.eduedge-template-table__head { padding: .75rem 1rem; background: var(--edge-surface-muted, #f8fafc); color: var(--edge-text-muted, #64748b); font-size: .78rem; font-weight: 700; }
.eduedge-template-row { width: 100%; border: 0; border-top: 1px solid var(--edge-border, #e2e8f0); background: transparent; text-align: left; padding: .9rem 1rem; }
.eduedge-template-row:hover { background: var(--edge-surface-muted, #f8fafc); }
.eduedge-template-primary, .eduedge-template-cell { display: grid; gap: .15rem; min-width: 0; }
.eduedge-template-primary span, .eduedge-template-cell span, .eduedge-template-primary small, .eduedge-template-cell small { color: var(--edge-text-muted, #64748b); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.eduedge-template-status { justify-self: start; }
.eduedge-template-pagination { display: flex; justify-content: space-between; align-items: center; padding: 1rem; border-top: 1px solid var(--edge-border, #e2e8f0); }
.eduedge-template-pagination > div { display: flex; gap: .5rem; }
.eduedge-template-refreshing { padding: .65rem 1rem; border-radius: .6rem; background: var(--edge-surface-muted, #f8fafc); margin-bottom: .7rem; }
@media (max-width: 900px) {
	.eduedge-template-field--search { grid-column: span 1; }
	.eduedge-template-table__head { display: none; }
	.eduedge-template-row { grid-template-columns: 1fr; gap: .5rem; }
	.eduedge-template-status { justify-self: stretch; }
}
</style>
