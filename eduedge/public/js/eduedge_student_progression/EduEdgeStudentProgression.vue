<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="selectedBranch.institution_name || ''"
		:branch-name="selectedBranch.branch_name || 'Student Progression'"
		:menu-items="menuItems"
		active-route="/app/eduedge-student-progression"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Students & Academic Governance"
					title="Student Progression"
					subtitle="Review academic evidence, prepare destination Enrollments, and approve promotion, repetition, internal transfer, completion or graduation without rewriting submitted history."
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loaded" message="Loading Student Progression..." :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loaded" title="Student Progression could not load" :message="error" action-label="Try again" @retry="load(true)" />
			<template v-else>
				<EdgeFilterBar title="Source academic context">
					<div class="progression-filter-grid">
						<label>
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="branchChanged">
								<option v-for="row in data.allowed_branches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option>
							</select>
						</label>
						<label>
							<span>Source Academic Session *</span>
							<select v-model="filters.source_academic_year" class="form-control" @change="sourceYearChanged">
								<option value="">Select Session</option>
								<option v-for="row in data.academic_years" :key="row.name" :value="row.name">{{ row.name }}</option>
							</select>
						</label>
						<label>
							<span>Class / Programme *</span>
							<select v-model="filters.program" class="form-control" :disabled="!filters.source_academic_year" @change="programChanged">
								<option value="">Select one Class / Programme</option>
								<option v-for="row in data.programs" :key="row.name" :value="row.name">{{ row.program_name || row.name }}</option>
							</select>
						</label>
						<label>
							<span>Source Class Arm / Group</span>
							<select v-model="filters.student_group" class="form-control" :disabled="!filters.program" @change="load(true)">
								<option value="">All Class Arms / Groups</option>
								<option v-for="row in sourceGroupChoices" :key="row.name" :value="row.name">{{ row.student_group_name || row.name }}</option>
							</select>
						</label>
						<label class="wide">
							<span>Search Student</span>
							<input v-model.trim="filters.search" class="form-control" placeholder="Student name or ID" @keyup.enter="load(true)" />
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" @click="clearFilters">Clear</button>
						<button type="button" class="edge-button edge-button--primary" :disabled="loading || !filters.source_academic_year" @click="load(true)">{{ loading ? 'Loading...' : 'Apply' }}</button>
					</template>
				</EdgeFilterBar>

				<section class="progression-principles">
					<div><span>Source Enrollment</span><strong>Submitted history stays immutable</strong></div>
					<div><span>Results & CBT</span><strong>Decision evidence only — never copied forward</strong></div>
					<div><span>Destination Enrollment</span><strong>Prepared as Draft, submitted before final approval</strong></div>
				</section>

				<p v-if="error" class="progression-error">{{ error }}</p>
				<section class="progression-layout">
					<article class="progression-panel">
						<div class="progression-heading">
							<div><p class="edge-eyebrow">Progression register</p><h2>Students</h2></div>
							<div class="progression-actions">
								<button type="button" class="edge-button" :disabled="!selectableRows.length" @click="selectAllVisible">Select visible</button>
								<button type="button" class="edge-button" :disabled="!selected.length" @click="clearSelection">Clear selection</button>
								<span>{{ selected.length }} selected</span>
							</div>
						</div>
						<EdgeActionBar v-if="!filters.program" label="Select one Class / Programme before planning a bulk progression. This prevents mixed destination Classes or Levels in one batch." />
						<EdgeLoadingState v-if="loading" message="Refreshing progression register..." />
						<EdgeEmptyState v-else-if="!data.rows.length" title="No submitted Enrollment found" description="Choose a source Academic Session and Class / Programme with submitted Student Enrollments." />
						<div v-else class="progression-list">
							<article v-for="row in data.rows" :key="row.name" class="progression-row" :class="{ selected: isSelected(row.name) }">
								<label class="progression-select"><input type="checkbox" :checked="isSelected(row.name)" @change="toggleSelection(row.name)" /></label>
								<div class="progression-student">
									<strong>{{ row.student_name || row.student }}</strong>
									<small>{{ row.student }} · {{ row.program_label || row.program }}<template v-if="row.progression_level_label"> · {{ row.progression_level_label }}</template></small>
									<small>{{ row.source_student_group?.student_group_name || row.source_student_group?.name || 'No Class Arm / Group allocation' }}</small>
								</div>
								<div class="progression-evidence">
									<span><strong>{{ row.evidence?.submitted_assessment_results || 0 }}</strong><small>Submitted results</small></span>
									<span><strong>{{ row.evidence?.approved_cbt_results || 0 }}</strong><small>Approved CBT</small></span>
									<span><strong>{{ row.evidence?.pending_cbt_results || 0 }}</strong><small>Pending CBT</small></span>
								</div>
								<div class="progression-decision">
									<EdgeStatusBadge :label="row.current_status || 'Active'" :status="row.current_status || 'active'" :tone="statusTone(row.current_status)" />
									<strong>{{ row.recommendation?.label || 'Review Required' }}</strong>
									<small>{{ row.recommendation?.reason || 'Review the academic record.' }}</small>
									<small v-if="row.planned_target">Prepared: {{ row.planned_target.name }} · {{ row.planned_target.docstatus === 1 ? 'Submitted' : 'Draft' }}</small>
								</div>
								<button type="button" class="edge-button" @click="selectOnly(row.name)">Review one</button>
							</article>
						</div>
						<div class="progression-paging">
							<button type="button" class="edge-button" :disabled="loading || data.paging.start <= 0" @click="previousPage">Previous</button>
							<span>{{ data.paging.start + (data.rows.length ? 1 : 0) }}–{{ data.paging.start + data.rows.length }}</span>
							<button type="button" class="edge-button" :disabled="loading || !data.paging.has_more" @click="nextPage">Next</button>
						</div>
					</article>

					<article class="progression-panel planner">
						<div class="progression-heading"><div><p class="edge-eyebrow">Governed decision</p><h2>Progression Planner</h2></div><span>{{ selected.length }} Student{{ selected.length === 1 ? '' : 's' }}</span></div>
						<EdgeEmptyState v-if="!selected.length" title="Select Students to continue" description="Select one learner for an individual decision or select several learners from the same Class / Programme for a bulk decision." />
						<template v-else>
							<div class="planner-grid">
								<label>
									<span>Outcome *</span>
									<select v-model="planner.outcome" class="form-control" @change="outcomeChanged">
										<option value="Promote">Promote / Progress</option>
										<option value="Repeat">Repeat Class / Level</option>
										<option value="Transfer">Internal Transfer</option>
										<option value="Complete">Complete Programme / Class</option>
										<option value="Graduate">Graduate</option>
										<option value="Defer">Defer</option>
										<option value="Hold">Hold for Review</option>
										<option value="Suspend">Suspend</option>
										<option value="Reactivate">Reactivate</option>
										<option value="Withdraw">Withdraw</option>
									</select>
								</label>
								<label v-if="needsDestination">
									<span>Destination Academic Session *</span>
									<select v-model="planner.destination_academic_year" class="form-control" @change="destinationContextChanged">
										<option value="">Select later Session</option>
										<option v-for="row in laterAcademicYears" :key="row.name" :value="row.name">{{ row.name }}</option>
									</select>
								</label>
								<label v-if="planner.outcome === 'Transfer'">
									<span>Target Branch / Campus *</span>
									<select v-model="planner.target_branch" class="form-control" @change="destinationContextChanged">
										<option value="">Select Branch</option>
										<option v-for="row in transferBranches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option>
									</select>
								</label>
								<label v-if="needsDestination" class="wide">
									<span>Destination Class Arm / Group</span>
									<select v-model="planner.target_student_group" class="form-control" :disabled="destinationLoading || !destination.offering">
										<option value="">Allocate later / no group</option>
										<option v-for="row in destination.student_groups" :key="row.name" :value="row.name">{{ row.student_group_name || row.name }}</option>
									</select>
									<small>Only groups belonging to the exact destination Programme Offering, Branch, Session and compatible Academic Level are offered.</small>
								</label>
								<div v-if="needsDestination && destination.offering" class="destination-card wide">
									<span>Destination Offering</span>
									<strong>{{ destination.offering.offering_title || destination.offering.name }}</strong>
									<small>{{ destination.target_program || destination.offering.program }} · {{ planner.destination_academic_year }}<template v-if="destination.target_progression_level"> · Level {{ destination.target_progression_level }}</template></small>
								</div>
								<label class="wide">
									<span>Decision reason / note *</span>
									<textarea v-model.trim="planner.reason" class="form-control" rows="3" placeholder="Record the academic or management reason for this decision."></textarea>
								</label>
								<label>
									<span>Effective Date</span>
									<input v-model="planner.effective_date" type="date" class="form-control" />
								</label>
							</div>

							<EdgeActionBar label="Preview revalidates every selected Student. Promotion/Repeat/Transfer preparation creates destination Enrollment drafts only; it never submits them automatically.">
								<template #actions>
									<button type="button" class="edge-button" :disabled="!canPreview || previewing" @click="previewSelected">{{ previewing ? 'Checking...' : 'Preview Selected' }}</button>
									<button v-if="needsDestination" type="button" class="edge-button" :disabled="!canPrepare || preparing" @click="confirmPrepare">{{ preparing ? 'Preparing...' : 'Prepare Draft Enrollments' }}</button>
									<button type="button" class="edge-button edge-button--primary" :disabled="!canFinalize || finalizing" @click="confirmFinalize">{{ finalizing ? 'Finalizing...' : 'Finalize Selected' }}</button>
								</template>
							</EdgeActionBar>

							<p v-if="plannerError" class="progression-error">{{ plannerError }}</p>
							<section v-if="preview" class="preview-card">
								<div class="preview-metrics">
									<div><span>Selected</span><strong>{{ preview.summary?.selected || 0 }}</strong></div>
									<div><span>Ready</span><strong>{{ preview.summary?.ready || 0 }}</strong></div>
									<div><span>Blocked</span><strong>{{ preview.summary?.blocked || 0 }}</strong></div>
								</div>
								<div v-if="preview.summary?.blocked" class="preview-list danger"><strong>Resolve before continuing</strong><span v-for="row in preview.rows.filter(item => item.status === 'blocked')" :key="row.source_enrollment">{{ row.source_enrollment }} · {{ row.blocker }}</span></div>
								<div v-else class="preview-list"><strong>Exact decisions ready for approval</strong><span v-for="row in preview.rows" :key="row.source_enrollment">{{ row.student_name || row.student }} · {{ row.outcome }}<template v-if="row.target_program"> → {{ row.target_program }}</template><template v-if="row.target_progression_level"> · {{ row.target_progression_level }}</template></span></div>
							</section>

							<section v-if="prepareResult" class="result-card">
								<strong>Destination Enrollment drafts prepared</strong>
								<span>{{ prepareResult.created_count || 0 }} created · {{ prepareResult.existing_count || 0 }} already prepared</span>
								<p>Review and submit each prepared Enrollment through the normal Enrollment workflow before finalizing progression. Submission remains the authority for capacity, course enrollment and any configured fee effects.</p>
								<div class="prepared-list">
									<button v-for="row in preparedEnrollments" :key="row.name" type="button" class="edge-button" @click="openEnrollment(row.name)">{{ row.name }} · {{ row.docstatus === 1 ? 'Submitted' : 'Draft' }}</button>
								</div>
							</section>

							<section v-if="finalizeResult" class="result-card">
								<strong>Progression finalization</strong>
								<span>{{ finalizeResult.finalized_count || 0 }} finalized · {{ finalizeResult.blocked_count || 0 }} blocked</span>
								<div v-if="finalizeResult.blocked?.length" class="preview-list danger"><span v-for="row in finalizeResult.blocked" :key="row.source_enrollment">{{ row.source_enrollment }} · {{ row.reason }}</span></div>
							</section>
						</template>
					</article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const today = () => frappe.datetime?.get_today?.() || new Date().toISOString().slice(0, 10);
const blankData = () => ({
	selected_branch: {}, allowed_branches: [], academic_years: [], programs: [], student_groups: [], rows: [],
	filters: {}, paging: { start: 0, page_length: 50, has_more: false, next_start: 0 }, permissions: {},
});
const blankDestination = () => ({ offering: null, target_program: "", target_progression_level: "", student_groups: [] });
const blankPlanner = () => ({ outcome: "Promote", destination_academic_year: "", target_branch: "", target_student_group: "", reason: "", effective_date: today() });

export default {
	name: "EduEdgeStudentProgression",
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS, loading: true, loaded: false, error: "", plannerError: "", previewing: false,
			preparing: false, finalizing: false, destinationLoading: false, data: blankData(), destination: blankDestination(),
			filters: { branch: "", source_academic_year: "", program: "", student_group: "", search: "", start: 0 },
			selected: [], planner: blankPlanner(), preview: null, prepareResult: null, finalizeResult: null,
		};
	},
	computed: {
		selectedBranch() { return this.data.selected_branch || {}; },
		sourceGroupChoices() { return (this.data.student_groups || []).filter((row) => !this.filters.program || row.program === this.filters.program); },
		selectableRows() { return this.data.rows || []; },
		needsDestination() { return ["Promote", "Repeat", "Transfer"].includes(this.planner.outcome); },
		laterAcademicYears() {
			const source = (this.data.academic_years || []).find((row) => row.name === this.filters.source_academic_year);
			return (this.data.academic_years || []).filter((row) => row.name !== this.filters.source_academic_year && (!source?.year_start_date || !row.year_start_date || row.year_start_date > source.year_start_date));
		},
		transferBranches() { const institution = this.selectedBranch.institution; return (this.data.allowed_branches || []).filter((row) => row.institution === institution && row.name !== this.filters.branch); },
		canPreview() { return Boolean(this.selected.length && this.filters.program && this.planner.outcome && (!this.needsDestination || (this.planner.destination_academic_year && (this.planner.outcome !== "Transfer" || this.planner.target_branch)))); },
		canPrepare() { return Boolean(this.data.permissions?.can_prepare && this.needsDestination && this.preview && !this.preview.summary?.blocked && this.planner.reason); },
		canFinalize() { return Boolean(this.data.permissions?.can_finalize && this.preview && !this.preview.summary?.blocked && this.planner.reason); },
		preparedEnrollments() { return [...(this.prepareResult?.created || []), ...(this.prepareResult?.existing || [])]; },
	},
	async mounted() {
		const params = new URLSearchParams(window.location.search || "");
		this.filters.branch = params.get("branch") || "";
		this.filters.source_academic_year = params.get("academic_year") || "";
		this.filters.program = params.get("program") || "";
		this.filters.student_group = params.get("student_group") || "";
		await this.load(true);
	},
	methods: {
		openRoute: openEduEdgeRoute,
		async load(resetStart = false) {
			if (resetStart) this.filters.start = 0;
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.student_progression.get_student_progression_page", this.filters);
				this.data = { ...blankData(), ...(response.message || {}) };
				this.filters = { ...this.filters, ...(this.data.filters || {}), start: this.data.paging?.start || 0 };
				this.selected = this.selected.filter((name) => this.data.rows.some((row) => row.name === name));
				this.loaded = true;
			} catch (error) { this.error = error?.message || "Student Progression could not be loaded."; }
			finally { this.loading = false; }
		},
		resetPlan() { this.selected = []; this.planner = blankPlanner(); this.destination = blankDestination(); this.preview = null; this.prepareResult = null; this.finalizeResult = null; this.plannerError = ""; },
		async branchChanged() { this.filters.source_academic_year = ""; this.filters.program = ""; this.filters.student_group = ""; this.resetPlan(); await this.load(true); },
		async sourceYearChanged() { this.filters.program = ""; this.filters.student_group = ""; this.resetPlan(); await this.load(true); },
		async programChanged() { this.filters.student_group = ""; this.resetPlan(); await this.load(true); },
		async clearFilters() { const branch = this.filters.branch; this.filters = { branch, source_academic_year: "", program: "", student_group: "", search: "", start: 0 }; this.resetPlan(); await this.load(true); },
		isSelected(name) { return this.selected.includes(name); },
		toggleSelection(name) { const set = new Set(this.selected); if (set.has(name)) set.delete(name); else set.add(name); this.selected = [...set]; this.invalidatePreview(); this.destinationContextChanged(); },
		selectOnly(name) { this.selected = [name]; this.invalidatePreview(); this.destinationContextChanged(); },
		selectAllVisible() { this.selected = this.selectableRows.map((row) => row.name); this.invalidatePreview(); this.destinationContextChanged(); },
		clearSelection() { this.selected = []; this.invalidatePreview(); this.destination = blankDestination(); },
		invalidatePreview() { this.preview = null; this.prepareResult = null; this.finalizeResult = null; this.plannerError = ""; },
		async outcomeChanged() { this.planner.target_student_group = ""; this.destination = blankDestination(); this.invalidatePreview(); await this.destinationContextChanged(); },
		async destinationContextChanged() {
			this.invalidatePreview(); this.planner.target_student_group = ""; this.destination = blankDestination();
			if (!this.needsDestination || this.selected.length !== 1 && !this.filters.program || !this.planner.destination_academic_year) return;
			const source = this.selected[0]; if (!source) return;
			if (this.planner.outcome === "Transfer" && !this.planner.target_branch) return;
			this.destinationLoading = true;
			try {
				const response = await frappe.call("eduedge.api.student_progression.get_progression_destination_options", {
					source_enrollment: source, outcome: this.planner.outcome, destination_academic_year: this.planner.destination_academic_year,
					target_branch: this.planner.outcome === "Transfer" ? this.planner.target_branch : undefined,
				});
				this.destination = { ...blankDestination(), ...(response.message || {}) };
			} catch (error) { this.plannerError = error?.message || "Destination progression context could not be resolved."; }
			finally { this.destinationLoading = false; }
		},
		batchPayload() { return { source_enrollments: this.selected, outcome: this.planner.outcome, destination_academic_year: this.needsDestination ? this.planner.destination_academic_year : undefined, target_branch: this.planner.outcome === "Transfer" ? this.planner.target_branch : undefined, target_student_group: this.needsDestination ? this.planner.target_student_group : undefined, reason: this.planner.reason, effective_date: this.planner.effective_date }; },
		async previewSelected() {
			if (!this.canPreview) return;
			this.previewing = true; this.plannerError = ""; this.preview = null; this.prepareResult = null; this.finalizeResult = null;
			try { const response = await frappe.call({ method: "eduedge.api.student_progression.preview_progression_batch", type: "POST", args: { payload: JSON.stringify(this.batchPayload()) } }); this.preview = response.message || null; }
			catch (error) { this.plannerError = error?.message || "Progression preview failed."; }
			finally { this.previewing = false; }
		},
		confirmPrepare() { if (!this.canPrepare) return; frappe.confirm(__(`Prepare ${this.selected.length} destination Enrollment draft(s)? Nothing will be submitted automatically.`), () => this.prepareSelected()); },
		async prepareSelected() {
			this.preparing = true; this.plannerError = "";
			try { const response = await frappe.call({ method: "eduedge.api.student_progression.prepare_progression_batch", type: "POST", args: { payload: JSON.stringify(this.batchPayload()) } }); this.prepareResult = response.message || null; frappe.show_alert({ message: __(`${this.prepareResult?.created_count || 0} destination Enrollment draft(s) prepared`), indicator: "green" }); await this.load(false); }
			catch (error) { this.plannerError = error?.message || "Destination Enrollments could not be prepared."; }
			finally { this.preparing = false; }
		},
		confirmFinalize() { if (!this.canFinalize) return; const note = this.needsDestination ? "Every prepared destination Enrollment must already be submitted." : "This writes an append-only Enrollment lifecycle decision."; frappe.confirm(__(`Finalize ${this.selected.length} Student progression decision(s)? ${note}`), () => this.finalizeSelected()); },
		async finalizeSelected() {
			this.finalizing = true; this.plannerError = "";
			try { const response = await frappe.call({ method: "eduedge.api.student_progression.finalize_progression_batch", type: "POST", args: { payload: JSON.stringify(this.batchPayload()) } }); this.finalizeResult = response.message || null; frappe.show_alert({ message: __(`${this.finalizeResult?.finalized_count || 0} progression decision(s) finalized`), indicator: this.finalizeResult?.blocked_count ? "orange" : "green" }); await this.load(false); }
			catch (error) { this.plannerError = error?.message || "Progression could not be finalized."; }
			finally { this.finalizing = false; }
		},
		openEnrollment(name) { if (name) window.open(`/app/program-enrollment/${encodeURIComponent(name)}`, "_blank", "noopener,noreferrer"); },
		statusTone(status) { return ["Active", "Promoted", "Graduated", "Completed"].includes(status) ? "success" : ["Held for Review", "Deferred", "Suspended"].includes(status) ? "warning" : ["Withdrawn", "Cancelled"].includes(status) ? "danger" : "neutral"; },
		previousPage() { this.filters.start = Math.max(0, (this.data.paging.start || 0) - (this.data.paging.page_length || 50)); this.load(false); },
		nextPage() { if (this.data.paging.has_more) { this.filters.start = this.data.paging.next_start; this.load(false); } },
	},
};
</script>

<style scoped>
.progression-filter-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.75rem;width:100%}.progression-filter-grid label,.planner-grid label{display:grid;gap:.35rem;font-weight:600}.progression-filter-grid .wide,.planner-grid .wide{grid-column:1/-1}.progression-principles{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.75rem;margin:1rem 0}.progression-principles>div,.preview-metrics>div{display:grid;gap:.2rem;padding:.8rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.progression-principles span,.preview-metrics span,.destination-card span{color:var(--text-muted);font-size:.78rem}.progression-layout{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(24rem,.9fr);gap:1rem}.progression-panel{display:grid;gap:1rem;align-content:start;padding:1rem;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}.progression-heading,.progression-actions,.progression-paging{display:flex;align-items:center;justify-content:space-between;gap:.65rem;flex-wrap:wrap}.progression-heading h2{margin:.2rem 0 0}.progression-list{display:grid;gap:.65rem}.progression-row{display:grid;grid-template-columns:2rem minmax(12rem,1.3fr) minmax(10rem,.8fr) minmax(13rem,1.15fr) auto;gap:.7rem;align-items:center;padding:.75rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.progression-row.selected{border-color:var(--primary)}.progression-select{display:flex;align-items:center;justify-content:center}.progression-student,.progression-decision{display:grid;gap:.2rem}.progression-student small,.progression-decision small,.result-card p{color:var(--text-muted)}.progression-evidence{display:grid;grid-template-columns:repeat(3,1fr);gap:.35rem}.progression-evidence span{display:grid;text-align:center;padding:.35rem;border-radius:6px;background:var(--card-bg)}.progression-evidence small{font-size:.7rem;color:var(--text-muted)}.planner-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem}.destination-card,.preview-card,.result-card{display:grid;gap:.5rem;padding:.8rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.preview-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:.5rem}.preview-list,.prepared-list{display:grid;gap:.4rem}.preview-list span{display:block}.preview-list.danger,.progression-error{color:var(--red-600,#b42318)}.prepared-list{grid-template-columns:repeat(auto-fit,minmax(12rem,1fr))}@media(max-width:1150px){.progression-layout{grid-template-columns:1fr}.progression-row{grid-template-columns:2rem minmax(12rem,1fr) minmax(10rem,.8fr);}.progression-decision,.progression-row>.edge-button{grid-column:2/-1}}@media(max-width:800px){.progression-filter-grid,.progression-principles,.planner-grid,.progression-row{grid-template-columns:1fr}.progression-filter-grid .wide,.planner-grid .wide,.progression-decision,.progression-row>.edge-button{grid-column:auto}.progression-select{justify-content:flex-start}.progression-evidence{grid-template-columns:repeat(3,1fr)}}
</style>
