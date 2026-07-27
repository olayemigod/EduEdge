<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="identity.tenant_name || ''"
		:branch-name="identity.branch_name || ''"
		:user-name="identity.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-cbt-marking"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Computer-Based Testing"
					title="CBT Scoring and Marking"
					subtitle="Auto-score objective responses, mark written answers, review readiness, and approve results without publishing them."
					action-label="Refresh"
					@action="refreshAll"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !scheduleContext.schedules.length" message="Loading CBT scoring workspace…" :skeleton="true" />
			<EdgeErrorState
				v-else-if="error && !scheduleContext.schedules.length"
				title="CBT scoring could not load"
				:message="error"
				action-label="Try again"
				@retry="initialise"
			/>
			<template v-else>
				<EdgeFilterBar title="Result workbench">
					<div class="marking-filters">
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
								<option value="">Select schedule</option>
								<option v-for="schedule in scheduleContext.schedules" :key="schedule.name" :value="schedule.name">
									{{ schedule.schedule_title || schedule.name }} · {{ schedule.status }}
								</option>
							</select>
						</label>
						<label>
							<span>Candidate Search</span>
							<input v-model.trim="filters.search" type="search" class="form-control" placeholder="Candidate, student, or question code">
						</label>
					</div>
					<template #actions>
						<div class="marking-actions">
							<button
								v-if="canApprove"
								type="button"
								class="edge-button edge-button--secondary"
								:disabled="!filters.schedule || scoring || loading"
								@click="scoreSchedule"
							>
								{{ scoring ? 'Scoring…' : 'Score Submitted Attempts' }}
							</button>
							<button
								v-if="canApprove"
								type="button"
								class="edge-button edge-button--primary"
								:disabled="!readyForApproval || approving"
								@click="approveSchedule"
							>
								{{ approving ? 'Approving…' : 'Approve Schedule Results' }}
							</button>
						</div>
					</template>
				</EdgeFilterBar>

				<EdgeEmptyState
					v-if="!filters.schedule"
					title="Select an examination schedule"
					description="Choose a schedule, run objective scoring, and complete any manual marking queue."
				/>
				<EdgeErrorState
					v-else-if="error"
					title="The scoring workspace could not refresh"
					:message="error"
					action-label="Try again"
					@retry="loadWorkspace"
				/>
				<template v-else>
					<section v-if="lastScoringMessage" class="scoring-message" :class="lastScoringTone">
						{{ lastScoringMessage }}
					</section>

					<EdgeDashboardLayout v-if="readiness" min-column-width="12rem">
						<EdgeStatCard label="Candidate Assignments" :value="readiness.candidate_assignment_count || 0" helper="Active assignments in schedule" />
						<EdgeStatCard label="Latest Attempts" :value="readiness.latest_attempt_count || 0" helper="Latest non-cancelled attempts" />
						<EdgeStatCard label="Manual Queue" :value="queue.total || 0" helper="Written responses awaiting marks" />
						<EdgeStatCard label="Pending Sync" :value="readiness.pending_sync_count || 0" helper="Browser answers unresolved" />
						<EdgeStatCard label="Review Required" :value="readiness.review_required_count || 0" helper="Integrity review blockers" />
						<EdgeStatCard label="Approval" :value="readyForApproval ? 'Ready' : 'Blocked'" helper="Server-authoritative result gate" />
					</EdgeDashboardLayout>

					<section v-if="readiness" class="approval-panel" :class="readyForApproval ? 'ready' : 'blocked'">
						<div class="approval-heading">
							<div>
								<p class="edge-eyebrow">Approval gate</p>
								<h2>{{ readyForApproval ? 'Results are ready for approval' : 'Result approval is blocked' }}</h2>
								<p>
									{{ readyForApproval
										? 'Every relevant attempt is scored and there are no pending sync or integrity-review blockers.'
										: 'Complete the actions below. Approval remains server-blocked even if the button is called outside this page.' }}
								</p>
							</div>
							<EdgeStatusBadge
								:label="readyForApproval ? 'Ready' : 'Blocked'"
								:status="readyForApproval ? 'ready' : 'blocked'"
								:tone="readyForApproval ? 'success' : 'warning'"
							/>
						</div>
						<div v-if="!readyForApproval" class="approval-blockers">
							<article v-for="blocker in readiness.approval_blockers || []" :key="blocker.code">
								<div><strong>{{ blocker.label }}</strong><span>{{ blocker.action }}</span></div>
								<b>{{ blocker.count }}</b>
							</article>
						</div>
					</section>

					<section class="manual-queue-panel">
						<div class="manual-queue-heading">
							<div>
								<p class="edge-eyebrow">Manual marking</p>
								<h2>Written-response queue</h2>
								<p>Only questions still marked <strong>Manual Required</strong> are shown. Each saved mark creates an append-only audit log.</p>
							</div>
							<span>{{ filteredRows.length }} of {{ queue.total || 0 }} shown</span>
						</div>
						<EdgeLoadingState v-if="loadingQueue" message="Loading manual responses…" :skeleton="true" />
						<EdgeEmptyState
							v-else-if="!filteredRows.length"
							title="No manual responses are waiting"
							description="Run objective scoring first, clear the candidate search, or select another schedule."
						/>
						<div v-else class="marking-grid">
							<article v-for="row in filteredRows" :key="rowKey(row)" class="marking-card">
								<header>
									<div>
										<strong>{{ row.candidate_name || row.result }}</strong>
										<span>{{ row.question_code || row.question_snapshot_key }} · {{ row.question_type }}</span>
									</div>
									<EdgeStatusBadge label="Manual Required" status="manual-required" tone="warning" />
								</header>
								<section class="question-block">
									<h3>Question</h3>
									<div class="rich-content" v-html="safeHtml(row.question_text)"></div>
								</section>
								<div class="marking-reference-grid">
									<section>
										<h3>Candidate Answer</h3>
										<pre>{{ candidateAnswer(row) }}</pre>
									</section>
									<section>
										<h3>Answer Key</h3>
										<p>{{ row.answer_key || 'No short answer key supplied.' }}</p>
										<h3>Marking Guide</h3>
										<p class="preserve-lines">{{ row.marking_guide || 'No marking guide supplied.' }}</p>
									</section>
								</div>
								<div class="mark-entry">
									<label>
										<span>Awarded Mark (maximum {{ row.available_mark }})</span>
										<input
											v-model.number="drafts[rowKey(row)].mark"
											type="number"
											class="form-control"
											min="0"
											:step="markStep(row.available_mark)"
											:max="row.available_mark"
										>
									</label>
									<label>
										<span>Marker Comment</span>
										<textarea v-model.trim="drafts[rowKey(row)].comment" class="form-control" rows="3" placeholder="Optional note for first marking; required for a later correction."></textarea>
									</label>
									<button
										type="button"
										class="edge-button edge-button--primary"
										:disabled="savingKey === rowKey(row)"
										@click="saveMark(row)"
									>
										{{ savingKey === rowKey(row) ? 'Saving…' : 'Save Mark' }}
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

const APPROVER_ROLES = new Set([
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
]);

export default {
	name: "EduEdgeCBTMarking",
	data() {
		const identity = frappe.boot?.eduedge_ui_identity || {};
		return {
			identity,
			menuItems: EDUEDGE_MENU_ITEMS,
			loading: true,
			loadingQueue: false,
			scoring: false,
			approving: false,
			savingKey: "",
			error: "",
			lastScoringMessage: "",
			lastScoringTone: "",
			scheduleContext: { allowed_branches: [], schedules: [] },
			readiness: null,
			queue: { total: 0, rows: [] },
			drafts: {},
			filters: { branch: "", schedule: "", search: "" },
		};
	},
	computed: {
		canApprove() {
			if (frappe.session.user === "Administrator") return true;
			const roles = frappe.boot?.user?.roles || frappe.user_roles || [];
			return roles.some((role) => APPROVER_ROLES.has(role));
		},
		readyForApproval() {
			return Boolean(this.readiness?.ready_for_result_approval);
		},
		filteredRows() {
			const search = this.filters.search.toLowerCase();
			if (!search) return this.queue.rows || [];
			return (this.queue.rows || []).filter((row) => {
				const haystack = [
					row.candidate_name,
					row.student,
					row.question_code,
					row.question_type,
					row.result,
				].filter(Boolean).join(" ").toLowerCase();
				return haystack.includes(search);
			});
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
				this.filters.schedule = completed?.name || active?.name || "";
				if (this.filters.schedule) await this.loadWorkspace({ quiet: true });
			} catch (error) {
				this.error = error?.message || "CBT scoring could not be loaded.";
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
				this.readiness = null;
				this.queue = { total: 0, rows: [] };
			}
		},
		async changeBranch() {
			this.loading = true;
			this.error = "";
			try {
				await this.loadSchedules();
				const completed = this.scheduleContext.schedules.find((row) => row.status === "Completed");
				const active = this.scheduleContext.schedules.find((row) => row.status === "Active");
				this.filters.schedule = completed?.name || active?.name || "";
				if (this.filters.schedule) await this.loadWorkspace({ quiet: true });
			} catch (error) {
				this.error = error?.message || "Schedules could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		async loadWorkspace({ quiet = false } = {}) {
			if (!this.filters.schedule) {
				this.readiness = null;
				this.queue = { total: 0, rows: [] };
				return;
			}
			if (!quiet) this.loading = true;
			this.loadingQueue = true;
			this.error = "";
			try {
				const [readinessResponse, queueResponse] = await Promise.all([
					frappe.call("eduedge.cbt.result_readiness.get_schedule_result_readiness", {
						exam_schedule: this.filters.schedule,
					}),
					frappe.call("eduedge.cbt.scoring.get_manual_marking_queue", {
						exam_schedule: this.filters.schedule,
						limit_start: 0,
						limit_page_length: 200,
					}),
				]);
				this.readiness = readinessResponse.message || null;
				this.queue = queueResponse.message || { total: 0, rows: [] };
				this.seedDrafts();
			} catch (error) {
				this.error = error?.message || "Scoring data could not be loaded.";
			} finally {
				this.loading = false;
				this.loadingQueue = false;
			}
		},
		async refreshAll() {
			await this.loadSchedules();
			await this.loadWorkspace();
		},
		seedDrafts() {
			const next = {};
			for (const row of this.queue.rows || []) {
				const key = this.rowKey(row);
				next[key] = this.drafts[key] || { mark: Number(row.awarded_mark || 0), comment: row.marker_comment || "" };
			}
			this.drafts = next;
		},
		rowKey(row) {
			return `${row.result}::${row.question_snapshot_key}`;
		},
		markStep(maximum) {
			return Number(maximum || 0) % 1 ? 0.1 : 1;
		},
		candidateAnswer(row) {
			const answer = row.candidate_answer || {};
			if (Object.prototype.hasOwnProperty.call(answer, "text")) return answer.text || "No written answer submitted.";
			if (Object.prototype.hasOwnProperty.call(answer, "value")) return String(answer.value ?? "No numeric answer submitted.");
			return JSON.stringify(answer, null, 2) || "No answer submitted.";
		},
		safeHtml(value) {
			const raw = String(value || "");
			if (frappe.utils?.sanitize_html) return frappe.utils.sanitize_html(raw);
			return frappe.utils.escape_html(raw).replace(/\n/g, "<br>");
		},
		async scoreSchedule() {
			if (!this.filters.schedule || !this.canApprove) return;
			this.scoring = true;
			this.lastScoringMessage = "";
			try {
				const response = await frappe.call("eduedge.cbt.scoring.score_schedule_objective", {
					exam_schedule: this.filters.schedule,
				});
				const result = response.message || { scored: [], skipped: [] };
				this.lastScoringMessage = `${result.scored.length} attempt(s) scored or already available; ${result.skipped.length} skipped.`;
				this.lastScoringTone = result.skipped.length ? "warning" : "success";
				await this.loadWorkspace({ quiet: true });
			} catch (error) {
				this.lastScoringMessage = error?.message || "Objective scoring failed.";
				this.lastScoringTone = "danger";
			} finally {
				this.scoring = false;
			}
		},
		async saveMark(row) {
			const key = this.rowKey(row);
			const draft = this.drafts[key];
			if (!draft) return;
			const mark = Number(draft.mark);
			if (!Number.isFinite(mark) || mark < 0 || mark > Number(row.available_mark || 0)) {
				frappe.msgprint({
					title: __("Invalid mark"),
					message: __("Enter a mark between 0 and {0}.", [row.available_mark]),
					indicator: "orange",
				});
				return;
			}
			this.savingKey = key;
			try {
				await frappe.call("eduedge.cbt.scoring.apply_manual_mark", {
					result_name: row.result,
					question_snapshot_key: row.question_snapshot_key,
					awarded_mark: mark,
					marker_comment: draft.comment || "",
				});
				frappe.show_alert({ message: __("Manual mark saved"), indicator: "green" });
				await this.loadWorkspace({ quiet: true });
			} catch (error) {
				frappe.msgprint({
					title: __("Mark could not be saved"),
					message: error?.message || String(error),
					indicator: "red",
				});
			} finally {
				this.savingKey = "";
			}
		},
		approveSchedule() {
			if (!this.filters.schedule || !this.canApprove || !this.readyForApproval) return;
			frappe.prompt(
				[
					{
						fieldname: "approval_note",
						fieldtype: "Small Text",
						label: __("Approval Note"),
						description: __("Optional schedule-level approval note. Approval does not publish or create Frappe Assessment Results."),
					},
				],
				async (values) => {
					this.approving = true;
					try {
						const response = await frappe.call("eduedge.cbt.scoring.approve_schedule_results", {
							exam_schedule: this.filters.schedule,
							approval_note: values.approval_note || "",
						});
						frappe.msgprint({
							title: __("CBT results approved"),
							message: __("{0} CBT result(s) were approved. Publication remains a separate governed step.", [response.message?.approved_count || 0]),
							indicator: "green",
						});
						await this.loadWorkspace({ quiet: true });
					} catch (error) {
						frappe.msgprint({
							title: __("Approval blocked"),
							message: error?.message || String(error),
							indicator: "red",
						});
					} finally {
						this.approving = false;
					}
				},
				__("Approve CBT Schedule Results"),
				__("Approve Results")
			);
		},
	},
};
</script>

<style scoped>
.marking-filters {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
	gap: 0.9rem;
	width: min(100%, 58rem);
}

.marking-filters label,
.mark-entry label {
	display: grid;
	gap: 0.35rem;
	color: var(--edge-text-muted, #64748b);
	font-size: 0.8rem;
	font-weight: 650;
}

.marking-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 0.65rem;
}

.scoring-message,
.approval-panel,
.manual-queue-panel {
	margin-top: 1rem;
	padding: 1rem;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: var(--edge-radius-lg, 0.9rem);
	background: var(--edge-surface, #fff);
}

.scoring-message.success {
	border-color: #86efac;
	background: #f0fdf4;
	color: #166534;
}

.scoring-message.warning {
	border-color: #fed7aa;
	background: #fff7ed;
	color: #9a3412;
}

.scoring-message.danger {
	border-color: #fecaca;
	background: #fef2f2;
	color: #991b1b;
}

.approval-panel.ready {
	border-color: #86efac;
	background: #f0fdf4;
}

.approval-panel.blocked {
	border-color: #fed7aa;
	background: #fffaf0;
}

.approval-heading,
.manual-queue-heading,
.marking-card > header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 1rem;
}

.approval-heading h2,
.manual-queue-heading h2 {
	margin: 0.15rem 0 0.25rem;
	font-size: 1.1rem;
}

.approval-heading p,
.manual-queue-heading p,
.marking-card header span {
	margin: 0;
	color: var(--edge-text-muted, #64748b);
	font-size: 0.82rem;
}

.approval-blockers {
	display: grid;
	gap: 0.65rem;
	margin-top: 1rem;
}

.approval-blockers article {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 1rem;
	padding: 0.75rem;
	border: 1px solid rgba(180, 83, 9, 0.22);
	border-radius: 0.7rem;
	background: rgba(255, 255, 255, 0.8);
}

.approval-blockers article > div,
.marking-card header > div {
	display: grid;
	gap: 0.2rem;
}

.approval-blockers span {
	color: var(--edge-text-muted, #64748b);
	font-size: 0.78rem;
}

.marking-grid {
	display: grid;
	gap: 1rem;
	margin-top: 1rem;
}

.marking-card {
	padding: 1rem;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: 0.8rem;
	background: #fff;
	box-shadow: var(--edge-shadow-sm, 0 1px 2px rgba(15, 23, 42, 0.06));
}

.question-block,
.marking-reference-grid section {
	margin-top: 1rem;
	padding: 0.9rem;
	border-radius: 0.7rem;
	background: var(--edge-surface-muted, #f8fafc);
}

.question-block h3,
.marking-reference-grid h3 {
	margin: 0 0 0.5rem;
	font-size: 0.8rem;
	letter-spacing: 0.03em;
	text-transform: uppercase;
}

.rich-content,
.marking-reference-grid p,
.marking-reference-grid pre {
	margin: 0;
	font-family: inherit;
	font-size: 0.9rem;
	line-height: 1.6;
	white-space: pre-wrap;
}

.marking-reference-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 0.85rem;
}

.preserve-lines {
	white-space: pre-wrap;
}

.mark-entry {
	display: grid;
	grid-template-columns: minmax(10rem, 0.4fr) minmax(16rem, 1fr) auto;
	align-items: end;
	gap: 0.85rem;
	margin-top: 1rem;
}

.mark-entry textarea {
	resize: vertical;
}

@media (max-width: 800px) {
	.approval-heading,
	.manual-queue-heading,
	.marking-card > header {
		align-items: stretch;
		flex-direction: column;
	}

	.marking-reference-grid,
	.mark-entry {
		grid-template-columns: 1fr;
	}
}
</style>
