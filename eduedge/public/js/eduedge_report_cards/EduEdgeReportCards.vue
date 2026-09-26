<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="context.tenant_name || ''"
		:branch-name="context.current_branch?.branch_name || ''"
		:user-name="context.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-report-cards"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Published Results"
					title="Report Cards and Progression"
					subtitle="Prepare student report cards, add comments, review progression recommendations, and print only published results."
					:action-label="context.can_review ? 'Prepare Report Cards' : ''"
					@action="prepareReviews"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading report cards..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error"
				title="Report cards could not load"
				:message="error"
				action-label="Try again"
				@retry="loadContext"
			/>
			<template v-else>
				<EdgeFilterBar title="Published result scope">
					<div class="eduedge-report-filters">
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
							<span>Published Results</span>
							<select v-model="filters.publication" class="form-control" @change="changePublication">
								<option value="">Select published result scope</option>
								<option v-for="publication in context.publications" :key="publication.name" :value="publication.name">
									{{ publication.title || publication.name }} · {{ publication.result_mode || 'Terminal' }} · v{{ publication.publication_version || 1 }}
								</option>
							</select>
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" @click="loadContext">Refresh</button>
						<button
							type="button"
							class="edge-button edge-button--primary"
							:disabled="working || !filters.publication || !context.can_review"
							@click="prepareReviews"
						>
							Prepare reviews
						</button>
					</template>
				</EdgeFilterBar>

				<EdgeDashboardLayout min-column-width="12rem">
					<EdgeStatCard label="Students" :value="context.counts.students || 0" helper="Active students in this class" />
					<EdgeStatCard label="Prepared Reviews" :value="context.counts.prepared_reviews || 0" helper="Report-card review records" />
					<EdgeStatCard label="Recommended" :value="context.counts.recommended || 0" helper="Awaiting approval" />
					<EdgeStatCard label="Approved" :value="context.counts.approved || 0" helper="Progression review completed" />
					<EdgeStatCard label="Issued" :value="context.counts.issued || 0" helper="Immutable official report cards" />
				</EdgeDashboardLayout>

				<EdgeEmptyState
					v-if="!filters.publication"
					title="Select published results"
					description="Report cards can only be prepared from a result scope that passed approval and publication."
				/>

				<section v-else class="eduedge-report-grid">
					<article class="eduedge-panel">
						<div class="eduedge-panel-heading">
							<div><p class="edge-eyebrow">Class list</p><h2>Students</h2></div>
						</div>
						<EdgeEmptyState v-if="!context.students.length" title="No students found" description="The published Student Group has no active students." />
						<div v-else class="eduedge-student-list">
							<button
								v-for="row in context.students"
								:key="row.student"
								type="button"
								class="eduedge-student-row"
								:class="{ 'is-active': selectedStudent?.student === row.student }"
								@click="selectStudent(row)"
							>
								<div>
									<strong>{{ row.student_name }}</strong>
									<span>{{ row.student }} · Average {{ formatPercent(row.average_percent) }}<template v-if="row.issue"> · Issue v{{ row.issue.issue_version }}</template></span>
								</div>
								<EdgeStatusBadge :label="row.review?.progression_status || 'Not Prepared'" :status="row.review?.progression_status || 'not-prepared'" :tone="reviewTone(row.review?.progression_status)" />
							</button>
						</div>
					</article>

					<article class="eduedge-panel eduedge-review-panel">
						<EdgeEmptyState v-if="!selectedStudent" title="Select a student" description="Choose a student to review performance, comments, progression, and print the report card." />
						<template v-else>
							<div class="eduedge-panel-heading">
								<div>
									<p class="edge-eyebrow">{{ selectedStudent.result_mode || context.publication?.result_mode || 'Published result' }}</p>
									<h2>{{ selectedStudent.student_name }}</h2>
									<p>
										{{ selectedStudent.student }}
										<span v-if="selectedStudent.group_roll_number"> · Roll {{ selectedStudent.group_roll_number }}</span>
										<span v-if="selectedStudent.publication_version"> · Publication v{{ selectedStudent.publication_version }}</span>
										<span v-if="selectedStudent.issue"> · Issue v{{ selectedStudent.issue.issue_version }}</span>
									</p>
								</div>
								<button type="button" class="edge-button" @click="printReportCard">Print PDF</button>
							</div>

							<div class="eduedge-summary-grid">
								<div><span>Average</span><strong>{{ formatPercent(selectedStudent.average_percent) }}</strong></div>
								<div><span>Grade</span><strong>{{ selectedStudent.overall_grade || '-' }}</strong></div>
								<div><span>Attendance</span><strong>{{ formatPercent(selectedStudent.attendance_percent) }}</strong></div>
								<div><span>Suggested</span><strong>{{ selectedStudent.suggested_progression || 'Pending Review' }}</strong></div>
								<div v-if="selectedStudent.attendance_school_opened !== undefined"><span>School Opened</span><strong>{{ selectedStudent.attendance_school_opened || 0 }}</strong></div>
								<div v-if="selectedStudent.overall_remark"><span>Overall Remark</span><strong>{{ selectedStudent.overall_remark }}</strong></div>
							</div>

							<div v-if="selectedStudent.courses?.length" class="eduedge-result-preview">
								<div class="eduedge-result-preview-heading">
									<div>
										<p class="edge-eyebrow">Published academic snapshot</p>
										<h3>{{ selectedStudent.result_mode === 'Annual' ? 'Annual / cumulative performance' : 'Terminal performance' }}</h3>
									</div>
									<span v-if="selectedStudent.result_profile" class="eduedge-snapshot-note">Immutable published version</span>
								</div>
								<div class="eduedge-result-table-wrap">
									<table class="eduedge-result-table">
										<thead>
											<tr>
												<th>Subject</th>
												<template v-if="selectedStudent.result_mode === 'Annual'">
													<th v-for="period in selectedStudent.periods || []" :key="period.academic_term">{{ period.display_label }}</th>
												</template>
												<template v-else>
													<th v-for="component in selectedStudent.display_components || []" :key="component.component_key">{{ component.component_label }}</th>
												</template>
												<th>Total</th>
												<th>%</th>
												<th>Grade</th>
												<th>Remark</th>
												<th v-for="metric in selectedStudent.display_metrics || []" :key="`${metric.metric_key}-${metric.calculation_basis}-${metric.display_label}`">{{ metric.display_label }}</th>
											</tr>
										</thead>
										<tbody>
											<tr v-for="course in selectedStudent.courses" :key="course.course">
												<td class="is-subject">{{ course.course_name || course.course }}</td>
												<template v-if="selectedStudent.result_mode === 'Annual'">
													<td v-for="period in selectedStudent.periods || []" :key="period.academic_term" class="is-number">
														{{ annualPeriodScore(course, period.academic_term) }}
													</td>
												</template>
												<template v-else>
													<td v-for="component in selectedStudent.display_components || []" :key="component.component_key" class="is-number">
														{{ terminalComponentScore(course, component.component_key) }}
													</td>
												</template>
												<td class="is-number">{{ resultTotal(course) }}</td>
												<td class="is-number">{{ formatPercent(resultPercent(course)) }}</td>
												<td>{{ course.grade || '-' }}</td>
												<td>{{ course.remark || '-' }}</td>
												<td v-for="(metric, index) in selectedStudent.display_metrics || []" :key="`${metric.display_label}-${index}`" class="is-number">
													{{ course.metrics?.[index]?.display_value ?? '-' }}
												</td>
											</tr>
										</tbody>
									</table>
								</div>
							</div>

							<div v-if="history.issues.length || history.publications.length" class="eduedge-history-panel">
								<div class="eduedge-result-preview-heading">
									<div>
										<p class="edge-eyebrow">Audit trail</p>
										<h3>Publication and issue history</h3>
									</div>
									<span v-if="historyLoading" class="eduedge-snapshot-note">Loading…</span>
								</div>
								<div class="eduedge-history-grid">
									<div>
										<strong>Issued report cards</strong>
										<div v-if="!history.issues.length" class="eduedge-history-empty">No official issue yet.</div>
										<div v-for="row in history.issues" :key="row.name" class="eduedge-history-row">
											<span>Issue v{{ row.issue_version }} · Publication v{{ row.publication_version || 1 }}</span>
											<small>{{ formatWhen(row.issued_on) }} · {{ row.fingerprint }}</small>
										</div>
									</div>
									<div>
										<strong>Published result revisions</strong>
										<div v-if="!history.publications.length" class="eduedge-history-empty">No publication history found.</div>
										<div v-for="row in history.publications" :key="row.name" class="eduedge-history-row">
											<span>Publication v{{ row.publication_version || 1 }}</span>
											<small>{{ formatWhen(row.published_on) }} · {{ row.name }}</small>
										</div>
									</div>
								</div>
							</div>

							<div v-if="!selectedStudent.review" class="eduedge-scope-note">Prepare report-card reviews before entering comments or progression recommendations.</div>
							<template v-else>
								<div v-if="!context.can_review" class="eduedge-scope-note">Published results are read-only here. Report-card review editing is limited to the effective Class Teacher, Form Teacher, Head of Class / Level, or an authorized academic administrator.</div>
								<label class="eduedge-field"><span>Class Teacher Comment</span><textarea v-model="editor.class_teacher_comment" class="form-control" rows="4" :disabled="!isDraft || !context.can_review"></textarea></label>
								<label class="eduedge-field"><span>Principal Comment</span><textarea v-model="editor.principal_comment" class="form-control" rows="4" :disabled="!isDraft || !context.can_approve"></textarea></label>
								<label class="eduedge-field">
									<span>Progression Recommendation</span>
									<select v-model="editor.progression_recommendation" class="form-control" :disabled="!isDraft || !context.can_review">
										<option>Pending Review</option><option>Promote</option><option>Repeat</option><option>Graduate</option><option>Transfer</option><option>Not Applicable</option>
									</select>
								</label>
								<div class="eduedge-review-meta">
									<EdgeStatusBadge :label="selectedStudent.review.progression_status" :status="selectedStudent.review.progression_status" :tone="reviewTone(selectedStudent.review.progression_status)" />
									<span v-if="selectedStudent.review.last_review_note">{{ selectedStudent.review.last_review_note }}</span>
								</div>
								<div class="eduedge-review-actions">
									<button v-if="context.can_review && isDraft" type="button" class="edge-button" :disabled="working" @click="saveReview">Save draft</button>
									<button v-if="context.can_review && isDraft" type="button" class="edge-button edge-button--primary" :disabled="working || editor.progression_recommendation === 'Pending Review'" @click="recommendProgression">Recommend</button>
									<button v-if="context.can_approve && selectedStudent.review.progression_status === 'Recommended'" type="button" class="edge-button edge-button--primary" :disabled="working" @click="approveProgression">Approve</button>
									<button v-if="context.can_approve && ['Recommended', 'Approved'].includes(selectedStudent.review.progression_status)" type="button" class="edge-button" :disabled="working" @click="reopenReview">Reopen</button>
									<button
										v-if="canContinueToProgression"
										type="button"
										class="edge-button edge-button--primary"
										@click="continueToProgression"
									>
										Continue to Student Progression
									</button>
								</div>
							</template>
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
	name: "EduEdgeReportCards",
	data() {
		return {
			loading: true,
			working: false,
			error: "",
			menuItems: EDUEDGE_MENU_ITEMS,
			filters: { branch: "", publication: "", student: "" },
			context: { user: {}, current_branch: null, allowed_branches: [], publications: [], publication: null, students: [], counts: {}, can_approve: false, can_review: false },
			selectedStudent: null,
			editor: { class_teacher_comment: "", principal_comment: "", progression_recommendation: "Pending Review" },
			history: { issues: [], publications: [] },
			historyLoading: false,
		};
	},
	computed: {
		isDraft() { return this.selectedStudent?.review?.progression_status === "Draft"; },
		canContinueToProgression() {
			return Boolean(
				this.selectedStudent?.result_mode === "Annual" &&
				this.selectedStudent?.review?.progression_status === "Approved" &&
				["Promote", "Repeat", "Transfer", "Graduate"].includes(this.editor.progression_recommendation) &&
				this.selectedStudent?.source_program
			);
		},
	},
	mounted() { this.loadContext(); },
	methods: {
		openRoute: openEduEdgeRoute,
		formatPercent(value) { return `${Number(value || 0).toFixed(1)}%`; },
		formatWhen(value) {
			if (!value) return "-";
			try { return frappe.datetime.str_to_user(value); } catch (error) { return value; }
		},
		terminalComponentScore(course, key) {
			const component = (course?.display_components || []).find((row) => row.component_key === key);
			if (!component) return "-";
			if (component.display_value !== undefined && component.display_value !== null) return component.display_value;
			if (!Number(component.maximum_score || 0)) return "-";
			return Number(component.score || 0).toFixed(2).replace(/\.00$/, "");
		},
		annualPeriodScore(course, term) {
			const period = course?.period_map?.[term];
			if (!period || !period.eligible) return "-";
			return Number(period.total_score || 0).toFixed(2).replace(/\.00$/, "");
		},
		resultTotal(course) {
			const value = this.selectedStudent?.result_mode === "Annual" ? course?.cumulative_score : course?.total_score;
			return Number(value || 0).toFixed(2).replace(/\.00$/, "");
		},
		resultPercent(course) {
			return this.selectedStudent?.result_mode === "Annual" ? course?.annual_percentage : course?.percentage;
		},
		reviewTone(status) {
			if (status === "Approved") return "success";
			if (status === "Recommended") return "warning";
			if (status === "Draft") return "neutral";
			return "muted";
		},
		async loadContext() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.report_cards.get_report_card_context", {
					branch: this.filters.branch || undefined,
					publication: this.filters.publication || undefined,
					student: this.filters.student || undefined,
				});
				this.context = response.message || this.context;
				this.filters = { ...this.filters, ...(this.context.filters || {}) };
				if (this.filters.student) {
					const row = this.context.students.find((item) => item.student === this.filters.student);
					this.selectStudent(row || null);
				} else if (this.selectedStudent) {
					const row = this.context.students.find((item) => item.student === this.selectedStudent.student);
					this.selectStudent(row || null);
				}
			} catch (error) {
				this.error = error?.message || "Report cards could not be loaded.";
			} finally { this.loading = false; }
		},
		async changeBranch() {
			if (!this.filters.branch) return;
			this.filters.publication = "";
			this.filters.student = "";
			this.selectedStudent = null;
			await frappe.call("eduedge.api.branch_context.switch_school_branch", { branch: this.filters.branch });
			await this.loadContext();
		},
		async changePublication() {
			this.filters.student = "";
			this.selectedStudent = null;
			await this.loadContext();
		},
		selectStudent(row) {
			this.selectedStudent = row;
			this.filters.student = row?.student || "";
			this.history = { issues: [], publications: [] };
			this.editor = {
				class_teacher_comment: row?.review?.class_teacher_comment || "",
				principal_comment: row?.review?.principal_comment || "",
				progression_recommendation: row?.review?.progression_recommendation || row?.suggested_progression || "Pending Review",
			};
			if (row?.student && this.filters.publication) this.loadHistory();
		},
		async loadHistory() {
			if (!this.selectedStudent?.student || !this.filters.publication) return;
			this.historyLoading = true;
			try {
				const response = await frappe.call("eduedge.api.report_cards.get_report_card_history", {
					publication: this.filters.publication,
					student: this.selectedStudent.student,
				});
				this.history = response.message || { issues: [], publications: [] };
			} catch (error) {
				this.history = { issues: [], publications: [] };
			} finally {
				this.historyLoading = false;
			}
		},
		async callAction(method, args = {}) {
			this.working = true;
			try {
				await frappe.call(method, args);
				await this.loadContext();
			} catch (error) {
				frappe.msgprint({ title: __("Report-card action failed"), message: error?.message || __("The requested action could not be completed."), indicator: "red" });
			} finally { this.working = false; }
		},
		prepareReviews() {
			if (!this.filters.publication) return;
			return this.callAction("eduedge.api.report_cards.prepare_report_cards", { publication: this.filters.publication });
		},
		saveReview() {
			return this.callAction("eduedge.api.report_cards.save_report_card_review", {
				review: this.selectedStudent.review.name,
				class_teacher_comment: this.editor.class_teacher_comment,
				principal_comment: this.editor.principal_comment,
				progression_recommendation: this.editor.progression_recommendation,
			});
		},
		async recommendProgression() {
			if (!this.selectedStudent?.review?.name) return;
			this.working = true;
			try {
				await frappe.call("eduedge.api.report_cards.save_report_card_review", {
					review: this.selectedStudent.review.name,
					class_teacher_comment: this.editor.class_teacher_comment,
					principal_comment: this.editor.principal_comment,
					progression_recommendation: this.editor.progression_recommendation,
				});
				await frappe.call("eduedge.api.report_cards.recommend_progression", { review: this.selectedStudent.review.name });
				await this.loadContext();
			} catch (error) {
				frappe.msgprint({ title: __("Progression recommendation failed"), message: error?.message || __("The recommendation could not be submitted."), indicator: "red" });
			} finally { this.working = false; }
		},
		approveProgression() { return this.callAction("eduedge.api.report_cards.approve_progression", { review: this.selectedStudent.review.name }); },
		continueToProgression() {
			if (!this.canContinueToProgression) return;
			const params = new URLSearchParams({
				branch: this.context.publication?.school_branch || this.filters.branch || "",
				academic_year: this.context.publication?.academic_year || "",
				program: this.selectedStudent.source_program || "",
				student_group: this.context.publication?.student_group || "",
				student: this.selectedStudent.student || "",
				outcome: this.editor.progression_recommendation || "",
				result_publication: this.context.publication?.name || "",
			});
			window.location.href = `/app/eduedge-student-progression?${params.toString()}`;
		},
		reopenReview() {
			frappe.prompt(
				[{ fieldname: "reason", fieldtype: "Small Text", label: __("Reopening reason"), reqd: 1 }],
				(values) => this.callAction("eduedge.api.report_cards.reopen_progression_review", { review: this.selectedStudent.review.name, reason: values.reason }),
				__("Reopen progression review"),
				__("Reopen")
			);
		},
		printReportCard() {
			open_url_post("/api/method/eduedge.api.report_cards.preview_report_card", { publication: this.filters.publication, student: this.selectedStudent.student }, true);
		},
	},
};
</script>

<style scoped>
.eduedge-report-filters { display: grid; grid-template-columns: minmax(12rem, 0.7fr) minmax(16rem, 1.3fr); gap: 0.75rem; width: 100%; }
.eduedge-report-filters label, .eduedge-field { display: flex; flex-direction: column; gap: 0.35rem; }
.eduedge-report-filters .form-control, .eduedge-field .form-control {
	background: var(--control-bg);
	color: var(--text-color, inherit);
	border-color: var(--border-color);
	min-height: 2.5rem;
}
.eduedge-report-filters .form-control:focus-visible, .eduedge-field .form-control:focus-visible {
	outline: 2px solid var(--primary);
	outline-offset: 2px;
}
.eduedge-field textarea.form-control { min-height: 6rem; resize: vertical; }
.eduedge-report-filters .form-control:disabled, .eduedge-field .form-control:disabled {
	opacity: 0.7;
	cursor: not-allowed;
}
.eduedge-report-grid { display: grid; grid-template-columns: minmax(18rem, 0.8fr) minmax(0, 1.2fr); gap: 1rem; margin-top: 1rem; }
.eduedge-panel { padding: 1rem; border: 1px solid var(--border-color); border-radius: var(--edge-radius-lg, 12px); background: var(--card-bg); }
.eduedge-panel-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; }
.eduedge-panel-heading h2 { margin: 0.2rem 0 0; }
.eduedge-panel-heading p { margin: 0.2rem 0 0; color: var(--text-muted); }
.eduedge-student-list { display: grid; gap: 0.45rem; max-height: 65vh; overflow: auto; }
.eduedge-student-row { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; width: 100%; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 10px; background: transparent; color: var(--text-color, inherit); text-align: left; }
.eduedge-student-row.is-active { outline: 2px solid var(--primary); outline-offset: 1px; }
.eduedge-student-row:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.eduedge-student-row div { display: grid; gap: 0.2rem; }
.eduedge-student-row span { color: var(--text-muted); }
.eduedge-summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr)); gap: 0.65rem; margin-bottom: 1rem; }
.eduedge-summary-grid div { padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 10px; }
.eduedge-summary-grid span { display: block; color: var(--text-muted); }
.eduedge-summary-grid strong { display: block; margin-top: 0.2rem; font-size: 1.1rem; }
.eduedge-result-preview { margin: 1rem 0; padding-top: 0.85rem; border-top: 1px solid var(--border-color); }
.eduedge-result-preview-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 0.65rem; }
.eduedge-result-preview-heading h3 { margin: 0.15rem 0 0; font-size: 1rem; }
.eduedge-snapshot-note { color: var(--text-muted); font-size: 0.8rem; }
.eduedge-result-table-wrap { overflow-x: auto; border: 1px solid var(--border-color); border-radius: 10px; }
.eduedge-result-table { width: 100%; min-width: 42rem; border-collapse: collapse; color: var(--text-color, inherit); }
.eduedge-result-table th, .eduedge-result-table td { padding: 0.55rem 0.6rem; border-bottom: 1px solid var(--border-color); white-space: nowrap; text-align: left; }
.eduedge-result-table th { background: var(--control-bg); font-size: 0.78rem; }
.eduedge-result-table tr:last-child td { border-bottom: 0; }
.eduedge-result-table .is-subject { font-weight: 600; white-space: normal; min-width: 10rem; }
.eduedge-result-table .is-number { text-align: right; font-variant-numeric: tabular-nums; }
.eduedge-history-panel { margin: 1rem 0; padding-top: 0.85rem; border-top: 1px solid var(--border-color); }
.eduedge-history-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.75rem; }
.eduedge-history-grid > div { padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 10px; background: var(--control-bg); }
.eduedge-history-row { display: grid; gap: 0.12rem; padding: 0.55rem 0; border-bottom: 1px solid var(--border-color); }
.eduedge-history-row:last-child { border-bottom: 0; }
.eduedge-history-row small, .eduedge-history-empty { color: var(--text-muted); overflow-wrap: anywhere; }
.eduedge-history-empty { padding-top: 0.5rem; }
.eduedge-field { margin-top: 0.85rem; }
.eduedge-review-meta { display: flex; align-items: center; gap: 0.65rem; margin-top: 1rem; color: var(--text-muted); }
.eduedge-review-actions { display: flex; flex-wrap: wrap; gap: 0.6rem; margin-top: 1rem; }
.eduedge-scope-note { padding: 0.85rem; border-radius: 10px; background: var(--control-bg); }
@media (max-width: 900px) { .eduedge-report-grid { grid-template-columns: 1fr; } .eduedge-report-filters { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .eduedge-summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .eduedge-history-grid { grid-template-columns: 1fr; } }
</style>
