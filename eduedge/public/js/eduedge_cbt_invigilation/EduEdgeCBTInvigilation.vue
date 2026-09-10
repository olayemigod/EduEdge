<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="identity.tenant_name || ''"
		:branch-name="identity.branch_name || ''"
		:user-name="identity.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-cbt-invigilation"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Computer-Based Testing"
					title="CBT Invigilation"
					subtitle="Monitor candidates, connection health, pending answers, timing, and result-readiness without viewing answer content."
					action-label="Refresh"
					@action="refreshAll"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !context" message="Loading invigilation schedules…" :skeleton="true" />
			<EdgeErrorState
				v-else-if="error && !context"
				title="CBT invigilation could not load"
				:message="error"
				action-label="Try again"
				@retry="initialise"
			/>
			<template v-else>
				<EdgeFilterBar title="Live examination view">
					<div class="invigilation-filters">
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
							<select v-model="filters.schedule" class="form-control" @change="loadContext">
								<option value="">Select schedule</option>
								<option v-for="schedule in scheduleContext.schedules" :key="schedule.name" :value="schedule.name">
									{{ schedule.schedule_title || schedule.name }} · {{ schedule.status }}
								</option>
							</select>
						</label>
						<label>
							<span>Candidate Search</span>
							<input v-model.trim="filters.search" type="search" class="form-control" placeholder="Name, student or assignment">
						</label>
						<label>
							<span>Operational State</span>
							<select v-model="filters.state" class="form-control">
								<option value="">All candidates</option>
								<option value="attention">Needs attention</option>
								<option value="In Progress">In Progress</option>
								<option value="Pending Sync">Pending Sync</option>
								<option value="Submitted">Submitted</option>
								<option value="No Attempt">No Attempt</option>
							</select>
						</label>
					</div>
					<template #actions>
						<div class="invigilation-refresh-state">
							<span>{{ loading ? 'Refreshing…' : `Updated ${lastUpdatedLabel}` }}</span>
							<button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="refreshAll">Refresh</button>
						</div>
					</template>
				</EdgeFilterBar>

				<EdgeEmptyState
					v-if="!filters.schedule"
					title="Select an examination schedule"
					description="Choose a Ready, Active, Suspended, or Completed schedule allowed by your role and Branch access."
				/>
				<EdgeErrorState
					v-else-if="error"
					title="Live candidate status could not refresh"
					:message="error"
					action-label="Try again"
					@retry="loadContext"
				/>
				<template v-else-if="context">
					<section class="invigilation-schedule-panel">
						<div>
							<p class="edge-eyebrow">Selected sitting</p>
							<h2>{{ context.schedule.schedule_title || context.schedule.name }}</h2>
							<p>
								{{ context.schedule.course || 'No course' }} ·
								{{ context.schedule.examination_centre || 'No centre' }} ·
								{{ formatDateTime(context.schedule.scheduled_start) }}
							</p>
						</div>
						<EdgeStatusBadge :label="context.schedule.status" :status="context.schedule.status" :tone="scheduleTone(context.schedule.status)" />
					</section>

					<EdgeDashboardLayout min-column-width="11rem">
						<EdgeStatCard label="Candidates" :value="context.summary.candidate_count || 0" helper="Assignments in this schedule" />
						<EdgeStatCard label="In Progress" :value="context.summary.in_progress_count || 0" helper="Currently active attempts" />
						<EdgeStatCard label="Pending Sync" :value="context.summary.pending_sync_count || 0" helper="Browser answers still unresolved" />
						<EdgeStatCard label="Stale Connections" :value="context.summary.stale_connection_count || 0" helper="No recent heartbeat" />
						<EdgeStatCard label="Submitted" :value="context.summary.submitted_count || 0" helper="Candidate or automatic submission" />
						<EdgeStatCard label="Review Required" :value="context.summary.review_required_count || 0" helper="Integrity review needed" />
					</EdgeDashboardLayout>

					<section class="result-readiness-panel" :class="readinessClass">
						<div class="result-readiness-heading">
							<div>
								<p class="edge-eyebrow">Result governance</p>
								<h2>{{ readinessTitle }}</h2>
								<p>{{ readinessMessage }}</p>
							</div>
							<EdgeStatusBadge
								:label="context.result_readiness.ready_for_result_processing ? 'Operationally Ready' : 'Blocked'"
								:status="context.result_readiness.ready_for_result_processing ? 'ready' : 'blocked'"
								:tone="context.result_readiness.ready_for_result_processing ? 'success' : 'warning'"
							/>
						</div>
						<div v-if="context.result_readiness.operational_blockers.length" class="readiness-blockers">
							<article v-for="blocker in context.result_readiness.operational_blockers" :key="blocker.code">
								<div><strong>{{ blocker.label }}</strong><span>{{ blocker.action }}</span></div>
								<b>{{ blocker.count }}</b>
							</article>
						</div>
						<p v-else class="readiness-clear">
							All current attempts are synchronised and free of unresolved operational review blockers. Scoring and marking still determine final approval readiness.
						</p>
					</section>

					<section class="candidate-monitor-panel">
						<div class="candidate-monitor-heading">
							<div>
								<p class="edge-eyebrow">Live candidates</p>
								<h2>Candidate attempt monitor</h2>
								<p>Connections become stale after {{ context.stale_heartbeat_seconds }} seconds without a heartbeat.</p>
							</div>
							<span>{{ filteredCandidates.length }} shown</span>
						</div>
						<EdgeEmptyState
							v-if="!filteredCandidates.length"
							title="No candidates match the current filters"
							description="Clear the search or state filter, or confirm candidates have been assigned to this schedule."
						/>
						<div v-else class="candidate-table-wrap">
							<table class="candidate-table">
								<thead>
									<tr>
										<th>Candidate</th>
										<th>Attempt</th>
										<th>Connection</th>
										<th>Progress</th>
										<th>Pending</th>
										<th>Time Left</th>
										<th>Review</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="candidate in filteredCandidates" :key="candidate.candidate_assignment" @click="openCandidate(candidate)">
										<td>
											<strong>{{ candidate.candidate_name || candidate.candidate_assignment }}</strong>
											<span>{{ candidate.student || candidate.public_candidate_reference || candidate.candidate_assignment }}</span>
										</td>
										<td><EdgeStatusBadge :label="candidate.attempt_status" :status="candidate.attempt_status" :tone="attemptTone(candidate.attempt_status)" /></td>
										<td>
											<EdgeStatusBadge :label="candidate.connection.label" :status="candidate.connection.code" :tone="candidate.connection.tone" />
											<span>{{ heartbeatLabel(candidate) }}</span>
										</td>
										<td><strong>{{ candidate.answered_count }}/{{ candidate.question_count }}</strong><span>server-saved</span></td>
										<td><strong :class="{ attention: candidate.reported_pending_sync_count }">{{ candidate.reported_pending_sync_count }}</strong></td>
										<td><strong>{{ formatDuration(candidate.seconds_remaining) }}</strong></td>
										<td><EdgeStatusBadge :label="candidate.requires_review ? 'Required' : 'Clear'" :status="candidate.requires_review ? 'required' : 'clear'" :tone="candidate.requires_review ? 'warning' : 'success'" /></td>
									</tr>
								</tbody>
							</table>
						</div>
					</section>
				</template>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const REFRESH_INTERVAL_MS = 15000;

export default {
	name: "EduEdgeCBTInvigilation",
	data() {
		const identity = frappe.boot?.eduedge_ui_identity || {};
		return {
			loading: true,
			error: "",
			identity,
			menuItems: EDUEDGE_MENU_ITEMS,
			scheduleContext: { allowed_branches: [], schedules: [] },
			context: null,
			filters: { branch: identity.branch_name ? "" : "", schedule: "", search: "", state: "" },
			lastUpdated: null,
			refreshTimer: null,
		};
	},
	computed: {
		filteredCandidates() {
			const search = this.filters.search.toLowerCase();
			return (this.context?.candidates || []).filter((candidate) => {
				if (search) {
					const haystack = [
						candidate.candidate_name,
						candidate.student,
						candidate.public_candidate_reference,
						candidate.candidate_assignment,
					].filter(Boolean).join(" ").toLowerCase();
					if (!haystack.includes(search)) return false;
				}
				if (this.filters.state === "attention") {
					return Boolean(
						candidate.requires_review ||
						candidate.reported_pending_sync_count ||
						["STALE", "NO_HEARTBEAT", "TIMED_OUT"].includes(candidate.connection.code)
					);
				}
				if (this.filters.state && candidate.attempt_status !== this.filters.state) return false;
				return true;
			});
		},
		lastUpdatedLabel() {
			return this.lastUpdated ? this.lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "—";
		},
		readinessTitle() {
			return this.context?.result_readiness?.ready_for_result_processing
				? "Attempt operations are ready for result processing"
				: "Result processing is blocked";
		},
		readinessMessage() {
			return this.context?.result_readiness?.ready_for_result_processing
				? "There are no pending browser answers, open attempts, missing attempts, or unresolved integrity reviews."
				: "Resolve every blocker below before scoring, approval, or publication can proceed.";
		},
		readinessClass() {
			return this.context?.result_readiness?.ready_for_result_processing ? "ready" : "blocked";
		},
	},
	mounted() {
		this.initialise();
		this.refreshTimer = window.setInterval(() => {
			if (!document.hidden && this.filters.schedule) this.loadContext({ quiet: true });
		}, REFRESH_INTERVAL_MS);
	},
	beforeUnmount() {
		window.clearInterval(this.refreshTimer);
	},
	methods: {
		openRoute: openEduEdgeRoute,
		async initialise() {
			this.loading = true;
			this.error = "";
			try {
				await this.loadSchedules();
				const active = this.scheduleContext.schedules.find((row) => row.status === "Active");
				if (!this.filters.schedule && active) this.filters.schedule = active.name;
				if (this.filters.schedule) await this.loadContext({ quiet: true });
			} catch (error) {
				this.error = error?.message || "CBT invigilation could not be loaded.";
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
				this.context = null;
			}
		},
		async changeBranch() {
			this.loading = true;
			this.error = "";
			try {
				await this.loadSchedules();
				const active = this.scheduleContext.schedules.find((row) => row.status === "Active");
				if (active) {
					this.filters.schedule = active.name;
					await this.loadContext({ quiet: true });
				}
			} catch (error) {
				this.error = error?.message || "Schedules could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		async loadContext({ quiet = false } = {}) {
			if (!this.filters.schedule) {
				this.context = null;
				return;
			}
			if (!quiet) this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.cbt.invigilation.get_invigilation_context", {
					exam_schedule: this.filters.schedule,
				});
				this.context = response.message || null;
				this.lastUpdated = new Date();
			} catch (error) {
				this.error = error?.message || "Live candidate status could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		async refreshAll() {
			await this.loadSchedules();
			await this.loadContext();
		},
		openCandidate(candidate) {
			if (candidate.attempt) {
				this.openRoute(`/app/eduedge-cbt-attempt/${candidate.attempt}`);
				return;
			}
			this.openRoute(`/app/eduedge-cbt-candidate-assignment/${candidate.candidate_assignment}`);
		},
		formatDateTime(value) {
			if (!value) return "—";
			return frappe.datetime?.str_to_user ? frappe.datetime.str_to_user(value) : String(value);
		},
		formatDuration(seconds) {
			const total = Math.max(0, Number(seconds || 0));
			if (!total) return "—";
			const hours = Math.floor(total / 3600);
			const minutes = Math.floor((total % 3600) / 60);
			const remaining = Math.floor(total % 60);
			return hours
				? `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`
				: `${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
		},
		heartbeatLabel(candidate) {
			if (candidate.heartbeat_age_seconds === null || candidate.heartbeat_age_seconds === undefined) return "No heartbeat received";
			if (candidate.heartbeat_age_seconds < 60) return `${candidate.heartbeat_age_seconds}s ago`;
			return `${Math.floor(candidate.heartbeat_age_seconds / 60)}m ago`;
		},
		scheduleTone(status) {
			if (status === "Active") return "success";
			if (status === "Suspended") return "warning";
			if (status === "Completed") return "neutral";
			return "info";
		},
		attemptTone(status) {
			if (["Submitted", "Auto Submitted", "Scored"].includes(status)) return "success";
			if (["Pending Sync", "Under Review"].includes(status)) return "warning";
			if (["Timed Out", "Cancelled"].includes(status)) return "danger";
			if (status === "In Progress") return "info";
			return "neutral";
		},
	},
};
</script>

<style scoped>
.invigilation-filters {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
	gap: 0.9rem;
	width: min(100%, 64rem);
}

.invigilation-filters label {
	display: grid;
	gap: 0.35rem;
	font-size: 0.8rem;
	font-weight: 650;
	color: var(--edge-text-muted, #64748b);
}

.invigilation-refresh-state {
	display: flex;
	align-items: center;
	gap: 0.75rem;
	color: var(--edge-text-muted, #64748b);
	font-size: 0.78rem;
}

.invigilation-schedule-panel,
.result-readiness-panel,
.candidate-monitor-panel {
	margin-top: 1rem;
	padding: 1.2rem;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: var(--edge-radius-lg, 0.9rem);
	background: var(--edge-surface, #fff);
	box-shadow: var(--edge-shadow-sm, 0 1px 2px rgba(15, 23, 42, 0.06));
}

.invigilation-schedule-panel,
.result-readiness-heading,
.candidate-monitor-heading {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 1rem;
}

.invigilation-schedule-panel h2,
.result-readiness-heading h2,
.candidate-monitor-heading h2 {
	margin: 0.2rem 0 0.25rem;
	font-size: 1.1rem;
}

.invigilation-schedule-panel p,
.result-readiness-heading p,
.candidate-monitor-heading p,
.readiness-blockers span {
	margin: 0;
	color: var(--edge-text-muted, #64748b);
	font-size: 0.82rem;
}

.result-readiness-panel.ready {
	border-color: #86efac;
	background: #f0fdf4;
}

.result-readiness-panel.blocked {
	border-color: #fed7aa;
	background: #fffaf0;
}

.readiness-blockers {
	display: grid;
	gap: 0.65rem;
	margin-top: 1rem;
}

.readiness-blockers article {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 1rem;
	padding: 0.8rem;
	border: 1px solid rgba(180, 83, 9, 0.22);
	border-radius: 0.7rem;
	background: rgba(255, 255, 255, 0.78);
}

.readiness-blockers article > div {
	display: grid;
	gap: 0.25rem;
}

.readiness-blockers b {
	min-width: 2rem;
	font-size: 1.1rem;
	text-align: right;
}

.readiness-clear {
	margin: 1rem 0 0;
	color: #166534;
}

.candidate-monitor-heading > span {
	color: var(--edge-text-muted, #64748b);
	font-size: 0.8rem;
}

.candidate-table-wrap {
	overflow-x: auto;
	margin-top: 1rem;
}

.candidate-table {
	width: 100%;
	min-width: 66rem;
	border-collapse: collapse;
}

.candidate-table th,
.candidate-table td {
	padding: 0.75rem;
	border-bottom: 1px solid var(--edge-border, #e2e8f0);
	text-align: left;
	vertical-align: middle;
}

.candidate-table th {
	color: var(--edge-text-muted, #64748b);
	font-size: 0.72rem;
	font-weight: 750;
	letter-spacing: 0.04em;
	text-transform: uppercase;
}

.candidate-table tbody tr {
	cursor: pointer;
}

.candidate-table tbody tr:hover {
	background: var(--edge-primary-soft, #eff6ff);
}

.candidate-table td {
	font-size: 0.82rem;
}

.candidate-table td:first-child,
.candidate-table td:nth-child(3),
.candidate-table td:nth-child(4) {
	display: table-cell;
}

.candidate-table td strong,
.candidate-table td span {
	display: block;
}

.candidate-table td span {
	margin-top: 0.2rem;
	color: var(--edge-text-muted, #64748b);
	font-size: 0.74rem;
}

.candidate-table .attention {
	color: #b45309;
}

@media (max-width: 720px) {
	.invigilation-schedule-panel,
	.result-readiness-heading,
	.candidate-monitor-heading {
		align-items: stretch;
		flex-direction: column;
	}

	.invigilation-refresh-state {
		width: 100%;
		justify-content: space-between;
	}
}
</style>
