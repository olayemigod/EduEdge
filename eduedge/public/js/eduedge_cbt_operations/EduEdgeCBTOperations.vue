<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="context.tenant_name || ''"
		:branch-name="context.current_branch?.branch_name || ''"
		:user-name="context.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-cbt-operations"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Computer-Based Testing"
					title="CBT Operations"
					subtitle="Govern examination centres, approved question banks, reusable exam templates, and candidate-control policies."
					:action-label="context.can_manage_templates ? 'New Exam Template' : null"
					@action="openRoute('/app/eduedge-cbt-exam-template/new-eduedge-cbt-exam-template')"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading CBT operations..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error"
				title="CBT operations could not load"
				:message="error"
				action-label="Try again"
				@retry="loadContext"
			/>
			<template v-else>
				<EdgeFilterBar title="Examination ownership">
					<div class="eduedge-cbt-filters">
						<label>
							<span>Examination Scope</span>
							<select v-model="filters.exam_scope" class="form-control" @change="changeScope">
								<option value="School Examination">School Examination</option>
								<option v-if="context.can_manage_public" value="EduEdge Public Examination">
									EduEdge Public Examination
								</option>
							</select>
						</label>
						<label v-if="isSchoolScope">
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="changeBranch">
								<option value="">Select branch</option>
								<option v-for="branch in context.allowed_branches" :key="branch.name" :value="branch.name">
									{{ branch.branch_name || branch.name }}
								</option>
							</select>
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button edge-button--primary" @click="loadContext">Refresh</button>
					</template>
				</EdgeFilterBar>

				<div v-if="isSchoolScope && !filters.branch" class="eduedge-cbt-scope-note">
					Select a School Branch / Campus to view its CBT centres, question bank, and templates.
				</div>

				<EdgeDashboardLayout min-column-width="12rem">
					<EdgeStatCard label="Examination Centres" :value="context.counts.centres || 0" helper="Centres in the selected scope" />
					<EdgeStatCard label="Enabled Centres" :value="context.counts.enabled_centres || 0" helper="Available for future schedules" />
					<EdgeStatCard label="Exam Templates" :value="context.counts.templates || 0" helper="Reusable examination definitions" />
					<EdgeStatCard label="Approved Templates" :value="context.counts.approved_templates || 0" helper="Ready for scheduling" />
					<EdgeStatCard
						v-if="context.can_author_questions"
						label="Approved Questions"
						:value="context.counts.approved_questions || 0"
						helper="Eligible for exam templates"
					/>
				</EdgeDashboardLayout>

				<section class="eduedge-cbt-grid">
					<article class="eduedge-cbt-panel">
						<div class="eduedge-cbt-panel-heading">
							<div>
								<p class="edge-eyebrow">Centre readiness</p>
								<h2>Examination centres</h2>
							</div>
							<button type="button" class="edge-button" @click="openRoute('/app/eduedge-examination-centre')">
								Open all centres
							</button>
						</div>
						<EdgeEmptyState
							v-if="!context.centres.length"
							title="No examination centres found"
							description="Create a centre that matches the selected school or EduEdge public examination scope."
							:action-label="context.can_manage_templates ? 'Create examination centre' : null"
							@action="openRoute('/app/eduedge-examination-centre/new-eduedge-examination-centre')"
						/>
						<div v-else class="eduedge-cbt-list">
							<button
								v-for="centre in context.centres"
								:key="centre.name"
								type="button"
								class="eduedge-cbt-row"
								@click="openRoute(`/app/eduedge-examination-centre/${centre.name}`)"
							>
								<div>
									<strong>{{ centre.centre_name || centre.name }}</strong>
									<span>{{ centre.centre_code }} · {{ centre.location || 'No location' }} · Capacity {{ centre.capacity || 0 }}</span>
								</div>
								<EdgeStatusBadge
									:label="centre.enabled ? 'Enabled' : 'Disabled'"
									:status="centre.enabled ? 'enabled' : 'disabled'"
									:tone="centre.enabled ? 'success' : 'neutral'"
								/>
							</button>
						</div>
					</article>

					<article class="eduedge-cbt-panel">
						<div class="eduedge-cbt-panel-heading">
							<div>
								<p class="edge-eyebrow">Reusable definitions</p>
								<h2>Exam templates</h2>
							</div>
							<button type="button" class="edge-button" @click="openRoute('/app/eduedge-cbt-exam-template')">
								Open all templates
							</button>
						</div>
						<EdgeEmptyState
							v-if="!context.templates.length"
							title="No exam templates found"
							description="Create a reusable exam definition and select only approved questions from the matching bank."
							:action-label="context.can_manage_templates ? 'Create exam template' : null"
							@action="openRoute('/app/eduedge-cbt-exam-template/new-eduedge-cbt-exam-template')"
						/>
						<div v-else class="eduedge-cbt-list">
							<button
								v-for="template in context.templates"
								:key="template.name"
								type="button"
								class="eduedge-cbt-row"
								@click="openRoute(`/app/eduedge-cbt-exam-template/${template.name}`)"
							>
								<div>
									<strong>{{ template.template_title || template.name }}</strong>
									<span>
										{{ template.course }} · {{ template.duration_minutes }} minutes ·
										{{ template.question_count || 0 }} questions · {{ template.total_marks || 0 }} marks
									</span>
								</div>
								<EdgeStatusBadge
									:label="template.status"
									:status="template.status"
									:tone="statusTone(template.status)"
								/>
							</button>
						</div>
					</article>
				</section>

				<section class="eduedge-cbt-grid">
					<article class="eduedge-cbt-panel">
						<div class="eduedge-cbt-panel-heading">
							<div>
								<p class="edge-eyebrow">Question governance</p>
								<h2>Question bank readiness</h2>
							</div>
							<button
								v-if="context.can_author_questions"
								type="button"
								class="edge-button"
								@click="openRoute('/app/eduedge-cbt-question')"
							>
								Open question bank
							</button>
						</div>
						<div v-if="context.can_author_questions" class="eduedge-cbt-readiness">
							<div><span>Approved questions</span><strong>{{ context.counts.approved_questions || 0 }}</strong></div>
							<div><span>Draft or under review</span><strong>{{ context.counts.draft_questions || 0 }}</strong></div>
							<p>
								Only approved questions from the matching ownership scope, branch, and course can be selected in a template.
							</p>
						</div>
						<div v-else class="eduedge-cbt-scope-note">
							Question content and answer governance are restricted to authorised academic staff. Invigilators can view approved exam templates without direct Question Bank access.
						</div>
					</article>

					<article class="eduedge-cbt-panel">
						<div class="eduedge-cbt-panel-heading">
							<div>
								<p class="edge-eyebrow">Next implementation boundary</p>
								<h2>Candidate scheduling and attempts</h2>
							</div>
						</div>
						<div class="eduedge-cbt-roadmap">
							<p>Exam templates are definitions only. They do not yet create candidate attempts or publish results.</p>
							<ul>
								<li>Exam schedule and candidate eligibility</li>
								<li>Server-authoritative timing and one active attempt</li>
								<li>Browser answer saving and pending-sync visibility</li>
								<li>Invigilator monitoring and result approval safety</li>
							</ul>
						</div>
					</article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

export default {
	name: "EduEdgeCBTOperations",
	data() {
		return {
			loading: true,
			error: "",
			menuItems: EDUEDGE_MENU_ITEMS,
			filters: {
				exam_scope: "School Examination",
				branch: "",
			},
			context: {
				user: {},
				current_branch: null,
				allowed_branches: [],
				counts: {},
				centres: [],
				templates: [],
				questions: [],
				can_manage_public: false,
				can_author_questions: false,
				can_manage_templates: false,
			},
		};
	},
	computed: {
		isSchoolScope() {
			return this.filters.exam_scope === "School Examination";
		},
	},
	mounted() {
		this.loadContext();
	},
	methods: {
		openRoute: openEduEdgeRoute,
		statusTone(status) {
			if (status === "Approved") return "success";
			if (status === "Retired") return "neutral";
			if (status === "Under Review") return "warning";
			return "neutral";
		},
		async loadContext() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.cbt.get_cbt_operations_context", {
					exam_scope: this.filters.exam_scope,
					branch: this.filters.branch || undefined,
				});
				this.context = response.message || this.context;
				this.filters = { ...this.filters, ...(this.context.filters || {}) };
			} catch (error) {
				this.error = error?.message || "CBT operations could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		async changeScope() {
			if (!this.isSchoolScope) this.filters.branch = "";
			await this.loadContext();
		},
		async changeBranch() {
			if (!this.filters.branch) {
				await this.loadContext();
				return;
			}
			await frappe.call("eduedge.api.branch_context.switch_school_branch", {
				branch: this.filters.branch,
			});
			await this.loadContext();
		},
	},
};
</script>

<style scoped>
.eduedge-cbt-filters {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
	gap: 1rem;
	width: min(100%, 38rem);
}

.eduedge-cbt-filters label {
	display: grid;
	gap: 0.35rem;
	font-size: 0.82rem;
	font-weight: 600;
	color: var(--edge-text-muted, #64748b);
}

.eduedge-cbt-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(min(100%, 28rem), 1fr));
	gap: 1rem;
	margin-top: 1rem;
}

.eduedge-cbt-panel {
	min-width: 0;
	padding: 1.25rem;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: var(--edge-radius-lg, 0.9rem);
	background: var(--edge-surface, #fff);
	box-shadow: var(--edge-shadow-sm, 0 1px 2px rgba(15, 23, 42, 0.06));
}

.eduedge-cbt-panel-heading {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 1rem;
	margin-bottom: 1rem;
}

.eduedge-cbt-panel-heading h2 {
	margin: 0.2rem 0 0;
	font-size: 1.05rem;
}

.eduedge-cbt-list {
	display: grid;
	gap: 0.65rem;
}

.eduedge-cbt-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 1rem;
	width: 100%;
	padding: 0.85rem;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: var(--edge-radius-md, 0.7rem);
	background: transparent;
	text-align: left;
}

.eduedge-cbt-row:hover {
	border-color: var(--edge-primary, #1f6feb);
	background: var(--edge-primary-soft, #eff6ff);
}

.eduedge-cbt-row div {
	display: grid;
	gap: 0.25rem;
	min-width: 0;
}

.eduedge-cbt-row span,
.eduedge-cbt-readiness p,
.eduedge-cbt-roadmap,
.eduedge-cbt-scope-note {
	color: var(--edge-text-muted, #64748b);
}

.eduedge-cbt-row span {
	overflow: hidden;
	font-size: 0.82rem;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.eduedge-cbt-readiness {
	display: grid;
	gap: 0.75rem;
}

.eduedge-cbt-readiness div {
	display: flex;
	justify-content: space-between;
	gap: 1rem;
	padding-bottom: 0.65rem;
	border-bottom: 1px solid var(--edge-border, #e2e8f0);
}

.eduedge-cbt-scope-note,
.eduedge-cbt-roadmap {
	padding: 1rem;
	border-radius: var(--edge-radius-md, 0.7rem);
	background: var(--edge-surface-subtle, #f8fafc);
}

.eduedge-cbt-scope-note {
	margin-top: 1rem;
}

.eduedge-cbt-roadmap ul {
	margin: 0.75rem 0 0;
	padding-left: 1.1rem;
}

@media (max-width: 640px) {
	.eduedge-cbt-panel-heading,
	.eduedge-cbt-row {
		align-items: stretch;
		flex-direction: column;
	}

	.eduedge-cbt-row span {
		white-space: normal;
	}
}
</style>
