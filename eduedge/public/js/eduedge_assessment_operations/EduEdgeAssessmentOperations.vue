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
							<span>Result Mode</span>
							<select v-model="filters.result_mode" class="form-control" @change="changeResultMode">
								<option value="Terminal">Terminal</option>
								<option value="Annual">Annual / Cumulative</option>
							</select>
						</label>
						<label v-if="filters.result_mode !== 'Annual'">
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
							<span>Result Profile</span>
							<select v-model="filters.result_profile" class="form-control" @change="changeResultProfile">
								<option value="">Legacy Assessment Group</option>
								<option v-for="profile in context.result_profiles" :key="profile.name" :value="profile.name">
									{{ profile.profile_name || profile.name }}{{ profile.is_default ? ' · Default' : '' }}
								</option>
							</select>
						</label>
						<label v-if="!filters.result_profile && filters.result_mode !== 'Annual'">
							<span>Assessment Group</span>
							<select v-model="filters.assessment_group" class="form-control" @change="loadContext">
								<option value="">Select assessment group</option>
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
					<EdgeStatCard v-if="context.can_view_publication_scope" label="Expected Results" :value="context.counts.expected_results" helper="Students × submitted plans" />
					<EdgeStatCard v-if="context.can_view_publication_scope" label="Submitted Results" :value="context.counts.submitted_results" helper="Final result records" />
					<EdgeStatCard v-if="context.can_view_publication_scope" label="Missing Results" :value="context.counts.missing_results" helper="Blocking approval" />
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

					<article v-if="context.can_view_publication_scope" class="eduedge-panel">
						<div class="eduedge-panel-heading">
							<div>
								<p class="edge-eyebrow">Approval and publication</p>
								<h2>Result publication control</h2>
							</div>
							<EdgeStatusBadge
								v-if="context.publication"
								:label="`${context.publication.status} · v${context.publication.publication_version || 1}`"
								:status="context.publication.status"
								:tone="publicationTone"
							/>
						</div>

						<div v-if="!scopeComplete" class="eduedge-scope-note">
							Select a class and Result Profile. Existing legacy Assessment Group publications remain available for read and history only.
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

							<div class="eduedge-result-scope-summary">
								<div><span>Mode</span><strong>{{ context.publication?.result_mode || filters.result_mode }}</strong></div>
								<div><span>Profile</span><strong>{{ selectedProfileLabel }}</strong></div>
								<div v-if="context.publication"><span>Version</span><strong>v{{ context.publication.publication_version || 1 }}</strong></div>
							</div>

							<div v-if="context.readiness?.profile_blockers?.length" class="eduedge-danger-note">
								<strong>Result publication is blocked</strong>
								<ul>
									<li v-for="(blocker, index) in context.readiness.profile_blockers" :key="index">
										{{ blocker.reason || blocker.code || 'Resolve result configuration before approval.' }}
										<span v-if="blocker.student"> · {{ blocker.student }}</span>
										<span v-if="blocker.course"> · {{ blocker.course }}</span>
									</li>
								</ul>
							</div>
							<div v-if="context.readiness?.unmapped_assessment_groups?.length" class="eduedge-danger-note">
								<strong>Unmapped assessment groups</strong>
								<p>{{ context.readiness.unmapped_assessment_groups.join(', ') }}</p>
							</div>

							<div class="eduedge-publication-actions">
								<button v-if="context.can_manage_publication" type="button" class="edge-button" @click="openRoute('/app/eduedge-result-profile')">
									Manage result profiles
								</button>
								<button v-if="context.can_manage_publication && !context.publication && filters.result_profile" type="button" class="edge-button edge-button--primary" :disabled="working" @click="ensurePublication">
									Create publication control
								</button>
								<button v-if="context.can_manage_publication && context.publication" type="button" class="edge-button" :disabled="working" @click="refreshPublication">
									Refresh completeness
								</button>
								<button
									v-if="context.can_manage_publication && context.publication?.result_profile && ['Draft', 'Rejected'].includes(context.publication?.status)"
									type="button"
									class="edge-button edge-button--primary"
									:disabled="working || !context.readiness?.ready"
									@click="requestApproval"
								>
									Request approval
								</button>
								<button
									v-if="context.can_approve && context.publication?.result_profile && context.publication?.status === 'Pending Approval'"
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
									v-if="context.can_approve && context.publication?.result_profile && context.publication?.status === 'Approved'"
									type="button"
									class="edge-button edge-button--primary"
									:disabled="working"
									@click="publishResults"
								>
									Publish results
								</button>
								<button
									v-if="context.can_approve && context.publication?.result_profile && context.publication?.status === 'Published'"
									type="button"
									class="edge-button"
									:disabled="working"
									@click="createRevision"
								>
									Create correction version
								</button>
							</div>

							<p v-if="isLegacyPublication" class="eduedge-danger-note">
								Legacy Assessment Group publication — read/history only. New approval, publication, and correction versions require a Result Profile.
							</p>
							<p v-else-if="context.publication?.status === 'Published'" class="eduedge-success-note">
								Results are published as immutable version {{ context.publication.publication_version || 1 }}. Corrections require a new publication version.
							</p>
							<p v-else-if="context.publication?.rejection_reason" class="eduedge-danger-note">
								{{ context.publication.rejection_reason }}
							</p>
						</template>
					</article>
					<article v-else class="eduedge-panel">
						<div class="eduedge-panel-heading">
							<div>
								<p class="edge-eyebrow">Approval and publication</p>
								<h2>Class-level result control</h2>
							</div>
						</div>
						<div class="eduedge-scope-note">
							Whole-class readiness and publication are available only to the effective Class/Form responsibility or authorized academic managers.
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
				result_profile: "",
				result_mode: "Terminal",
			},
			context: {
				user: {},
				current_branch: null,
				allowed_branches: [],
				student_groups: [],
				assessment_groups: [],
				result_profiles: [],
				plans: [],
				counts: {},
				publication: null,
				readiness: null,
				can_approve: false,
				can_view_publication_scope: false,
				can_manage_publication: false,
			},
		};
	},
	computed: {
		scopeComplete() {
			const resultScope = this.filters.result_profile || (
				this.context.publication &&
				this.filters.result_mode !== "Annual" &&
				this.filters.assessment_group
			);
			return Boolean(
				this.filters.branch &&
					this.filters.academic_year &&
					this.filters.student_group &&
					resultScope
			);
		},
		isLegacyPublication() {
			return Boolean(this.context.publication && !this.context.publication.result_profile);
		},
		selectedProfileLabel() {
			if (!this.filters.result_profile) {
				return this.isLegacyPublication ? "Legacy Assessment Group · read only" : "Select Result Profile";
			}
			const profile = this.context.result_profiles.find((row) => row.name === this.filters.result_profile);
			return profile?.profile_name || this.filters.result_profile;
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
					result_profile: this.filters.result_profile || undefined,
					result_mode: this.filters.result_mode || "Terminal",
				});
				this.context = response.message || this.context;
				this.filters = { ...this.filters, ...(this.context.filters || {}) };
				if (this.filters.result_mode === "Annual") this.filters.academic_term = "";
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
			this.filters.result_profile = "";
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
		async changeResultMode() {
			this.filters.student_group = "";
			this.filters.assessment_group = "";
			if (this.filters.result_mode === "Annual") {
				this.filters.academic_term = "";
				if (!this.filters.result_profile) {
					const preferred = this.context.result_profiles.find((row) => row.is_default) || this.context.result_profiles[0];
					this.filters.result_profile = preferred?.name || "";
				}
			}
			await this.loadContext();
		},
		async changeResultProfile() {
			this.filters.student_group = "";
			if (this.filters.result_profile) this.filters.assessment_group = "";
			if (!this.filters.result_profile && this.filters.result_mode === "Annual") {
				this.filters.result_mode = "Terminal";
			}
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
				assessment_group: this.filters.assessment_group || undefined,
				result_profile: this.filters.result_profile || undefined,
				result_mode: this.filters.result_mode || "Terminal",
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
		createRevision() {
			frappe.confirm(
				__("Create a new correction version? The published version will remain unchanged."),
				() => this.callAction("eduedge.api.assessment_operations.create_result_publication_revision", {
					publication: this.context.publication.name,
				})
			);
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
.eduedge-result-scope-summary {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
	gap: 0.55rem;
	margin-top: 0.9rem;
}
.eduedge-result-scope-summary div {
	padding: 0.65rem;
	border: 1px solid var(--border-color);
	border-radius: 10px;
}
.eduedge-result-scope-summary span {
	display: block;
	color: var(--text-muted);
	margin-bottom: 0.2rem;
}
.eduedge-danger-note ul { margin: 0.5rem 0 0; padding-left: 1.2rem; }
.eduedge-danger-note p { margin: 0.45rem 0 0; }
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
