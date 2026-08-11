<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="selectedBranch?.institution_name || ''"
		:branch-name="selectedBranch?.branch_name || 'Lesson Plans'"
		:menu-items="menuItems"
		active-route="/app/eduedge-lesson-plans"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Teaching Preparation"
					title="Lesson Plans"
					subtitle="Prepare lessons from approved Schemes of Work, exact teaching assignments, and the effective academic period. Submitted and approved history stays auditable."
					:action-label="canCreate ? 'New Lesson Plan' : ''"
					@action="newPlan"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loaded" message="Loading Lesson Plans..." :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loaded" title="Lesson Plans could not load" :message="error" action-label="Try again" @retry="load(true)" />
			<template v-else>
				<EdgeFilterBar title="Teaching context">
					<div class="lesson-filters">
						<label><span>Branch / Campus</span><select v-model="filters.school_branch" class="form-control" @change="branchChanged"><option v-for="row in data.allowed_branches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option></select></label>
						<label><span>Class / Programme Offering</span><select v-model="filters.program_offering" class="form-control" @change="offeringChanged"><option value="">All Classes</option><option v-for="row in data.offerings" :key="row.value" :value="row.value">{{ row.label }} · {{ row.academic_year }}{{ row.academic_term ? ` · ${row.academic_term}` : '' }}</option></select></label>
						<label><span>Class Arm</span><select v-model="filters.student_group" class="form-control" :disabled="!filters.program_offering" @change="groupChanged"><option value="">Class-wide / All Arms</option><option v-for="row in data.groups" :key="row.value" :value="row.value">{{ row.label }}</option></select></label>
						<label><span>Subject / Course</span><select v-model="filters.course" class="form-control" :disabled="!filters.program_offering" @change="courseChanged"><option value="">All Subjects</option><option v-for="row in data.courses" :key="row.value" :value="row.value">{{ row.label }}</option></select></label>
						<label><span>Status</span><select v-model="filters.status" class="form-control" @change="load(true)"><option value="">All Statuses</option><option>Draft</option><option>Submitted</option><option>Approved</option><option>Returned</option></select></label>
						<label><span>Instructor</span><select v-model="filters.instructor" class="form-control" @change="load(true)"><option value="">All permitted Instructors</option><option v-for="row in data.instructors" :key="row.value" :value="row.value">{{ row.label }}</option></select></label>
						<label><span>From</span><input v-model="filters.date_from" type="date" class="form-control" @change="load(true)" /></label>
						<label><span>To</span><input v-model="filters.date_to" type="date" class="form-control" @change="load(true)" /></label>
					</div>
					<template #actions><button type="button" class="edge-button" :disabled="loading" @click="clearHistoryFilters">Clear History Filters</button><button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="load(true)">Apply</button></template>
				</EdgeFilterBar>

				<EdgeActionBar
					v-if="data.permissions?.is_limited_instructor"
					:label="filters.course ? 'Your Lesson Plan access follows your exact Instructor Assignment for this Branch, Class, Class Arm, Subject and date.' : 'Select an assigned Class and Subject to prepare a Lesson Plan.'"
				/>
				<p v-if="error" class="lesson-error">{{ error }}</p>

				<section class="lesson-layout">
					<article class="lesson-panel register">
						<div class="lesson-heading"><div><p class="edge-eyebrow">Teaching preparation history</p><h2>Lesson Plans</h2></div><button v-if="canCreate" type="button" class="edge-button" @click="newPlan">New Lesson Plan</button></div>
						<EdgeLoadingState v-if="loading" message="Refreshing Lesson Plans..." />
						<EdgeEmptyState v-else-if="!data.plans.length" title="No Lesson Plan found" description="Select an approved Scheme item and prepare the first lesson for this teaching context." />
						<div v-else class="lesson-list">
							<button v-for="row in data.plans" :key="row.name" type="button" class="lesson-card" :class="{ 'is-selected': draft.name === row.name }" @click="editPlan(row)">
								<span><strong>{{ row.lesson_plan_title || row.name }}</strong><small>{{ offeringLabel(row.program_offering) }} · {{ courseLabel(row.course) }}{{ row.student_group ? ` · ${groupLabel(row.student_group)}` : '' }}</small><small>{{ row.lesson_date }}{{ row.period_label ? ` · ${row.period_label}` : '' }} · {{ instructorLabel(row.instructor) }}</small></span>
								<EdgeStatusBadge :label="row.status" :status="row.status" :tone="statusTone(row.status)" />
							</button>
						</div>
						<div class="paging"><button type="button" class="edge-button" :disabled="loading || data.paging.start <= 0" @click="previousPage">Previous</button><span>{{ data.paging.start + (data.plans.length ? 1 : 0) }}–{{ data.paging.start + data.plans.length }}</span><button type="button" class="edge-button" :disabled="loading || !data.paging.has_more" @click="nextPage">Next</button></div>
					</article>

					<article class="lesson-panel editor">
						<div class="lesson-heading">
							<div><p class="edge-eyebrow">{{ draft.name ? 'Lesson Plan details' : 'Prepare a lesson' }}</p><h2>{{ draft.lesson_plan_title || (canCreate ? 'New Lesson Plan' : 'Select a Lesson Plan') }}</h2></div>
							<div class="lesson-actions">
								<button v-if="draft.name && draft.can_return" type="button" class="edge-button" :disabled="saving || !reviewReason.trim()" @click="returnPlan">Return for Correction</button>
								<button v-if="draft.name && draft.can_approve" type="button" class="edge-button edge-button--primary" :disabled="saving" @click="approvePlan">Approve</button>
								<button v-if="draft.name && draft.can_submit" type="button" class="edge-button" :disabled="saving" @click="submitPlan">Submit for Review</button>
								<button v-if="canSave" type="button" class="edge-button edge-button--primary" :disabled="saving" @click="savePlan">{{ saving ? 'Saving...' : 'Save Draft' }}</button>
							</div>
						</div>

						<EdgeEmptyState v-if="!draft.name && !canCreate" title="Complete the teaching context" description="Choose Class, Subject, Approved Scheme, Scheme Item, Lesson Date and an eligible Instructor. Options are assignment- and curriculum-aware." />
						<template v-else>
							<div class="context-summary">
								<div><span>Branch</span><strong>{{ branchLabel(draft.school_branch || filters.school_branch) }}</strong></div>
								<div><span>Class</span><strong>{{ offeringLabel(draft.program_offering || filters.program_offering) }}</strong></div>
								<div><span>Class Arm</span><strong>{{ (draft.student_group || filters.student_group) ? groupLabel(draft.student_group || filters.student_group) : 'Class-wide' }}</strong></div>
								<div><span>Subject</span><strong>{{ courseLabel(draft.course || filters.course) }}</strong></div>
								<div><span>Instructor</span><strong>{{ instructorLabel(draft.instructor || filters.instructor) }}</strong></div>
								<div><span>Status</span><strong>{{ draft.status || 'Draft' }}</strong></div>
							</div>

							<div v-if="!draft.name" class="planner-grid">
								<label class="wide"><span>Approved Scheme of Work *</span><select v-model="filters.scheme_of_work" class="form-control" :disabled="!filters.course" @change="schemeChanged"><option value="">Select Approved Scheme</option><option v-for="row in data.schemes" :key="row.value" :value="row.value">{{ row.label }} · Version {{ row.version_no }}</option></select></label>
								<label class="wide"><span>Scheme Item / Topic *</span><select v-model="draft.scheme_item_reference" class="form-control" :disabled="!filters.scheme_of_work" @change="schemeItemChanged"><option value="">Select Scheme Item</option><option v-for="row in data.scheme_items" :key="row.value" :value="row.value">Week {{ row.week_no || '—' }} · {{ row.label }}</option></select></label>
								<label><span>Lesson Date *</span><input v-model="filters.lesson_date" type="date" class="form-control" @change="lessonDateChanged" /></label>
								<label><span>Instructor *</span><select v-model="draft.instructor" class="form-control" :disabled="!filters.lesson_date" @change="instructorChanged"><option value="">Select eligible Instructor</option><option v-for="row in data.instructors" :key="row.value" :value="row.value">{{ row.label }} · {{ row.assignment_title }}</option></select></label>
								<label><span>Period / Slot</span><input v-model.trim="draft.period_label" class="form-control" placeholder="e.g. Period 2" /></label>
								<label><span>Duration (Minutes)</span><input v-model.number="draft.duration_minutes" type="number" min="1" class="form-control" /></label>
							</div>

							<EdgeActionBar v-if="['Submitted','Approved'].includes(draft.status)" :label="draft.status === 'Approved' ? 'Approved Lesson Plans are immutable academic history. Scheme, Class, Subject and Topic labels below are approval snapshots.' : 'Submitted Lesson Plans are read-only until Academic Review approves or returns them.'" />
							<div v-if="draft.status === 'Approved'" class="snapshot-summary"><strong>Approval snapshot</strong><span>{{ draft.course_name_snapshot || courseLabel(draft.course) }} · {{ draft.offering_title_snapshot || offeringLabel(draft.program_offering) }}{{ draft.student_group_name_snapshot ? ` · ${draft.student_group_name_snapshot}` : '' }} · {{ draft.topic_name_snapshot || 'Topic' }}</span><small>Reviewed by {{ draft.reviewed_by || '—' }} on {{ draft.reviewed_on || '—' }}</small></div>
							<div v-if="draft.status === 'Returned' && draft.return_reason" class="return-note"><strong>Returned for correction</strong><span>{{ draft.return_reason }}</span></div>
							<label v-if="draft.can_approve || draft.can_return" class="review-field"><span>Academic Review Comment / Return Reason</span><textarea v-model.trim="reviewReason" class="form-control" rows="3" placeholder="Required when returning; optional on approval"></textarea></label>

							<div class="content-grid">
								<label class="wide"><span>Lesson Objectives *</span><textarea v-model.trim="draft.lesson_objectives" class="form-control" rows="3" :disabled="!editable"></textarea></label>
								<label class="wide"><span>Prior Knowledge / Entry Behaviour</span><textarea v-model.trim="draft.prior_knowledge" class="form-control" rows="2" :disabled="!editable"></textarea></label>
								<label class="wide"><span>Introduction / Starter</span><textarea v-model.trim="draft.introduction" class="form-control" rows="3" :disabled="!editable"></textarea></label>
								<label class="wide"><span>Teaching Methods *</span><textarea v-model.trim="draft.teaching_methods" class="form-control" rows="3" :disabled="!editable"></textarea></label>
								<label class="wide"><span>Teacher Activities</span><textarea v-model.trim="draft.teacher_activities" class="form-control" rows="4" :disabled="!editable"></textarea></label>
								<label class="wide"><span>Learner Activities *</span><textarea v-model.trim="draft.learner_activities" class="form-control" rows="4" :disabled="!editable"></textarea></label>
								<label class="wide"><span>Learning Resources / Materials</span><textarea v-model.trim="draft.learning_resources" class="form-control" rows="3" :disabled="!editable"></textarea></label>
								<label class="wide"><span>Assessment / Evaluation *</span><textarea v-model.trim="draft.formative_assessment" class="form-control" rows="3" :disabled="!editable"></textarea></label>
								<label class="wide"><span>Differentiation / Support Notes</span><textarea v-model.trim="draft.differentiation_notes" class="form-control" rows="3" :disabled="!editable"></textarea></label>
								<label class="wide"><span>Homework / Follow-up</span><textarea v-model.trim="draft.homework" class="form-control" rows="3" :disabled="!editable"></textarea></label>
								<label class="wide"><span>Internal Notes</span><textarea v-model.trim="draft.notes" class="form-control" rows="2" :disabled="!editable"></textarea></label>
							</div>
						</template>
						<p v-if="saveError" class="lesson-error">{{ saveError }}</p>
					</article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const blankData = () => ({
	allowed_branches: [], offerings: [], groups: [], courses: [], schemes: [], scheme_items: [], instructors: [], plans: [],
	filters: {}, paging: { start: 0, page_length: 25, has_more: false }, permissions: {},
});
const blankPlan = (filters = {}) => ({
	name: "", lesson_plan_title: "", status: "Draft", scheme_of_work: filters.scheme_of_work || "", scheme_item_reference: "",
	scheme_version: 0, institution: "", school_branch: filters.school_branch || "", program_offering: filters.program_offering || "",
	student_group: filters.student_group || "", course: filters.course || "", academic_year: "", academic_term: "",
	lesson_date: filters.lesson_date || "", period_label: "", duration_minutes: 40, instructor: filters.instructor || "", instructor_assignment: "",
	lesson_objectives: "", prior_knowledge: "", introduction: "", teaching_methods: "", teacher_activities: "", learner_activities: "",
	learning_resources: "", formative_assessment: "", differentiation_notes: "", homework: "", notes: "",
	prepared_by: "", submitted_by: "", submitted_on: null, reviewed_by: "", reviewed_on: null, review_comment: "", return_reason: "",
	scheme_title_snapshot: "", offering_title_snapshot: "", student_group_name_snapshot: "", course_name_snapshot: "", topic_name_snapshot: "", learning_objective_snapshot: "",
	can_edit: true, can_submit: false, can_approve: false, can_return: false,
});

export default {
	name: "EduEdgeLessonPlans",
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS,
			data: blankData(),
			filters: { school_branch: "", program_offering: "", student_group: "", course: "", scheme_of_work: "", lesson_date: "", instructor: "", status: "", date_from: "", date_to: "", start: 0 },
			draft: blankPlan(), loading: true, loaded: false, saving: false, error: "", saveError: "", reviewReason: "",
		};
	},
	computed: {
		selectedBranch() { return this.data.allowed_branches.find((row) => row.name === this.filters.school_branch) || null; },
		canCreate() { return Boolean(this.data.permissions?.can_create && this.filters.program_offering && this.filters.course && this.filters.scheme_of_work && this.filters.lesson_date && this.data.instructors.length); },
		editable() { return Boolean(!this.draft.name || this.draft.can_edit); },
		canSave() { return Boolean(this.editable && this.draft.scheme_item_reference && (this.draft.lesson_date || this.filters.lesson_date) && this.draft.instructor); },
	},
	mounted() {
		const params = new URLSearchParams(window.location.search || "");
		for (const key of Object.keys(this.filters)) if (params.has(key)) this.filters[key] = params.get(key) || "";
		this.load(true);
	},
	methods: {
		openRoute: openEduEdgeRoute,
		statusTone(status) { return status === "Approved" ? "success" : status === "Submitted" ? "warning" : status === "Returned" ? "danger" : "neutral"; },
		branchLabel(name) { return this.data.allowed_branches.find((row) => row.name === name)?.branch_name || name || "—"; },
		offeringLabel(name) { return this.data.offerings.find((row) => row.value === name)?.label || this.draft.offering_title_snapshot || name || "—"; },
		groupLabel(name) { return this.data.groups.find((row) => row.value === name)?.label || this.draft.student_group_name_snapshot || name || "—"; },
		courseLabel(name) { return this.data.courses.find((row) => row.value === name)?.label || this.draft.course_name_snapshot || name || "—"; },
		instructorLabel(name) { return this.data.instructors.find((row) => row.value === name)?.label || name || "—"; },
		persistFilters() {
			const params = new URLSearchParams();
			for (const [key, value] of Object.entries(this.filters)) if (value && key !== "start") params.set(key, value);
			const query = params.toString();
			window.history.replaceState({}, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
		},
		async load(resetPage = false) {
			if (resetPage) this.filters.start = 0;
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.lesson_plans.get_lesson_plan_workbench", {
					school_branch: this.filters.school_branch || undefined,
					program_offering: this.filters.program_offering || undefined,
					student_group: this.filters.student_group || undefined,
					course: this.filters.course || undefined,
					scheme_of_work: this.filters.scheme_of_work || undefined,
					lesson_date: this.filters.lesson_date || undefined,
					instructor: this.filters.instructor || undefined,
					status: this.filters.status || undefined,
					date_from: this.filters.date_from || undefined,
					date_to: this.filters.date_to || undefined,
					start: this.filters.start || 0,
					page_length: 25,
				});
				this.data = response.message || blankData();
				this.filters.school_branch = this.data.filters?.school_branch || this.filters.school_branch;
				if (this.data.permissions?.exact_instructor && !this.filters.instructor) this.filters.instructor = this.data.permissions.exact_instructor;
				this.persistFilters(); this.loaded = true;
			} catch (error) {
				this.error = error?.message || "Lesson Plans could not be loaded.";
			} finally { this.loading = false; }
		},
		async branchChanged() { this.filters.program_offering = ""; this.filters.student_group = ""; this.filters.course = ""; this.filters.scheme_of_work = ""; this.filters.lesson_date = ""; this.filters.instructor = ""; this.draft = blankPlan(this.filters); await this.load(true); },
		async offeringChanged() { this.filters.student_group = ""; this.filters.course = ""; this.filters.scheme_of_work = ""; this.filters.lesson_date = ""; this.filters.instructor = ""; this.draft = blankPlan(this.filters); await this.load(true); },
		async groupChanged() { this.filters.course = ""; this.filters.scheme_of_work = ""; this.filters.lesson_date = ""; this.filters.instructor = ""; this.draft = blankPlan(this.filters); await this.load(true); },
		async courseChanged() { this.filters.scheme_of_work = ""; this.filters.lesson_date = ""; this.filters.instructor = ""; this.draft = blankPlan(this.filters); await this.load(true); },
		async schemeChanged() { this.draft.scheme_item_reference = ""; this.draft.scheme_of_work = this.filters.scheme_of_work; await this.load(true); },
		schemeItemChanged() {
			const row = this.data.scheme_items.find((item) => item.value === this.draft.scheme_item_reference);
			if (row && !this.draft.lesson_objectives) this.draft.lesson_objectives = row.learning_objective || "";
		},
		async lessonDateChanged() { this.filters.instructor = ""; this.draft.lesson_date = this.filters.lesson_date; this.draft.instructor = ""; await this.load(true); },
		instructorChanged() { this.filters.instructor = this.draft.instructor; },
		clearHistoryFilters() { this.filters.status = ""; this.filters.date_from = ""; this.filters.date_to = ""; this.filters.instructor = this.data.permissions?.exact_instructor || ""; this.load(true); },
		newPlan() {
			if (!this.canCreate) return;
			this.draft = blankPlan(this.filters);
			this.draft.scheme_of_work = this.filters.scheme_of_work;
			this.draft.lesson_date = this.filters.lesson_date;
			if (this.data.permissions?.exact_instructor) this.draft.instructor = this.data.permissions.exact_instructor;
			this.reviewReason = ""; this.saveError = "";
		},
		async editPlan(row) {
			this.saveError = ""; this.reviewReason = "";
			try {
				const response = await frappe.call("eduedge.api.lesson_plans.get_lesson_plan", { name: row.name });
				this.draft = response.message || blankPlan();
			} catch (error) { this.saveError = error?.message || "Lesson Plan could not be opened."; }
		},
		payload() {
			const source = { ...this.draft };
			source.school_branch = this.draft.school_branch || this.filters.school_branch;
			source.program_offering = this.draft.program_offering || this.filters.program_offering;
			source.student_group = this.draft.student_group || this.filters.student_group;
			source.course = this.draft.course || this.filters.course;
			source.scheme_of_work = this.draft.scheme_of_work || this.filters.scheme_of_work;
			source.lesson_date = this.draft.lesson_date || this.filters.lesson_date;
			return source;
		},
		async savePlan() {
			if (!this.canSave) return;
			this.saving = true; this.saveError = "";
			try {
				const response = await frappe.call({ method: "eduedge.api.lesson_plans.save_lesson_plan", type: "POST", args: { payload: JSON.stringify(this.payload()) } });
				this.draft = response.message || this.draft;
				frappe.show_alert({ message: __("Lesson Plan saved"), indicator: "green" });
				await this.load(false);
			} catch (error) { this.saveError = error?.message || "Lesson Plan could not be saved."; }
			finally { this.saving = false; }
		},
		async submitPlan() { if (!this.draft.name) return; await this.workflowAction("eduedge.api.lesson_plans.submit_lesson_plan", { name: this.draft.name }, "Lesson Plan submitted for review"); },
		async approvePlan() { if (!this.draft.name) return; await this.workflowAction("eduedge.api.lesson_plans.approve_lesson_plan", { name: this.draft.name, comment: this.reviewReason }, "Lesson Plan approved"); },
		async returnPlan() { if (!this.draft.name || !this.reviewReason.trim()) return; await this.workflowAction("eduedge.api.lesson_plans.return_lesson_plan", { name: this.draft.name, reason: this.reviewReason }, "Lesson Plan returned for correction"); },
		async workflowAction(method, args, successMessage) {
			this.saving = true; this.saveError = "";
			try {
				const response = await frappe.call({ method, type: "POST", args });
				this.draft = response.message || this.draft; this.reviewReason = "";
				frappe.show_alert({ message: __(successMessage), indicator: "green" });
				await this.load(false);
			} catch (error) { this.saveError = error?.message || "Lesson Plan action failed."; }
			finally { this.saving = false; }
		},
		previousPage() { this.filters.start = Math.max(0, (this.data.paging?.start || 0) - (this.data.paging?.page_length || 25)); this.load(false); },
		nextPage() { if (!this.data.paging?.has_more) return; this.filters.start = (this.data.paging?.start || 0) + (this.data.paging?.page_length || 25); this.load(false); },
	},
};
</script>

<style scoped>
.lesson-filters{display:grid;grid-template-columns:repeat(auto-fit,minmax(13rem,1fr));gap:.75rem}.lesson-filters label,.planner-grid label,.content-grid label,.review-field{display:grid;gap:.35rem;font-weight:600}.lesson-layout{display:grid;grid-template-columns:minmax(18rem,.75fr) minmax(0,1.45fr);gap:1rem;margin-top:1rem}.lesson-panel{display:grid;gap:1rem;align-content:start;padding:1rem;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}.lesson-heading,.lesson-actions,.paging{display:flex;align-items:center;justify-content:space-between;gap:.75rem;flex-wrap:wrap}.lesson-heading h2{margin:.2rem 0 0}.lesson-list{display:grid;gap:.6rem}.lesson-card{display:flex;align-items:center;justify-content:space-between;gap:.75rem;width:100%;padding:.75rem;text-align:left;border:1px solid var(--border-color);border-radius:9px;background:var(--control-bg);color:inherit}.lesson-card.is-selected{outline:2px solid var(--primary)}.lesson-card>span{display:grid;gap:.15rem}.lesson-card small{color:var(--text-muted)}.paging{justify-content:center}.context-summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(10rem,1fr));gap:.65rem}.context-summary>div{display:grid;gap:.2rem;padding:.7rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.context-summary span{font-size:.75rem;color:var(--text-muted)}.planner-grid,.content-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem}.planner-grid .wide,.content-grid .wide{grid-column:1/-1}.snapshot-summary,.return-note{display:grid;gap:.3rem;padding:.8rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.return-note{border-color:var(--red-300,#fda29b)}.snapshot-summary small,.snapshot-summary span{color:var(--text-muted)}.lesson-error{color:var(--red-600,#b42318)}@media(max-width:1000px){.lesson-layout{grid-template-columns:1fr}}@media(max-width:650px){.planner-grid,.content-grid{grid-template-columns:1fr}.planner-grid .wide,.content-grid .wide{grid-column:auto}.lesson-card,.lesson-heading,.lesson-actions{align-items:stretch;flex-direction:column}}
</style>
