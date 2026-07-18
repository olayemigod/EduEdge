<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="context.tenant_name || ''"
		:branch-name="context.current_branch?.branch_name || ''"
		:user-name="context.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-assessment-operations"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Assessment and Results"
					title="Assessment Operations"
					subtitle="Plan assessments, review completeness, approve results, and control report-card publication."
					action-label="New Assessment Plan"
					@action="openRoute('/app/assessment-plan/new-assessment-plan')"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading assessment operations..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error"
				title="Assessment operations could not load"
				:message="error"
				action-label="Try again"
				@retry="loadContext"
			/>
			<template v-else>
				<EdgeFilterBar title="Assessment scope">
					<div class="eduedge-assessment-filters">
						<label>
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="changeBranch">
								<option value="">Select branch</option>
								<option v-for="branch in context.allowed_branches" :key="branch.name" :value="branch.name">
									{{ branch.branch_name || branch.name }}
								</option>
							</select>
						</label>
						<label>
							<span>Academic Year</span>
							<input v-model="filters.academic_year" class="form-control" placeholder="Academic Year" @change="resetScope" />
						</label>
						<label>
							<span>Academic Term</span>
							<input v-model="filters.academic_term" class="form-control" placeholder="Optional term" @change="resetScope" />
						</label>
						<label>
							<span>Student Group / Class</span>
							<select v-model="filters.student_group" class="form-control" @change="loadContext">
								<option value="">All classes</option>
								<option v-for="group in context.student_groups" :key="group.name" :value="group.name">
									{{ group.student_group_name || group.name }}
								</option>
							</select>
						</label>
						<label>
							<span>Assessment Group</span>
							<select v-model="filters.assessment_group" class="form-control" @change="loadContext">
								<option value="">All assessment groups</option>
								<option v-for="group in context.assessment_groups" :key="group.name" :value="group.name">
									{{ group.assessment_group_name || group.name }}
								</option>
							</select>
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button edge-button--primary" @click="loadContext">Refresh</button>
					</template>
				</EdgeFilterBar>

				<EdgeDashboardLayout min-column-width="12rem">
					<EdgeStatCard label="Assessment Plans" :value="context.counts.plans" helper="Plans in the selected scope" />
					<EdgeStatCard label="Submitted Plans" :value="context.counts.submitted_plans" helper="Ready for result entry" />
					<EdgeStatCard label="Expected Results" :value="context.counts.expected_results" helper="Students × submitted plans" />
					<EdgeStatCard label="Submitted Results" :value="context.counts.submitted_results" helper="Final result records" />
					<EdgeStatCard label="Missing Results" :value="context.counts.missing_results" helper="Blocking approval" />
				</EdgeDashboardLayout>

				<section class="eduedge-assessment-grid">
					<article class="eduedge-panel">
						<div class="eduedge-panel-heading">
							<div>
								<p class="edge-eyebrow">Assessment plans</p>
								<h2>Plans and examinations</h2>
							</div>
							<button type="button" class="edge-button" @click="openRoute('/app/assessment-plan')">Open all plans</button>
						</div>
						<EdgeEmptyState
							v-if="!context.plans.length"
							title="No assessment plans found"
							description="Create and submit an Assessment Plan for the selected class and assessment group."
							action-label="Create assessment plan"
							@action="openRoute('/app/assessment-plan/new-assessment-plan')"
						/>
						<div v-else class="eduedge-plan-list">
							<button
								v-for="plan in context.plans"
								:key="plan.name"
								type="button"
								class="eduedge-plan-row"
								@click="openRoute(`/app/assessment-plan/${plan.name}`)"
							>
								<div>
									<strong>{{ plan.assessment_name || plan.course || plan.name }}</strong>
									<span>{{ plan.course }} · {{ plan.student_group }} · {{ plan.schedule_date || 'No date' }}</span>
								</div>
								<EdgeStatusBadge
									:label="plan.docstatus === 1 ? 'Submitted' : plan.docstatus === 2 ? 'Cancelled' : 'Draft'"
									:status="plan.docstatus === 1 ? 'submitted' : plan.docstatus === 2 ? 'cancelled' : 'draft'"
									:tone="plan.docstatus === 1 ? 'success' : plan.docstatus === 2 ? 'danger' : 'warning'"
								/>
							</button>
						</div>
					</article>

					<article class="eduedge-panel">
						<div class="eduedge-panel-heading">
							<div>
								<p class="edge-eyebrow">Approval and publication</p>
								<h2>Result publication control</h2>
							</div>
							<EdgeStatusBadge
								v-if="context.publication"
								:label="context.publication.status"
								:status="context.publication.status"
								:tone="publicationTone"
							/>
						</div>

						<div v-if="!scopeComplete" class="eduedge-scope-note">
							Select a class and assessment group to calculate result completeness and manage publication.
						</div>
						<template v-else>
							<div class="eduedge-readiness-list">
								<div><span>Assessment plans</span><strong>{{ context.readiness?.assessment_plan_count || 0 }}</strong></div>
								<div><span>Students</span><strong>{{ context.readiness?.student_count || 0 }}</strong></div>
								<div><span>Expected results</span><strong>{{ context.readiness?.expected_results || 0 }}</strong></div>
								<div><span>Submitted</span><strong>{{ context.readiness?.submitted_results || 0 }}</strong></div>
								<div><span>Draft</span><strong>{{ context.readiness?.draft_results || 0 }}</strong></div>
								<div><span>Missing</span><strong>{{ context.readiness?.missing_results || 0 }}</strong></div>
							</div>

							<div class="eduedge-publication-actions">
								<button v-if="!context.publication" type="button" class="edge-button edge-button--primary" :disabled="working" @click="ensurePublication">
									Create publication control
								</button>
								<button v-if="context.publication" type="button" class="edge-button" :disabled="working" @click="refreshPublication">
									Refresh completeness
								</button>
								<button
									v-if="['Draft', 'Rejected'].includes(context.publication?.status)"
									type="button"
									class="edge-button edge-button--primary"
									:disabled="working || !context.readiness?.ready"
									@click="requestApproval"
								>
									Request approval
								</button>
								<button
									v-if="context.can_approve && context.publication?.status === 'Pending Approval'"
									type="button"
									class="edge-button edge-button--primary"
									:disabled="working"
									@click="approveResults"
								>
									Approve results
								</button>
								<button
									v-if="context.can_approve && ['Pending Approval', 'Approved'].includes(context.publication?.status)"
									type="button"
									class="edge-button"
									:disabled="working"
									@click="rejectResults"
								>
									Reject
								</button>
								<button
									v-if="context.can_approve && context.publication?.status === 'Approved'"
									type="button"
									class="edge-button edge-button--primary"
									:disabled="working"
									@click="publishResults"
								>
									Publish results
								</button>
							</div>

							<p v-if="context.publication?.status === 'Published'" class="eduedge-success-note">
								Results are published and report-card generation is enabled for this scope.
							</p>
							<p v-else-if="context.publication?.rejection_reason" class="eduedge-danger-note">
								{{ context.publication.rejection_reason }}
							</p>
						</template>
					</article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

export default {
	name: "EduEdgeAssessmentOperations",
	data() {
		return {
			loading: true,
			working: false,
			error: "",
			menuItems: EDUEDGE_MENU_ITEMS,
			filters: {
				branch: "",
				academic_year: "",
				academic_term: "",
				student_group: "",
				assessment_group: "",
			},
			context: {
				user: {},
				current_branch: null,
				allowed_branches: [],
				student_groups: [],
				assessment_groups: [],
				plans: [],
				counts: {},
				publication: null,
				readiness: null,
				can_approve: false,
			},
		};
	},
	computed: {
		scopeComplete() {
			return Boolean(
				this.filters.branch &&
					this.filters.academic_year &&
					this.filters.student_group &&
					this.filters.assessment_group
			);
		},
		publicationTone() {
			const status = this.context.publication?.status;
			if (["Approved", "Published"].includes(status)) return "success";
			if (status === "Rejected") return "danger";
			if (status === "Pending Approval") return "warning";
			return "neutral";
		},
	},
	mounted() {
		this.loadContext();
	},
	methods: {
		openRoute: openEduEdgeRoute,
		async loadContext() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.assessment_operations.get_assessment_context", {
					branch: this.filters.branch || undefined,
					academic_year: this.filters.academic_year || undefined,
					academic_term: this.filters.academic_term || undefined,
					student_group: this.filters.student_group || undefined,
					assessment_group: this.filters.assessment_group || undefined,
				});
				this.context = response.message || this.context;
				this.filters = { ...this.filters, ...(this.context.filters || {}) };
			} catch (error) {
				this.error = error?.message || "Assessment operations could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		async changeBranch() {
			if (!this.filters.branch) return;
			this.filters.student_group = "";
			this.filters.assessment_group = "";
			await frappe.call("eduedge.api.branch_context.switch_school_branch", {
				branch: this.filters.branch,
			});
			await this.loadContext();
		},
		async resetScope() {
			this.filters.student_group = "";
			this.filters.assessment_group = "";
			await this.loadContext();
		},
		async callAction(method, args = {}) {
			this.working = true;
			try {
				await frappe.call(method, args);
				await this.loadContext();
			} catch (error) {
				frappe.msgprint({
					title: __("Assessment action failed"),
					message: error?.message || __("The requested action could not be completed."),
					indicator: "red",
				});
			} finally {
				this.working = false;
			}
		},
		ensurePublication() {
			return this.callAction("eduedge.api.assessment_operations.ensure_result_publication", {
				school_branch: this.filters.branch,
				student_group: this.filters.student_group,
				academic_year: this.filters.academic_year,
				academic_term: this.filters.academic_term || undefined,
				assessment_group: this.filters.assessment_group,
			});
		},
		refreshPublication() {
			return this.callAction("eduedge.api.assessment_operations.refresh_result_publication", {
				publication: this.context.publication.name,
			});
		},
		requestApproval() {
			return this.callAction("eduedge.api.assessment_operations.request_result_approval", {
				publication: this.context.publication.name,
			});
		},
		approveResults() {
			return this.callAction("eduedge.api.assessment_operations.approve_results", {
				publication: this.context.publication.name,
			});
		},
		rejectResults() {
			frappe.prompt(
				[{ fieldname: "reason", fieldtype: "Small Text", label: __("Rejection reason"), reqd: 1 }],
				(values) => this.callAction("eduedge.api.assessment_operations.reject_results", {
					publication: this.context.publication.name,
					reason: values.reason,
				}),
				__("Reject results"),
				__("Reject")
			);
		},
		publishResults() {
			return this.callAction("eduedge.api.assessment_operations.publish_results", {
				publication: this.context.publication.name,
			});
		},
	},
};
</script>

<style scoped>
.eduedge-assessment-filters {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
	gap: 0.75rem;
	width: 100%;
}
.eduedge-assessment-filters label {
	display: flex;
	flex-direction: column;
	gap: 0.35rem;
}
.eduedge-assessment-grid {
	display: grid;
	grid-template-columns: minmax(0, 1.35fr) minmax(18rem, 0.85fr);
	gap: 1rem;
	margin-top: 1rem;
}
.eduedge-panel {
	padding: 1rem;
	border: 1px solid var(--border-color);
	border-radius: var(--edge-radius-lg, 12px);
	background: var(--card-bg);
}
.eduedge-panel-heading {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 1rem;
	margin-bottom: 1rem;
}
.eduedge-panel-heading h2 { margin: 0.2rem 0 0; }
.eduedge-plan-list { display: grid; gap: 0.5rem; }
.eduedge-plan-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 1rem;
	width: 100%;
	padding: 0.8rem;
	border: 1px solid var(--border-color);
	border-radius: 10px;
	background: transparent;
	text-align: left;
}
.eduedge-plan-row div { display: grid; gap: 0.2rem; }
.eduedge-plan-row span { color: var(--text-muted); }
.eduedge-readiness-list { display: grid; gap: 0.55rem; }
.eduedge-readiness-list div {
	display: flex;
	justify-content: space-between;
	gap: 1rem;
	padding-bottom: 0.45rem;
	border-bottom: 1px solid var(--border-color);
}
.eduedge-publication-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 0.6rem;
	margin-top: 1rem;
}
.eduedge-scope-note,
.eduedge-success-note,
.eduedge-danger-note {
	padding: 0.85rem;
	border-radius: 10px;
	background: var(--control-bg);
}
.eduedge-success-note { margin-top: 1rem; }
.eduedge-danger-note { margin-top: 1rem; }
@media (max-width: 900px) {
	.eduedge-assessment-grid { grid-template-columns: 1fr; }
}
</style>
