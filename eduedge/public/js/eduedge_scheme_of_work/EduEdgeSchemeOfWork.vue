<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="selectedBranch?.institution_name || ''"
		:branch-name="selectedBranch?.branch_name || 'Scheme of Work'"
		:menu-items="menuItems"
		active-route="/app/eduedge-schemes-of-work"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Curriculum Delivery"
					title="Scheme of Work"
					subtitle="Plan term curriculum against the exact Branch, Class, Class Arm and Subject responsibility. Approved versions retain readable curriculum snapshots."
					:action-label="canCreate ? 'New Scheme' : ''"
					@action="newScheme"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loaded" message="Loading Scheme of Work..." :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loaded" title="Scheme of Work could not load" :message="error" action-label="Try again" @retry="load(true)" />
			<template v-else>
				<EdgeFilterBar title="Academic context">
					<div class="scheme-filters">
						<label><span>Branch / Campus</span><select v-model="filters.school_branch" class="form-control" @change="branchChanged"><option v-for="row in data.allowed_branches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option></select></label>
						<label><span>Class / Programme Offering</span><select v-model="filters.program_offering" class="form-control" @change="offeringChanged"><option value="">All Classes</option><option v-for="row in data.offerings" :key="row.value" :value="row.value">{{ row.label }} · {{ row.academic_year }}{{ row.academic_term ? ` · ${row.academic_term}` : '' }}</option></select></label>
						<label><span>Class Arm</span><select v-model="filters.student_group" class="form-control" :disabled="!filters.program_offering" @change="groupChanged"><option value="">Class-wide / All Arms</option><option v-for="row in data.groups" :key="row.value" :value="row.value">{{ row.label }}</option></select></label>
						<label><span>Subject / Course</span><select v-model="filters.course" class="form-control" :disabled="!filters.program_offering" @change="courseChanged"><option value="">All Subjects</option><option v-for="row in data.courses" :key="row.value" :value="row.value">{{ row.label }}</option></select></label>
						<label><span>Status</span><select v-model="filters.status" class="form-control" @change="load(true)"><option value="">All Statuses</option><option>Draft</option><option>Approved</option><option>Retired</option></select></label>
					</div>
					<template #actions><button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="load(true)">Apply</button></template>
				</EdgeFilterBar>

				<EdgeActionBar
					v-if="data.permissions?.is_limited_instructor"
					:label="filters.course ? 'Your Scheme access is derived from your exact Instructor Assignment for this academic context.' : 'Select an assigned Class and Subject to prepare a Scheme of Work.'"
				/>
				<p v-if="error" class="scheme-error">{{ error }}</p>

				<section class="scheme-layout">
					<article class="scheme-panel register">
						<div class="scheme-heading"><div><p class="edge-eyebrow">Curriculum history</p><h2>Schemes</h2></div><button v-if="canCreate" type="button" class="edge-button" @click="newScheme">New Scheme</button></div>
						<EdgeLoadingState v-if="loading" message="Refreshing Schemes..." />
						<EdgeEmptyState v-else-if="!data.schemes.length" title="No Scheme of Work found" description="Select an academic context and prepare the first Scheme for this Subject." />
						<div v-else class="scheme-list">
							<button v-for="row in data.schemes" :key="row.name" type="button" class="scheme-card" :class="{ 'is-selected': draft.name === row.name }" @click="editScheme(row)">
								<span><strong>{{ row.scheme_title || row.name }}</strong><small>{{ offeringLabel(row.program_offering) }} · {{ courseLabel(row.course) }}{{ row.student_group ? ` · ${groupLabel(row.student_group)}` : '' }}</small><small>{{ row.academic_year }}{{ row.academic_term ? ` · ${row.academic_term}` : '' }} · Version {{ row.version_no }}</small></span>
								<EdgeStatusBadge :label="row.status" :status="row.status" :tone="statusTone(row.status)" />
							</button>
						</div>
						<div class="paging"><button type="button" class="edge-button" :disabled="loading || data.paging.start <= 0" @click="previousPage">Previous</button><span>{{ data.paging.start + (data.schemes.length ? 1 : 0) }}–{{ data.paging.start + data.schemes.length }}</span><button type="button" class="edge-button" :disabled="loading || !data.paging.has_more" @click="nextPage">Next</button></div>
					</article>

					<article class="scheme-panel editor">
						<div class="scheme-heading">
							<div><p class="edge-eyebrow">{{ draft.name ? 'Scheme details' : 'New Scheme' }}</p><h2>{{ draft.scheme_title || (canCreate ? 'Prepare Scheme of Work' : 'Select a Scheme') }}</h2></div>
							<div class="scheme-actions">
								<button v-if="draft.name && draft.status === 'Approved' && data.permissions?.is_manager" type="button" class="edge-button" :disabled="saving" @click="createVersion">Create New Version</button>
								<button v-if="draft.name && draft.status === 'Approved' && data.permissions?.is_manager" type="button" class="edge-button" :disabled="saving" @click="retire">Retire</button>
								<button v-if="draft.name && draft.status === 'Draft' && data.permissions?.is_manager" type="button" class="edge-button" :disabled="saving || !draft.items.length" @click="approve">Approve</button>
								<button v-if="canSave" type="button" class="edge-button edge-button--primary" :disabled="saving" @click="save">{{ saving ? 'Saving...' : 'Save Draft' }}</button>
							</div>
						</div>

						<EdgeEmptyState v-if="!draft.name && !canCreate" title="Select a Scheme or complete the filters" description="Choose Branch, Class and Subject. Instructor options remain limited to the exact assignment context." />
						<template v-else>
							<div class="context-summary">
								<div><span>Branch</span><strong>{{ branchLabel(draft.school_branch) }}</strong></div>
								<div><span>Class</span><strong>{{ offeringLabel(draft.program_offering) }}</strong></div>
								<div><span>Class Arm</span><strong>{{ draft.student_group ? groupLabel(draft.student_group) : 'Class-wide' }}</strong></div>
								<div><span>Subject</span><strong>{{ courseLabel(draft.course) }}</strong></div>
								<div><span>Academic Period</span><strong>{{ draft.period_start_date || selectedOffering?.period_start_date || '—' }} → {{ draft.period_end_date || selectedOffering?.period_end_date || '—' }}</strong></div>
								<div><span>Version</span><strong>{{ draft.version_no || 1 }} · {{ draft.status || 'Draft' }}</strong></div>
							</div>

							<EdgeActionBar v-if="draft.status === 'Approved'" label="Approved curriculum is immutable. Topic names and descriptions below are frozen approval snapshots; create a new version for changes." />
							<div v-if="draft.status === 'Approved' || draft.status === 'Retired'" class="snapshot-summary">
								<strong>Approval snapshot</strong>
								<span>{{ draft.course_name_snapshot || courseLabel(draft.course) }} · {{ draft.offering_title_snapshot || offeringLabel(draft.program_offering) }}{{ draft.student_group_name_snapshot ? ` · ${draft.student_group_name_snapshot}` : '' }}</span>
								<small>Approved by {{ draft.approved_by || '—' }} on {{ draft.approved_on || '—' }}</small>
							</div>

							<div class="scheme-heading item-heading"><div><p class="edge-eyebrow">Planned delivery</p><h3>Scheme Items</h3></div><button v-if="editable" type="button" class="edge-button" @click="addItem">Add Topic</button></div>
							<EdgeEmptyState v-if="!draft.items.length" title="No curriculum delivery items" description="Add Topics in the order they should be taught during the academic period." />
							<div v-else class="scheme-items">
								<article v-for="(row,index) in draft.items" :key="row.name || index" class="scheme-item">
									<div class="item-grid">
										<label><span>Sequence</span><input v-model.number="row.sequence" type="number" min="1" class="form-control" :disabled="!editable" /></label>
										<label><span>Week</span><input v-model.number="row.week_no" type="number" min="1" class="form-control" :disabled="!editable" /></label>
										<label class="topic-field"><span>Topic *</span><select v-if="editable" v-model="row.topic" class="form-control"><option value="">Select Topic</option><option v-for="topic in data.topics" :key="topic.value" :value="topic.value">{{ topic.label }} · {{ topic.scope }}</option></select><strong v-else>{{ row.topic_name_snapshot || topicLabel(row.topic) }}</strong></label>
										<label><span>Estimated Periods</span><input v-model.number="row.estimated_periods" type="number" min="1" class="form-control" :disabled="!editable" /></label>
										<label><span>Planned Start</span><input v-model="row.planned_start_date" type="date" class="form-control" :disabled="!editable" /></label>
										<label><span>Planned End</span><input v-model="row.planned_end_date" type="date" class="form-control" :disabled="!editable" /></label>
										<label class="wide"><span>Learning Objective</span><textarea v-model.trim="row.learning_objective" class="form-control" rows="2" :disabled="!editable"></textarea></label>
										<label class="wide"><span>Notes</span><textarea v-model.trim="row.notes" class="form-control" rows="2" :disabled="!editable"></textarea></label>
									</div>
									<div v-if="!editable && row.topic_description_snapshot" class="topic-snapshot"><small>{{ row.topic_description_snapshot }}</small></div>
									<button v-if="editable" type="button" class="edge-button remove" @click="removeItem(index)">Remove</button>
								</article>
							</div>
							<label class="notes"><span>Internal Notes</span><textarea v-model.trim="draft.notes" class="form-control" rows="3" :disabled="!editable"></textarea></label>
							<SchemeDeliveryPanel
								v-if="draft.name && ['Approved', 'Retired'].includes(draft.status)"
								:scheme="draft"
								:is-manager="Boolean(data.permissions?.is_manager)"
							/>
						</template>
						<p v-if="saveError" class="scheme-error">{{ saveError }}</p>
					</article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";
import SchemeDeliveryPanel from "../eduedge_ui/components/SchemeDeliveryPanel.vue";

const blankData = () => ({
	allowed_branches: [], offerings: [], groups: [], courses: [], topics: [], schemes: [],
	filters: {}, paging: { start: 0, page_length: 25, has_more: false }, permissions: {},
});
const blankScheme = (filters = {}, offering = null) => ({
	name: "", scheme_title: "", status: "Draft", version_no: 1, supersedes_scheme: "",
	institution: offering?.institution || "", school_branch: filters.school_branch || "",
	program_offering: filters.program_offering || "", student_group: filters.student_group || "", course: filters.course || "",
	academic_year: offering?.academic_year || "", academic_term: offering?.academic_term || "",
	period_start_date: offering?.period_start_date || "", period_end_date: offering?.period_end_date || "",
	prepared_by: "", approved_by: "", approved_on: null, snapshot_on: null,
	offering_title_snapshot: "", student_group_name_snapshot: "", course_name_snapshot: "", notes: "", items: [],
});

export default {
	name: "EduEdgeSchemeOfWork",
	components: { SchemeDeliveryPanel },
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS, data: blankData(), filters: { school_branch: "", program_offering: "", student_group: "", course: "", status: "", start: 0 },
			draft: blankScheme(), loading: true, loaded: false, saving: false, error: "", saveError: "",
		};
	},
	computed: {
		selectedBranch() { return this.data.allowed_branches.find((row) => row.name === this.filters.school_branch) || null; },
		selectedOffering() { return this.data.offerings.find((row) => row.value === this.filters.program_offering) || null; },
		selectedCourse() { return this.data.courses.find((row) => row.value === this.filters.course) || null; },
		canCreate() { return Boolean(this.data.permissions?.can_create_in_context && this.filters.program_offering && this.filters.course); },
		editable() { return Boolean((!this.draft.name || this.draft.status === "Draft") && (this.canCreate || this.data.permissions?.is_manager)); },
		canSave() { return Boolean(this.editable && this.draft.program_offering && this.draft.course); },
	},
	mounted() { this.load(); },
	methods: {
		openRoute: openEduEdgeRoute,
		statusTone(status) { return status === "Approved" ? "success" : status === "Retired" ? "neutral" : "warning"; },
		branchLabel(name) { return this.data.allowed_branches.find((row) => row.name === name)?.branch_name || name || "—"; },
		offeringLabel(name) { return this.data.offerings.find((row) => row.value === name)?.label || this.draft.offering_title_snapshot || name || "—"; },
		groupLabel(name) { return this.data.groups.find((row) => row.value === name)?.label || this.draft.student_group_name_snapshot || name || "—"; },
		courseLabel(name) { return this.data.courses.find((row) => row.value === name)?.label || this.draft.course_name_snapshot || name || "—"; },
		topicLabel(name) { return this.data.topics.find((row) => row.value === name)?.label || name || "—"; },
		async load(reset = false, selectedName = "") {
			if (reset) this.filters.start = 0;
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.scheme_of_work_workbench.get_scheme_workbench", {
					school_branch: this.filters.school_branch || undefined,
					program_offering: this.filters.program_offering || undefined,
					student_group: this.filters.student_group || undefined,
					course: this.filters.course || undefined,
					status: this.filters.status || undefined,
					start: this.filters.start,
					page_length: this.data.paging?.page_length || 25,
				});
				this.data = response.message || blankData();
				this.filters = { ...this.filters, ...(this.data.filters || {}), start: this.data.paging?.start || 0 };
				this.loaded = true;
				if (selectedName) await this.loadScheme(selectedName);
				else if (!this.draft.name) this.draft = blankScheme(this.filters, this.selectedOffering);
			} catch (error) { this.error = error?.message || "Scheme of Work could not be loaded."; }
			finally { this.loading = false; }
		},
		async branchChanged() {
			this.filters.program_offering = ""; this.filters.student_group = ""; this.filters.course = ""; this.draft = blankScheme();
			await this.load(true);
		},
		async offeringChanged() {
			this.filters.student_group = ""; this.filters.course = ""; this.draft = blankScheme();
			await this.load(true);
		},
		async groupChanged() {
			this.filters.course = ""; this.draft = blankScheme();
			await this.load(true);
		},
		async courseChanged() { this.draft = blankScheme(); await this.load(true); },
		newScheme() { if (this.canCreate) { this.saveError = ""; this.draft = blankScheme(this.filters, this.selectedOffering); } },
		async editScheme(row) {
			this.filters.program_offering = row.program_offering || "";
			this.filters.student_group = row.student_group || "";
			this.filters.course = row.course || "";
			await this.load(true, row.name);
		},
		async loadScheme(name) {
			const response = await frappe.call("eduedge.api.scheme_of_work.get_scheme", { name });
			this.draft = { ...blankScheme(), ...(response.message || {}) };
		},
		addItem() {
			if (!this.editable) return;
			const last = this.draft.items[this.draft.items.length - 1];
			this.draft.items.push({
				sequence: (last?.sequence || this.draft.items.length) + 1,
				week_no: last?.week_no || this.draft.items.length + 1,
				topic: "", topic_name_snapshot: "", topic_description_snapshot: "", learning_objective: "",
				planned_start_date: "", planned_end_date: "", estimated_periods: 1, notes: "",
			});
		},
		removeItem(index) { if (this.editable) this.draft.items.splice(index, 1); },
		async save() {
			if (!this.canSave) return;
			this.saving = true; this.saveError = "";
			try {
				const payload = { ...this.draft, school_branch: this.filters.school_branch, program_offering: this.filters.program_offering, student_group: this.filters.student_group, course: this.filters.course };
				const response = await frappe.call({ method: "eduedge.api.scheme_of_work.save_scheme", type: "POST", args: { payload: JSON.stringify(payload) } });
				this.draft = { ...blankScheme(), ...(response.message || {}) };
				frappe.show_alert({ message: __("Scheme of Work saved"), indicator: "green" });
				await this.load(true, this.draft.name);
			} catch (error) { this.saveError = error?.message || "Scheme of Work could not be saved."; }
			finally { this.saving = false; }
		},
		async approve() { await this.runAction("eduedge.api.scheme_of_work.approve_scheme", "Scheme of Work approved"); },
		async retire() { await this.runAction("eduedge.api.scheme_of_work.retire_scheme", "Scheme of Work retired"); },
		async createVersion() { await this.runAction("eduedge.api.scheme_of_work.create_next_version", "New Scheme version created"); },
		async runAction(method, message) {
			if (!this.draft.name || this.saving) return;
			this.saving = true; this.saveError = "";
			try {
				const response = await frappe.call({ method, type: "POST", args: { name: this.draft.name } });
				this.draft = { ...blankScheme(), ...(response.message || {}) };
				frappe.show_alert({ message: __(message), indicator: "green" });
				this.filters.status = "";
				await this.load(true, this.draft.name);
			} catch (error) { this.saveError = error?.message || "Scheme action could not be completed."; }
			finally { this.saving = false; }
		},
		previousPage() { this.filters.start = Math.max(0, this.filters.start - this.data.paging.page_length); this.load(); },
		nextPage() { this.filters.start += this.data.paging.page_length; this.load(); },
	},
};
</script>

<style scoped>
.scheme-filters { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:.65rem; width:100%; }.scheme-filters label,.item-grid label,.notes { display:grid; gap:.3rem; font-weight:600; }.scheme-layout { display:grid; grid-template-columns:minmax(18rem,.72fr) minmax(0,1.6fr); gap:1rem; margin-top:1rem; }.scheme-panel { display:grid; gap:1rem; align-content:start; padding:1rem; border:1px solid var(--border-color); border-radius:12px; background:var(--card-bg); }.scheme-heading,.scheme-actions { display:flex; align-items:center; justify-content:space-between; gap:.65rem; flex-wrap:wrap; }.scheme-heading h2,.scheme-heading h3 { margin:0; }.scheme-list,.scheme-items { display:grid; gap:.65rem; }.scheme-card { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:.7rem; align-items:center; padding:.75rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); text-align:left; }.scheme-card.is-selected,.scheme-card:hover { border-color:var(--primary); }.scheme-card span { display:grid; gap:.18rem; }.scheme-card small,.snapshot-summary small,.topic-snapshot small { color:var(--text-muted); }.context-summary { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.65rem; }.context-summary div,.snapshot-summary { display:grid; gap:.2rem; padding:.65rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); }.context-summary span { font-size:.78rem; color:var(--text-muted); }.scheme-item { position:relative; padding:.8rem; border:1px solid var(--border-color); border-radius:9px; background:var(--control-bg); }.item-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.65rem; }.item-grid .wide { grid-column:1/-1; }.item-grid .topic-field { grid-column:span 1; }.scheme-item .remove { margin-top:.6rem; }.topic-snapshot { margin-top:.6rem; }.paging { display:flex; justify-content:space-between; align-items:center; }.scheme-error { color:var(--red-600,#b42318); }.notes { margin-top:.25rem; } @media (max-width:1100px) { .scheme-filters { grid-template-columns:repeat(2,minmax(0,1fr)); }.scheme-layout { grid-template-columns:1fr; } } @media (max-width:700px) { .scheme-filters,.context-summary,.item-grid { grid-template-columns:1fr; }.item-grid .wide,.item-grid .topic-field { grid-column:auto; } }
</style>
