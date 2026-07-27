<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="identity.tenant_name || ''"
		:branch-name="identity.branch_name || ''"
		:user-name="identity.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-cbt-attempt-review"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Computer-Based Testing"
					title="CBT Attempt Review"
					subtitle="Resolve integrity flags through auditable decisions without changing candidate answers or scoring keys."
					action-label="Refresh"
					@action="refreshAll"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !scheduleContext.schedules.length" message="Loading attempt review queue…" :skeleton="true" />
			<EdgeErrorState
				v-else-if="error && !scheduleContext.schedules.length"
				title="Attempt review could not load"
				:message="error"
				action-label="Try again"
				@retry="initialise"
			/>
			<template v-else>
				<EdgeFilterBar title="Integrity review queue">
					<div class="review-filters">
						<label>
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="changeBranch">
								<option value="">All permitted branches</option>
								<option v-for="branch in scheduleContext.allowed_branches" :key="branch.name" :value="branch.name">
									{{ branch.branch_name || branch.name }}
								</option>
							</select>
						</label>
						<label>
							<span>Examination Schedule</span>
							<select v-model="filters.schedule" class="form-control" @change="loadWorkspace">
								<option value="">All listed schedules</option>
								<option v-for="schedule in scheduleContext.schedules" :key="schedule.name" :value="schedule.name">
									{{ schedule.schedule_title || schedule.name }} · {{ schedule.status }}
								</option>
							</select>
						</label>
						<label>
							<span>Candidate Search</span>
							<input v-model.trim="filters.search" type="search" class="form-control" placeholder="Candidate, student, attempt, or reason">
						</label>
					</div>
				</EdgeFilterBar>

				<EdgeErrorState
					v-if="error"
					title="The review queue could not refresh"
					:message="error"
					action-label="Try again"
					@retry="loadWorkspace"
				/>
				<template v-else>
					<EdgeDashboardLayout min-column-width="12rem">
						<EdgeStatCard label="Review Queue" :value="queue.total || 0" helper="Attempts currently flagged" />
						<EdgeStatCard label="Pending Sync" :value="pendingSyncCount" helper="Cannot be accepted yet" />
						<EdgeStatCard label="Timed Out" :value="timedOutCount" helper="Requires explicit acceptance or disqualification" />
						<EdgeStatCard label="With Interventions" :value="interventionAttemptCount" helper="Has operational intervention evidence" />
						<EdgeStatCard label="Prior Decisions" :value="priorDecisionCount" helper="Append-only review history" />
						<EdgeStatCard label="Result Processing" :value="readiness?.ready_for_result_processing ? 'Ready' : 'Blocked'" helper="Schedule-level readiness" />
					</EdgeDashboardLayout>

					<section v-if="readiness && filters.schedule" class="review-readiness" :class="readiness.ready_for_result_processing ? 'ready' : 'blocked'">
						<div>
							<p class="edge-eyebrow">Schedule result readiness</p>
							<h2>{{ readiness.ready_for_result_processing ? 'Operational blockers are cleared' : 'Result processing remains blocked' }}</h2>
							<p>
								{{ readiness.ready_for_result_processing
									? 'This schedule has no pending sync, open-attempt, missing-attempt, or integrity-review blockers.'
									: 'Resolving a review does not bypass other schedule blockers such as pending answers or missing attempts.' }}
							</p>
						</div>
						<EdgeStatusBadge
							:label="readiness.ready_for_result_processing ? 'Ready' : 'Blocked'"
							:status="readiness.ready_for_result_processing ? 'ready' : 'blocked'"
							:tone="readiness.ready_for_result_processing ? 'success' : 'warning'"
						/>
					</section>

					<section class="review-queue-panel">
						<div class="review-queue-heading">
							<div>
								<p class="edge-eyebrow">Flagged attempts</p>
								<h2>Review evidence and decide</h2>
								<p>Accept for scoring only after pending browser answers are zero. Disqualification cancels the Attempt and marks the Candidate Assignment as Disqualified.</p>
							</div>
							<span>{{ filteredRows.length }} of {{ queue.total || 0 }} shown</span>
						</div>
						<EdgeLoadingState v-if="loadingQueue" message="Loading review evidence…" :skeleton="true" />
						<EdgeEmptyState
							v-else-if="!filteredRows.length"
							title="No flagged attempts match the filters"
							description="The queue is clear, or the selected Branch, Schedule, or search does not match an open review."
						/>
						<div v-else class="review-grid">
							<article v-for="row in filteredRows" :key="row.attempt" class="review-card">
								<header>
									<div>
										<strong>{{ row.candidate_name || row.attempt }}</strong>
										<span>{{ row.student || row.candidate_assignment }} · Attempt {{ row.attempt_number }}</span>
									</div>
									<div class="review-badges">
										<EdgeStatusBadge :label="row.attempt_status" :status="row.attempt_status" :tone="statusTone(row.attempt_status)" />
										<EdgeStatusBadge
											:label="row.reported_pending_sync_count ? `${row.reported_pending_sync_count} Pending` : 'Sync Clear'"
											:status="row.reported_pending_sync_count ? 'pending' : 'clear'"
											:tone="row.reported_pending_sync_count ? 'warning' : 'success'"
										/>
									</div>
								</header>

								<div class="review-metadata">
									<div><span>Attempt</span><button type="button" @click="openAttempt(row)">{{ row.attempt }}</button></div>
									<div><span>Submission Source</span><strong>{{ row.submission_source || '—' }}</strong></div>
									<div><span>Last Sync</span><strong>{{ formatDateTime(row.last_sync_at) }}</strong></div>
									<div><span>Interventions</span><strong>{{ row.intervention_count }}</strong></div>
									<div><span>Prior Decisions</span><strong>{{ row.previous_review_count }}</strong></div>
									<div><span>Result Exists</span><strong>{{ row.result_exists ? 'Yes' : 'No' }}</strong></div>
								</div>

								<section class="evidence-block">
									<h3>Review Reasons</h3>
									<p class="preserve-lines">{{ row.review_reasons || 'No review reason text was recorded.' }}</p>
								</section>

								<details v-if="row.interventions.length" class="evidence-details">
									<summary>{{ row.interventions.length }} Intervention Record(s)</summary>
									<article v-for="intervention in row.interventions" :key="intervention.name">
										<div><strong>{{ intervention.intervention_type }}</strong><span>{{ formatDateTime(intervention.acted_on) }} · {{ intervention.acted_by }}</span></div>
										<p>{{ intervention.reason }}</p>
									</article>
								</details>

								<details v-if="row.previous_reviews.length" class="evidence-details">
									<summary>{{ row.previous_review_count }} Previous Review Decision(s)</summary>
									<article v-for="review in row.previous_reviews" :key="review.name">
										<div><strong>{{ review.decision }}</strong><span>{{ formatDateTime(review.decided_on) }} · {{ review.decided_by }}</span></div>
										<p>{{ review.decision_note }}</p>
									</article>
								</details>

								<div class="review-actions">
									<button
										type="button"
										class="edge-button edge-button--primary"
										:disabled="!row.can_accept || resolvingAttempt === row.attempt"
										:title="acceptDisabledReason(row)"
										@click="promptDecision(row, 'Accept for Scoring')"
									>
										Accept for Scoring
									</button>
									<button
										type="button"
										class="edge-button edge-button--secondary"
										:disabled="resolvingAttempt === row.attempt"
										@click="promptDecision(row, 'Keep Flagged')"
									>
										Keep Flagged
									</button>
									<button
										type="button"
										class="edge-button review-danger-button"
										:disabled="row.result_exists || resolvingAttempt === row.attempt"
										:title="row.result_exists ? 'A result already exists; use a controlled result-cancellation workflow.' : ''"
										@click="promptDecision(row, 'Disqualify Candidate')"
									>
										Disqualify Candidate
									</button>
								</div>
							</article>
						</div>
					</section>
				</template>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

export default {
	name: "EduEdgeCBTAttemptReview",
	data() {
		const identity = frappe.boot?.eduedge_ui_identity || {};
		return {
			identity,
			menuItems: EDUEDGE_MENU_ITEMS,
			loading: true,
			loadingQueue: false,
			error: "",
			resolvingAttempt: "",
			scheduleContext: { allowed_branches: [], schedules: [] },
			queue: { total: 0, rows: [] },
			readiness: null,
			filters: { branch: "", schedule: "", search: "" },
		};
	},
	computed: {
		filteredRows() {
			const search = this.filters.search.toLowerCase();
			if (!search) return this.queue.rows || [];
			return (this.queue.rows || []).filter((row) => {
				const haystack = [
					row.candidate_name,
					row.student,
					row.attempt,
					row.candidate_assignment,
					row.review_reasons,
					row.attempt_status,
				].filter(Boolean).join(" ").toLowerCase();
				return haystack.includes(search);
			});
		},
		pendingSyncCount() {
			return (this.queue.rows || []).filter((row) => row.reported_pending_sync_count).length;
		},
		timedOutCount() {
			return (this.queue.rows || []).filter((row) => row.attempt_status === "Timed Out").length;
		},
		interventionAttemptCount() {
			return (this.queue.rows || []).filter((row) => row.intervention_count).length;
		},
		priorDecisionCount() {
			return (this.queue.rows || []).reduce((total, row) => total + Number(row.previous_review_count || 0), 0);
		},
	},
	mounted() {
		this.initialise();
	},
	methods: {
		openRoute: openEduEdgeRoute,
		async initialise() {
			this.loading = true;
			this.error = "";
			try {
				await this.loadSchedules();
				const active = this.scheduleContext.schedules.find((row) => row.status === "Active");
				const completed = this.scheduleContext.schedules.find((row) => row.status === "Completed");
				this.filters.schedule = active?.name || completed?.name || "";
				await this.loadWorkspace({ quiet: true });
			} catch (error) {
				this.error = error?.message || "CBT Attempt reviews could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		async loadSchedules() {
			const response = await frappe.call("eduedge.cbt.invigilation.get_invigilation_schedules", {
				school_branch: this.filters.branch || undefined,
			});
			this.scheduleContext = response.message || { allowed_branches: [], schedules: [] };
			if (this.filters.schedule && !this.scheduleContext.schedules.some((row) => row.name === this.filters.schedule)) {
				this.filters.schedule = "";
			}
		},
		async changeBranch() {
			this.loading = true;
			this.error = "";
			try {
				await this.loadSchedules();
				const active = this.scheduleContext.schedules.find((row) => row.status === "Active");
				const completed = this.scheduleContext.schedules.find((row) => row.status === "Completed");
				this.filters.schedule = active?.name || completed?.name || "";
				await this.loadWorkspace({ quiet: true });
			} catch (error) {
				this.error = error?.message || "Schedules could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		async loadWorkspace({ quiet = false } = {}) {
			if (!quiet) this.loading = true;
			this.loadingQueue = true;
			this.error = "";
			try {
				const calls = [
					frappe.call("eduedge.cbt.attempt_review.get_attempt_review_queue", {
						exam_schedule: this.filters.schedule || undefined,
						school_branch: this.filters.branch || undefined,
						limit_start: 0,
						limit_page_length: 200,
					}),
				];
				if (this.filters.schedule) {
					calls.push(frappe.call("eduedge.cbt.result_readiness.get_schedule_result_readiness", {
						exam_schedule: this.filters.schedule,
					}));
				}
				const responses = await Promise.all(calls);
				this.queue = responses[0].message || { total: 0, rows: [] };
				this.readiness = responses[1]?.message || null;
			} catch (error) {
				this.error = error?.message || "Attempt review evidence could not be loaded.";
			} finally {
				this.loading = false;
				this.loadingQueue = false;
			}
		},
		async refreshAll() {
			await this.loadSchedules();
			await this.loadWorkspace();
		},
		openAttempt(row) {
			this.openRoute(`/app/eduedge-cbt-attempt/${row.attempt}`);
		},
		statusTone(status) {
			if (["Submitted", "Auto Submitted"].includes(status)) return "success";
			if (["Pending Sync", "Timed Out"].includes(status)) return "warning";
			if (status === "Cancelled") return "danger";
			return "info";
		},
		formatDateTime(value) {
			if (!value) return "—";
			return frappe.datetime?.str_to_user ? frappe.datetime.str_to_user(value) : String(value);
		},
		acceptDisabledReason(row) {
			if (row.result_exists) return "A CBT Result already exists.";
			if (row.reported_pending_sync_count) return "Resolve pending browser answers first.";
			if (!row.can_accept) return "Only Submitted, Auto Submitted, or Timed Out attempts can be accepted.";
			return "";
		},
		promptDecision(row, decision) {
			const descriptions = {
				"Accept for Scoring": "Clears the review flag. A Timed Out attempt becomes Auto Submitted. Candidate answers are not changed.",
				"Keep Flagged": "Records the review decision but leaves the attempt blocked from scoring.",
				"Disqualify Candidate": "Cancels the attempt and marks the Candidate Assignment as Disqualified. This cannot be used after a Result exists.",
			};
			frappe.prompt(
				[
					{
						fieldname: "decision_note",
						fieldtype: "Small Text",
						label: __("Decision Note"),
						reqd: 1,
						description: __(descriptions[decision]),
					},
				],
				(values) => this.resolve(row, decision, values.decision_note),
				__(decision),
				__("Record Decision")
			);
		},
		async resolve(row, decision, note) {
			this.resolvingAttempt = row.attempt;
			try {
				await frappe.call("eduedge.cbt.attempt_review.resolve_attempt_review", {
					attempt_name: row.attempt,
					decision,
					decision_note: note,
				});
				frappe.show_alert({ message: __("Attempt review decision recorded"), indicator: "green" });
				await this.loadWorkspace({ quiet: true });
			} catch (error) {
				frappe.msgprint({
					title: __("Review decision blocked"),
					message: error?.message || String(error),
					indicator: "red",
				});
			} finally {
				this.resolvingAttempt = "";
			}
		},
	},
};
</script>

<style scoped>
.review-filters {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
	gap: 0.9rem;
	width: min(100%, 62rem);
}

.review-filters label {
	display: grid;
	gap: 0.35rem;
	color: var(--edge-text-muted, #64748b);
	font-size: 0.8rem;
	font-weight: 650;
}

.review-readiness,
.review-queue-panel {
	margin-top: 1rem;
	padding: 1rem;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: var(--edge-radius-lg, 0.9rem);
	background: #fff;
}

.review-readiness {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 1rem;
}

.review-readiness.ready {
	border-color: #86efac;
	background: #f0fdf4;
}

.review-readiness.blocked {
	border-color: #fed7aa;
	background: #fffaf0;
}

.review-readiness h2,
.review-queue-heading h2 {
	margin: 0.15rem 0 0.25rem;
	font-size: 1.1rem;
}

.review-readiness p,
.review-queue-heading p,
.review-card header span,
.review-metadata span,
.evidence-details span {
	margin: 0;
	color: var(--edge-text-muted, #64748b);
	font-size: 0.8rem;
}

.review-queue-heading,
.review-card > header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 1rem;
}

.review-grid {
	display: grid;
	gap: 1rem;
	margin-top: 1rem;
}

.review-card {
	padding: 1rem;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: 0.85rem;
	background: #fff;
	box-shadow: var(--edge-shadow-sm, 0 1px 2px rgba(15, 23, 42, 0.06));
}

.review-card header > div:first-child,
.evidence-details article > div {
	display: grid;
	gap: 0.2rem;
}

.review-badges {
	display: flex;
	flex-wrap: wrap;
	justify-content: flex-end;
	gap: 0.45rem;
}

.review-metadata {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
	gap: 0.65rem;
	margin-top: 1rem;
}

.review-metadata > div {
	display: grid;
	gap: 0.2rem;
	padding: 0.7rem;
	border-radius: 0.65rem;
	background: var(--edge-surface-muted, #f8fafc);
}

.review-metadata button {
	width: fit-content;
	padding: 0;
	border: 0;
	background: transparent;
	color: var(--edge-primary, #2563eb);
	font: inherit;
	font-weight: 700;
	cursor: pointer;
}

.evidence-block,
.evidence-details {
	margin-top: 0.85rem;
	padding: 0.8rem;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: 0.7rem;
	background: var(--edge-surface-muted, #f8fafc);
}

.evidence-block h3 {
	margin: 0 0 0.45rem;
	font-size: 0.78rem;
	letter-spacing: 0.03em;
	text-transform: uppercase;
}

.preserve-lines {
	margin: 0;
	white-space: pre-wrap;
}

.evidence-details summary {
	cursor: pointer;
	font-weight: 700;
}

.evidence-details article {
	display: grid;
	gap: 0.45rem;
	margin-top: 0.65rem;
	padding-top: 0.65rem;
	border-top: 1px solid var(--edge-border, #e2e8f0);
}

.evidence-details article p {
	margin: 0;
}

.review-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 0.65rem;
	margin-top: 1rem;
}

.review-danger-button {
	border-color: #fecaca;
	background: #fff;
	color: #b42318;
}

.review-danger-button:hover:not(:disabled) {
	background: #fef2f2;
}

@media (max-width: 720px) {
	.review-readiness,
	.review-queue-heading,
	.review-card > header {
		align-items: stretch;
		flex-direction: column;
	}

	.review-badges {
		justify-content: flex-start;
	}

	.review-actions,
	.review-actions .edge-button {
		width: 100%;
	}
}
</style>
