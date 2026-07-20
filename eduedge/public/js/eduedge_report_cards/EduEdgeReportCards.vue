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
					action-label="Prepare Report Cards"
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
									{{ publication.title || publication.name }}
								</option>
							</select>
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" @click="loadContext">Refresh</button>
						<button
							type="button"
							class="edge-button edge-button--primary"
							:disabled="working || !filters.publication"
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
								<div><strong>{{ row.student_name }}</strong><span>{{ row.student }} · Average {{ formatPercent(row.average_percent) }}</span></div>
								<EdgeStatusBadge :label="row.review?.progression_status || 'Not Prepared'" :status="row.review?.progression_status || 'not-prepared'" :tone="reviewTone(row.review?.progression_status)" />
							</button>
						</div>
					</article>

					<article class="eduedge-panel eduedge-review-panel">
						<EdgeEmptyState v-if="!selectedStudent" title="Select a student" description="Choose a student to review performance, comments, progression, and print the report card." />
						<template v-else>
							<div class="eduedge-panel-heading">
								<div><p class="edge-eyebrow">Student report card</p><h2>{{ selectedStudent.student_name }}</h2><p>{{ selectedStudent.student }}</p></div>
								<button type="button" class="edge-button" @click="printReportCard">Print PDF</button>
							</div>

							<div class="eduedge-summary-grid">
								<div><span>Average</span><strong>{{ formatPercent(selectedStudent.average_percent) }}</strong></div>
								<div><span>Grade</span><strong>{{ selectedStudent.overall_grade || '-' }}</strong></div>
								<div><span>Attendance</span><strong>{{ formatPercent(selectedStudent.attendance_percent) }}</strong></div>
								<div><span>Suggested</span><strong>{{ selectedStudent.suggested_progression || 'Pending Review' }}</strong></div>
							</div>

							<div v-if="!selectedStudent.review" class="eduedge-scope-note">Prepare report-card reviews before entering comments or progression recommendations.</div>
							<template v-else>
								<label class="eduedge-field"><span>Class Teacher Comment</span><textarea v-model="editor.class_teacher_comment" class="form-control" rows="4" :disabled="!isDraft"></textarea></label>
								<label class="eduedge-field"><span>Principal Comment</span><textarea v-model="editor.principal_comment" class="form-control" rows="4" :disabled="!isDraft || !context.can_approve"></textarea></label>
								<label class="eduedge-field">
									<span>Progression Recommendation</span>
									<select v-model="editor.progression_recommendation" class="form-control" :disabled="!isDraft">
										<option>Pending Review</option><option>Promote</option><option>Repeat</option><option>Graduate</option><option>Transfer</option><option>Not Applicable</option>
									</select>
								</label>
								<div class="eduedge-review-meta">
									<EdgeStatusBadge :label="selectedStudent.review.progression_status" :status="selectedStudent.review.progression_status" :tone="reviewTone(selectedStudent.review.progression_status)" />
									<span v-if="selectedStudent.review.last_review_note">{{ selectedStudent.review.last_review_note }}</span>
								</div>
								<div class="eduedge-review-actions">
									<button v-if="isDraft" type="button" class="edge-button" :disabled="working" @click="saveReview">Save draft</button>
									<button v-if="isDraft" type="button" class="edge-button edge-button--primary" :disabled="working || editor.progression_recommendation === 'Pending Review'" @click="recommendProgression">Recommend</button>
									<button v-if="context.can_approve && selectedStudent.review.progression_status === 'Recommended'" type="button" class="edge-button edge-button--primary" :disabled="working" @click="approveProgression">Approve</button>
									<button v-if="context.can_approve && ['Recommended', 'Approved'].includes(selectedStudent.review.progression_status)" type="button" class="edge-button" :disabled="working" @click="reopenReview">Reopen</button>
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
			context: { user: {}, current_branch: null, allowed_branches: [], publications: [], publication: null, students: [], counts: {}, can_approve: false },
			selectedStudent: null,
			editor: { class_teacher_comment: "", principal_comment: "", progression_recommendation: "Pending Review" },
		};
	},
	computed: {
		isDraft() { return this.selectedStudent?.review?.progression_status === "Draft"; },
	},
	mounted() { this.loadContext(); },
	methods: {
		openRoute: openEduEdgeRoute,
		formatPercent(value) { return `${Number(value || 0).toFixed(1)}%`; },
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
			this.editor = {
				class_teacher_comment: row?.review?.class_teacher_comment || "",
				principal_comment: row?.review?.principal_comment || "",
				progression_recommendation: row?.review?.progression_recommendation || row?.suggested_progression || "Pending Review",
			};
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
.eduedge-report-grid { display: grid; grid-template-columns: minmax(18rem, 0.8fr) minmax(0, 1.2fr); gap: 1rem; margin-top: 1rem; }
.eduedge-panel { padding: 1rem; border: 1px solid var(--border-color); border-radius: var(--edge-radius-lg, 12px); background: var(--card-bg); }
.eduedge-panel-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; }
.eduedge-panel-heading h2 { margin: 0.2rem 0 0; }
.eduedge-panel-heading p { margin: 0.2rem 0 0; color: var(--text-muted); }
.eduedge-student-list { display: grid; gap: 0.45rem; max-height: 65vh; overflow: auto; }
.eduedge-student-row { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; width: 100%; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 10px; background: transparent; text-align: left; }
.eduedge-student-row.is-active { outline: 2px solid var(--primary); }
.eduedge-student-row div { display: grid; gap: 0.2rem; }
.eduedge-student-row span { color: var(--text-muted); }
.eduedge-summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.65rem; margin-bottom: 1rem; }
.eduedge-summary-grid div { padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 10px; }
.eduedge-summary-grid span { display: block; color: var(--text-muted); }
.eduedge-summary-grid strong { display: block; margin-top: 0.2rem; font-size: 1.1rem; }
.eduedge-field { margin-top: 0.85rem; }
.eduedge-review-meta { display: flex; align-items: center; gap: 0.65rem; margin-top: 1rem; color: var(--text-muted); }
.eduedge-review-actions { display: flex; flex-wrap: wrap; gap: 0.6rem; margin-top: 1rem; }
.eduedge-scope-note { padding: 0.85rem; border-radius: 10px; background: var(--control-bg); }
@media (max-width: 900px) { .eduedge-report-grid { grid-template-columns: 1fr; } .eduedge-report-filters { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .eduedge-summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
