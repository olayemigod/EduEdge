<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="tenantName"
		:branch-name="branchLabel"
		:menu-items="menuItems"
		active-route="/app/eduedge-marks-entry"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Assessments and Results"
					title="Marks Entry"
					subtitle="Enter assessment scores against submitted plans with explicit saves and governed submission."
					action-label="Assessment Plans"
					@action="openRoute('/app/eduedge-assessment-plans')"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loaded" message="Loading marks entry..." :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loaded" title="Marks Entry could not load" :message="error" action-label="Try again" @retry="load" />
			<template v-else>
				<EdgeFilterBar title="Assessment scope">
					<div class="marks-filters">
						<label>
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="changeBranch">
								<option v-for="row in context.allowed_branches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option>
							</select>
						</label>
						<label class="wide">
							<span>Submitted Assessment Plan</span>
							<select v-model="filters.assessment_plan" class="form-control" @change="load">
								<option value="">Select assessment plan</option>
								<option v-for="plan in context.plans" :key="plan.name" :value="plan.name">
									{{ planLabel(plan) }}
								</option>
							</select>
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="load">Refresh</button>
					</template>
				</EdgeFilterBar>

				<p v-if="error" class="marks-error">{{ error }}</p>

				<template v-if="context.selected_plan">
					<EdgeDashboardLayout min-column-width="11rem">
						<EdgeStatCard label="Students" :value="rows.length" helper="Students in the selected class" />
						<EdgeStatCard label="Criteria" :value="context.criteria.length" helper="Required score components" />
						<EdgeStatCard label="Draft Results" :value="draftCount" helper="Can still be edited" />
						<EdgeStatCard label="Submitted Results" :value="submittedCount" helper="Locked from editing" />
						<EdgeStatCard label="Unsaved Rows" :value="dirtyCount" helper="Changes exist only in this browser" />
					</EdgeDashboardLayout>

					<section class="marks-plan-summary">
						<div>
							<p class="edge-eyebrow">Selected assessment</p>
							<h2>{{ context.selected_plan.assessment_name || context.selected_plan.name }}</h2>
							<p>{{ context.selected_plan.course }} · {{ context.selected_plan.student_group }} · {{ context.selected_plan.schedule_date || 'No date' }}</p>
						</div>
						<div class="marks-actions">
							<EdgeStatusBadge label="Submitted plan" status="submitted" tone="success" />
							<button
								v-if="context.permissions.can_submit && draftCount"
								type="button"
								class="edge-button edge-button--primary"
								:disabled="working || dirtyCount > 0"
								@click="submitDrafts"
							>
								Submit Draft Results
							</button>
						</div>
					</section>

					<EdgeEmptyState
						v-if="!rows.length"
						title="No students found"
						description="The selected Assessment Plan has no eligible students in its Student Group."
					/>
					<div v-else class="marks-table-wrap">
						<table class="table marks-table">
							<thead>
								<tr>
									<th>Student</th>
									<th v-for="criterion in context.criteria" :key="criterion.assessment_criteria">
										{{ criterion.assessment_criteria }} / {{ criterion.maximum_score }}
									</th>
									<th>Total</th>
									<th>Grade</th>
									<th>Comment</th>
									<th>Status</th>
									<th>Action</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="row in rows" :key="row.student">
									<td><strong>{{ row.student_name || row.student }}</strong><small>{{ row.student }}</small></td>
									<td v-for="criterion in context.criteria" :key="criterion.assessment_criteria">
										<input
											v-model="row.scores[criterion.assessment_criteria]"
											type="number"
											class="form-control marks-score"
											min="0"
											:step="0.01"
											:max="criterion.maximum_score"
											:disabled="row.docstatus === 1 || working || !canEditResults"
											@input="markDirty(row)"
										/>
										<small v-if="row.grades[criterion.assessment_criteria]">{{ row.grades[criterion.assessment_criteria] }}</small>
									</td>
									<td><strong>{{ rowTotal(row) }}</strong> / {{ context.selected_plan.maximum_assessment_score }}</td>
									<td>{{ row.grade || '—' }}</td>
									<td><input v-model.trim="row.comment" class="form-control" :disabled="row.docstatus === 1 || working || !canEditResults" @input="markDirty(row)" /></td>
									<td>
										<EdgeStatusBadge
											:label="row.docstatus === 1 ? 'Submitted' : row.name ? 'Draft' : 'Not Saved'"
											:status="row.docstatus === 1 ? 'submitted' : row.name ? 'draft' : 'new'"
											:tone="row.docstatus === 1 ? 'success' : 'warning'"
										/>
									</td>
									<td>
										<button
											v-if="row.docstatus !== 1 && canEditResults"
											type="button"
											class="edge-button"
											:disabled="working || !row.dirty || !rowComplete(row)"
											@click="saveRow(row)"
										>
											{{ row.saving ? 'Saving...' : 'Save Row' }}
										</button>
										<button v-if="row.name" type="button" class="edge-button" @click="openResult(row.name)">Open</button>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
					<p class="marks-note">Scores are not sent while you type. Save each changed row explicitly. Submit Draft Results is disabled while unsaved changes remain.</p>
				</template>

				<EdgeEmptyState
					v-else
					title="Select an Assessment Plan"
					description="Choose a submitted Assessment Plan to load its students and scoring criteria."
				/>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

export default {
	name: "EduEdgeMarksEntry",
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS,
			loading: true,
			loaded: false,
			working: false,
			error: "",
			filters: { branch: "", assessment_plan: "" },
			context: { allowed_branches: [], branch: "", plans: [], selected_plan: null, criteria: [], students: [], permissions: {} },
			rows: [],
		};
	},
	computed: {
		tenantName() { return frappe.boot?.eduedge_ui_identity?.tenant_name || ""; },
		branchLabel() {
			const branch = this.context.allowed_branches.find((row) => row.name === this.filters.branch);
			return branch?.branch_name || branch?.name || "";
		},
		canEditResults() { return Boolean(this.context.permissions?.can_create || this.context.permissions?.can_write); },
		draftCount() { return this.rows.filter((row) => row.name && row.docstatus === 0).length; },
		submittedCount() { return this.rows.filter((row) => row.docstatus === 1).length; },
		dirtyCount() { return this.rows.filter((row) => row.dirty).length; },
	},
	mounted() {
		const params = new URLSearchParams(window.location.search || "");
		this.filters.branch = params.get("branch") || "";
		this.filters.assessment_plan = params.get("assessment_plan") || "";
		this.load();
	},
	methods: {
		openRoute: openEduEdgeRoute,
		planLabel(plan) {
			return [plan.assessment_name || plan.name, plan.course, plan.student_group, plan.schedule_date].filter(Boolean).join(" · ");
		},
		normalizeRows(students) {
			return (students || []).map((student) => {
				const details = student.assessment_details || {};
				const scores = {};
				const grades = {};
				for (const criterion of this.context.criteria || []) {
					const value = details[criterion.assessment_criteria];
					scores[criterion.assessment_criteria] = Array.isArray(value) ? value[0] : "";
					grades[criterion.assessment_criteria] = Array.isArray(value) ? value[1] : "";
				}
				const total = Array.isArray(details.total_score) ? details.total_score : ["", ""];
				return {
					student: student.student,
					student_name: student.student_name,
					name: student.name || "",
					docstatus: Number(student.docstatus || 0),
					scores,
					grades,
					grade: total[1] || "",
					comment: details.comment || "",
					dirty: false,
					saving: false,
				};
			});
		},
		async load() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.assessment_workbenches.get_marks_entry_context", {
					branch: this.filters.branch || undefined,
					assessment_plan: this.filters.assessment_plan || undefined,
				});
				this.context = response.message || this.context;
				this.filters.branch = this.context.branch || this.filters.branch;
				if (this.filters.assessment_plan && !this.context.selected_plan) this.filters.assessment_plan = "";
				this.rows = this.normalizeRows(this.context.students);
				this.loaded = true;
			} catch (error) {
				this.error = error?.message || "Marks Entry could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		async changeBranch() {
			this.filters.assessment_plan = "";
			this.rows = [];
			await this.load();
		},
		markDirty(row) { row.dirty = true; },
		rowTotal(row) {
			return (this.context.criteria || []).reduce((total, criterion) => total + Number(row.scores[criterion.assessment_criteria] || 0), 0).toFixed(2);
		},
		rowComplete(row) {
			return (this.context.criteria || []).every((criterion) => {
				const raw = row.scores[criterion.assessment_criteria];
				if (raw === "" || raw === null || raw === undefined) return false;
				const value = Number(raw);
				return Number.isFinite(value) && value >= 0 && value <= Number(criterion.maximum_score);
			});
		},
		async saveRow(row) {
			if (!this.rowComplete(row) || row.docstatus === 1) return;
			row.saving = true;
			this.working = true;
			try {
				const response = await frappe.call("eduedge.api.assessment_workbenches.save_marks_entry", {
					assessment_plan: this.filters.assessment_plan,
					student: row.student,
					scores: JSON.stringify(row.scores),
					comment: row.comment || "",
				});
				const saved = response.message || {};
				row.name = saved.name || row.name;
				row.docstatus = Number(saved.docstatus || 0);
				row.grade = saved.grade || "";
				for (const [criterion, detail] of Object.entries(saved.details || {})) {
					row.grades[criterion] = detail.grade || "";
				}
				row.dirty = false;
				frappe.show_alert({ message: __("Result row saved"), indicator: "green" });
			} catch (error) {
				frappe.msgprint({ title: __("Result could not be saved"), message: error?.message || __("The result row could not be saved."), indicator: "red" });
			} finally {
				row.saving = false;
				this.working = false;
			}
		},
		submitDrafts() {
			if (this.dirtyCount) return;
			frappe.confirm(
				__("Submit all saved Draft Assessment Results for this plan? Submitted results become read-only."),
				async () => {
					this.working = true;
					try {
						const response = await frappe.call("eduedge.api.assessment_workbenches.submit_marks_entry", { assessment_plan: this.filters.assessment_plan });
						frappe.show_alert({ message: __(`${response.message?.submitted || 0} result(s) submitted`), indicator: "green" });
						await this.load();
					} catch (error) {
						frappe.msgprint({ title: __("Results could not be submitted"), message: error?.message || __("The saved results could not be submitted."), indicator: "red" });
					} finally {
						this.working = false;
					}
				}
			);
		},
		openResult(name) {
			window.open(`/app/assessment-result/${encodeURIComponent(name)}`, "_blank", "noopener,noreferrer");
		},
	},
};
</script>

<style scoped>
.marks-filters { display:grid; grid-template-columns:minmax(12rem,.55fr) minmax(20rem,1.45fr); gap:.75rem; width:100%; }
.marks-filters label { display:grid; gap:.35rem; font-weight:600; }
.marks-plan-summary { display:flex; justify-content:space-between; align-items:center; gap:1rem; flex-wrap:wrap; margin-top:1rem; padding:1rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.marks-plan-summary h2 { margin:.2rem 0; }
.marks-plan-summary p { margin:0; color:var(--text-muted); }
.marks-actions { display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; }
.marks-table-wrap { overflow-x:auto; margin-top:1rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.marks-table { min-width:76rem; margin:0; }
.marks-table th { white-space:nowrap; }
.marks-table td { vertical-align:middle; }
.marks-table td:first-child { min-width:13rem; }
.marks-table td:first-child strong,.marks-table td:first-child small { display:block; }
.marks-table td:first-child small,.marks-table td small,.marks-note { color:var(--text-muted); }
.marks-score { min-width:6.25rem; }
.marks-note { margin:.75rem 0 0; }
.marks-error { color:var(--text-color); border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); padding:.75rem; }
@media (max-width:700px) { .marks-filters { grid-template-columns:1fr; } }
</style>
