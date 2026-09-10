<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="selectedBranch.institution_name || ''"
		:branch-name="selectedBranch.branch_name || classArmPlural"
		:menu-items="menuItems"
		active-route="/app/eduedge-class-arms"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Academic Setup"
					:title="classArmPlural"
					:subtitle="`${classArmPlural} span the full Academic Session. Terms and Semesters use the same class identity, roster and Student Group.`"
					:action-label="canCreate ? `New ${classArmSingular}` : ''"
					@action="newClassArm"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loadedOnce" :message="`Loading ${classArmPlural.toLowerCase()}...`" :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loadedOnce" :title="`${classArmPlural} could not load`" :message="error" action-label="Try again" @retry="load(true)" />
			<template v-else>
				<EdgeFilterBar :title="`${classArmSingular} filters`">
					<div class="class-arm-filter-grid">
						<label>
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="filterBranchChanged">
								<option v-for="branch in data.allowed_branches" :key="branch.name" :value="branch.name">{{ branch.branch_name || branch.name }}</option>
							</select>
						</label>
						<label>
							<span>{{ academicYearSingular }}</span>
							<select v-model="filters.academic_year" class="form-control" @change="load(true)">
								<option value="">All {{ academicYearPlural.toLowerCase() }}</option>
								<option v-for="year in academicYearChoices" :key="year" :value="year">{{ year }}</option>
							</select>
						</label>
						<label class="class-arm-search">
							<span>Search</span>
							<input v-model.trim="filters.search" class="form-control" :placeholder="`${classArmSingular} or ${programmeSingular.toLowerCase()}`" @keyup.enter="load(true)" />
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" @click="clearFilters">Clear</button>
						<button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="load(true)">{{ loading ? "Loading..." : "Apply" }}</button>
					</template>
				</EdgeFilterBar>

				<section class="session-rule">
					<div><span>Programme Offering</span><strong>One per Branch + Class + Academic Session</strong></div>
					<div><span>{{ classArmSingular }}</span><strong>One Student Group for the full Academic Session</strong></div>
					<div><span>Term / Semester</span><strong>Calendar and academic activity context only</strong></div>
				</section>

				<p v-if="error && loadedOnce" class="class-arm-error">{{ error }}</p>
				<section class="class-arm-layout">
					<article class="class-arm-panel">
						<div class="class-arm-heading">
							<div><p class="edge-eyebrow">Session Class Arms</p><h2>{{ classArmPlural }}</h2></div>
							<div class="class-arm-heading-actions">
								<button v-if="canCreate" type="button" class="edge-button" @click="openBulkRollover">Bulk Carry Forward</button>
								<button v-if="canCreate" type="button" class="edge-button edge-button--primary" @click="newClassArm">New {{ classArmSingular }}</button>
							</div>
						</div>
						<EdgeLoadingState v-if="loading" :message="`Refreshing ${classArmPlural.toLowerCase()}...`" />
						<EdgeEmptyState v-else-if="!data.class_arms.length" :title="`No ${classArmPlural.toLowerCase()} found`" :description="canCreate ? `Create the first ${classArmSingular.toLowerCase()} from a sessional Programme Offering.` : 'Change the filters or contact an academic administrator.'" />
						<div v-else class="class-arm-list">
							<article v-for="row in data.class_arms" :key="row.name" class="class-arm-card" :class="{ 'is-selected': draft.name === row.name }">
								<button type="button" class="class-arm-card-main" @click="editClassArm(row.name)">
									<div class="class-arm-title">
										<span><strong>{{ row.display_name || row.student_group_name || row.name }}</strong><small>{{ row.program || programmeSingular }} · {{ row.academic_year || 'No Academic Session' }}</small></span>
										<div class="class-arm-badges">
											<EdgeStatusBadge :label="row.disabled ? 'Disabled' : 'Active'" :status="row.disabled ? 'disabled' : 'active'" :tone="row.disabled ? 'danger' : 'success'" />
											<EdgeStatusBadge v-if="row.legacy_term_bound" label="Legacy Term Record" status="legacy" tone="warning" />
										</div>
									</div>
									<div class="class-arm-meta">
										<span>{{ row.class_arm_identity?.class_arm_code || "Legacy identity" }}</span>
										<span>{{ row.course || row.group_based_on || "Class" }}</span>
										<span>{{ row.student_count || 0 }} {{ studentPlural.toLowerCase() }}</span>
										<span>{{ row.legacy_term_bound ? row.academic_term : "Full session" }}</span>
									</div>
								</button>
								<div class="class-arm-card-actions">
									<button v-if="canCarryForward(row)" type="button" class="edge-button" @click="carryClassArmForward(row)">Carry {{ classArmSingular }} Forward</button>
									<span v-else-if="row.legacy_term_bound" class="class-arm-action-note">Historical record · no carry-forward action</span>
								</div>
							</article>
						</div>
						<div class="class-arm-paging">
							<button type="button" class="edge-button" :disabled="loading || data.paging.start <= 0" @click="previousPage">Previous</button>
							<span>{{ data.paging.start + (data.class_arms.length ? 1 : 0) }}–{{ data.paging.start + data.class_arms.length }}</span>
							<button type="button" class="edge-button" :disabled="loading || !data.paging.has_more" @click="nextPage">Next</button>
						</div>
					</article>

					<article class="class-arm-panel editor">
						<div class="class-arm-heading">
							<div><p class="edge-eyebrow">{{ draft.name ? "Academic Session Class Arm" : "New Session Class Arm" }}</p><h2>{{ draft.name ? draft.display_name || classArmSingular : `New ${classArmSingular}` }}</h2></div>
							<button type="button" class="edge-button" @click="newClassArm">Reset</button>
						</div>
						<div v-if="draft.legacy_term_bound" class="legacy-warning"><strong>Historical term-bound record</strong><span>This record is preserved for audit and existing references. Do not edit or duplicate it. Create/use the session-wide {{ classArmSingular }} for current operations.</span></div>
						<EdgeEmptyState v-if="!canCreate && !canWrite" :title="`Read-only ${classArmPlural.toLowerCase()}`" :description="`Your role can view ${classArmPlural.toLowerCase()} but cannot create or edit them.`" />
						<template v-else>
							<label>
								<span>Branch / Campus</span>
								<select v-model="draft.branch" class="form-control" :disabled="Boolean(draft.name)" @change="draftBranchChanged">
									<option value="">Select Branch / Campus</option>
									<option v-for="branch in data.allowed_branches" :key="branch.name" :value="branch.name">{{ branch.branch_name || branch.name }}</option>
								</select>
							</label>
							<label>
								<span>{{ offeringSingular }}</span>
								<select v-model="draft.offering" class="form-control" :disabled="Boolean(draft.name) || !draft.branch || optionsLoading" @change="draftOfferingChanged">
									<option value="">{{ draft.branch ? `Select sessional ${offeringSingular}` : "Select Branch first" }}</option>
									<option v-for="offering in options.offerings" :key="offering.name" :value="offering.name">{{ offering.offering_title || offering.name }} · {{ offering.academic_year }}</option>
								</select>
								<small>Only session-wide Programme Offerings are available. No Term / Semester selection is required.</small>
							</label>

							<div v-if="draft.offering || draft.name" class="class-arm-context">
								<div><span>Institution</span><strong>{{ contextInstitutionName }}</strong></div>
								<div><span>{{ programmeSingular }}</span><strong>{{ draft.program || "Not resolved" }}</strong></div>
								<div><span>{{ academicYearSingular }}</span><strong>{{ draft.academic_year || "Not resolved" }}</strong></div>
								<div><span>Coverage</span><strong>{{ draft.legacy_term_bound ? `Legacy · ${draft.academic_term}` : "Full Academic Session" }}</strong></div>
								<div><span>Reusable identity</span><strong>{{ draft.class_arm_identity?.class_arm_code || (draft.name ? "Migration required" : "Created on save") }}</strong></div>
								<div><span>Previous session</span><strong>{{ draft.previous_student_group || "First known session" }}</strong></div>
							</div>

							<label><span>{{ classArmSingular }} Name</span><input v-model.trim="draft.display_name" class="form-control" :disabled="Boolean(draft.name)" :placeholder="`Example: JSS 2A or ${programmeSingular} Group A`" /><small v-if="draft.name">This reusable identity continues across Academic Sessions. A session record cannot be reassigned to another identity.</small></label>
							<div class="two-column">
								<label><span>Group Based On</span><select v-model="draft.group_based_on" class="form-control" :disabled="draft.legacy_term_bound" @change="groupBasisChanged"><option value="Batch">Batch / Class</option><option value="Course">Course / Subject</option><option value="Activity">Activity</option></select></label>
								<label><span>Maximum Strength</span><input v-model.number="draft.max_strength" type="number" min="0" class="form-control" :disabled="draft.legacy_term_bound" /><small>Zero means no configured limit.</small></label>
							</div>
							<label v-if="draft.group_based_on === 'Course'"><span>{{ courseSingular }}</span><select v-model="draft.course" class="form-control" :disabled="draft.legacy_term_bound"><option value="">Select {{ courseSingular }}</option><option v-for="course in options.courses" :key="course.name" :value="course.name">{{ course.label || course.name }}</option></select></label>
							<label class="class-arm-check"><input v-model="draft.disabled" type="checkbox" :disabled="draft.legacy_term_bound" /> Disabled</label>

							<section class="class-arm-roster">
								<div class="class-arm-subheading"><div><p class="edge-eyebrow">Session roster</p><h3>{{ studentPlural }}</h3></div><span>{{ activeRosterCount }} selected</span></div>
								<p class="roster-help">The same roster serves every Term / Semester in this Academic Session. Students removed later are made inactive in the group rather than deleted from history.</p>
								<input v-model.trim="studentSearch" class="form-control" :disabled="draft.legacy_term_bound" :placeholder="`Search eligible ${studentPlural.toLowerCase()}`" />
								<EdgeEmptyState v-if="draft.offering && !studentChoices.length" :title="`No eligible ${studentPlural.toLowerCase()}`" description="Only enabled students with submitted enrollment in this exact Programme Offering and Branch are available." />
								<button v-if="draft.offering && !studentChoices.length && !draft.legacy_term_bound" type="button" class="edge-button edge-button--primary" @click="openStudentEnrollments">Enroll Student</button>
								<div v-else class="choice-list">
									<div v-for="student in filteredStudentChoices" :key="student.name" class="choice-row">
										<label><input type="checkbox" :disabled="draft.legacy_term_bound" :checked="isStudentSelected(student.name)" @change="toggleStudent(student)" /><span><strong>{{ student.student_name || student.name }}</strong><small>{{ student.name }}</small></span></label>
										<input v-if="isStudentSelected(student.name)" :value="studentRoll(student.name)" type="number" min="1" class="form-control input-sm" :disabled="draft.legacy_term_bound" placeholder="Roll no." @input="setStudentRoll(student.name, $event.target.value)" />
									</div>
								</div>
							</section>

							<EdgeActionBar label="Teaching responsibility is separate from Class Arm identity. Use Instructor Assignments for whole-class, Class Arm and Subject responsibility.">
								<template #actions>
									<button v-if="canCarryDraftForward" type="button" class="edge-button" @click="carryClassArmForward(draftAsListRow)">Carry {{ classArmSingular }} Forward</button>
									<button v-if="draft.name" type="button" class="edge-button edge-button--primary" @click="openInstructorAssignments">Assign Instructor</button>
									<button type="button" class="edge-button" @click="openInstructors">Manage Instructors</button>
								</template>
							</EdgeActionBar>

							<p v-if="saveError" class="class-arm-error">{{ saveError }}</p>
							<div class="class-arm-actions">
								<button v-if="!draft.legacy_term_bound" type="button" class="edge-button edge-button--primary" :disabled="!canSave || saving || optionsLoading" @click="saveClassArm">{{ saving ? "Saving..." : `Save ${classArmSingular}` }}</button>
								<button v-if="draft.name" type="button" class="edge-button" @click="openFullForm(draft.name)">Open full form</button>
							</div>
						</template>
					</article>
				</section>

				<section v-if="canCreate" ref="bulkRolloverPanel" class="class-arm-panel bulk-rollover-panel">
					<div class="class-arm-heading">
						<div>
							<p class="edge-eyebrow">Academic Session rollover</p>
							<h2>Bulk Carry Class Arms Forward</h2>
							<p>Prepare next-session class structure first. Select the {{ classArmPlural.toLowerCase() }} to create; Student Progression will later create destination Enrollments and allocate learners. Terms and Semesters do not require Class Arm rollover.</p>
						</div>
					</div>
					<div class="rollover-controls">
						<label><span>Branch / Campus</span><select v-model="bulk.branch" class="form-control" @change="resetBulkPreview"><option v-for="branch in data.allowed_branches" :key="branch.name" :value="branch.name">{{ branch.branch_name || branch.name }}</option></select></label>
						<label><span>Source {{ academicYearSingular }}</span><select v-model="bulk.source_academic_year" class="form-control" @change="bulkSourceChanged"><option value="">Select source Session</option><option v-for="year in academicYearChoices" :key="year" :value="year">{{ year }}</option></select></label>
						<label><span>Destination {{ academicYearSingular }}</span><select v-model="bulk.destination_academic_year" class="form-control" @change="resetBulkPreview"><option value="">Select next Session</option><option v-for="year in bulkDestinationYears" :key="year" :value="year">{{ year }}</option></select></label>
					</div>
					<div class="class-arm-actions rollover-toolbar">
						<div class="rollover-selection-actions">
							<button type="button" class="edge-button" :disabled="!bulk.preview?.summary?.ready" @click="selectAllBulkReady">Select all ready</button>
							<button type="button" class="edge-button" :disabled="!selectedBulkCount" @click="clearBulkSelection">Clear selection</button>
							<span v-if="bulk.preview">{{ selectedBulkCount }} selected</span>
						</div>
						<div class="rollover-execution-actions">
							<button type="button" class="edge-button" :disabled="!bulkReady || bulk.previewing" @click="previewSessionRollover">{{ bulk.previewing ? "Checking..." : "Preview Next Session" }}</button>
							<button v-if="bulk.preview?.summary?.ready" type="button" class="edge-button edge-button--primary" :disabled="!selectedBulkCount || bulk.executing" @click="confirmExecuteSessionRollover">{{ bulk.executing ? "Preparing..." : `Prepare ${selectedBulkCount} Selected` }}</button>
						</div>
					</div>
					<p v-if="bulk.error" class="class-arm-error">{{ bulk.error }}</p>
					<div v-if="bulk.preview" class="rollover-summary">
						<div><span>Total</span><strong>{{ bulk.preview.summary.total }}</strong></div>
						<div><span>Ready</span><strong>{{ bulk.preview.summary.ready }}</strong></div>
						<div><span>Already prepared</span><strong>{{ bulk.preview.summary.existing }}</strong></div>
						<div><span>Blocked</span><strong>{{ bulk.preview.summary.blocked }}</strong></div>
						<div><span>Source students</span><strong>{{ bulk.preview.summary.source_students || 0 }}</strong></div>
						<div><span>Awaiting progression</span><strong>{{ bulk.preview.summary.students_pending_progression || 0 }}</strong></div>
					</div>
					<div v-if="bulk.preview?.rows?.length" class="rollover-list">
						<article v-for="row in bulk.preview.rows" :key="row.class_arm_identity || row.source" class="rollover-row">
							<label class="rollover-select">
								<input v-if="row.status === 'ready'" type="checkbox" :checked="isBulkSelected(row.class_arm_identity)" @change="toggleBulkSelection(row.class_arm_identity)" />
								<span v-else>—</span>
							</label>
							<div><strong>{{ row.display_name || row.class_arm_identity || 'Class Arm' }}</strong><small>{{ row.program || '' }}<template v-if="row.legacy_source"> · Legacy source consolidated</template></small></div>
							<EdgeStatusBadge :label="rolloverStatusLabel(row.status)" :status="row.status" :tone="rolloverTone(row.status)" />
							<span>{{ row.status === 'blocked' ? row.reason : `${row.source_student_count || 0} source students · destination roster starts empty` }}</span>
						</article>
					</div>
					<div class="downstream-note">
						<strong>Student Progression, Assessment, Results and CBT alignment</strong>
						<span>Carry-forward creates only the next-session Class Arm structure. It does not copy Students. Student Progression prepares and submits the destination Program Enrollment, then allocates each learner to a prepared Class Arm. Existing Assessment Plans, Assessment Results, Result Publications, CBT Schedules, attempts and CBT Results remain historical and are never copied or retargeted.</span>
					</div>
					<div v-if="bulk.result" class="rollover-result">
						<strong>Next-session Class Arm structure prepared</strong>
						<span>{{ bulk.result.created_count }} created · {{ bulk.result.existing_count }} already existed · {{ bulk.result.blocked_count }} blocked</span>
						<button type="button" class="edge-button edge-button--primary" @click="openStudentProgression">Continue to Student Progression</button>
					</div>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const emptyDraft = () => ({
	name: "", display_name: "", class_arm_identity: null, previous_student_group: "", branch: "", institution: "", offering: "", program: "",
	academic_year: "", academic_term: "", batch: "", group_based_on: "Batch", course: "", max_strength: 0, disabled: false,
	legacy_term_bound: false, students: [], can_write: true,
});
const emptyOptions = () => ({ offerings: [], academic_years: [], courses: [], students: [], class_arm_identities: [], context: {} });
const emptyData = () => ({ selected_branch: {}, allowed_branches: [], class_arms: [], filters: {}, permissions: { can_create: false, can_write: false }, paging: { start: 0, page_length: 25, has_more: false, next_start: 0 } });
const emptyBulk = () => ({ branch: "", source_academic_year: "", destination_academic_year: "", selected_class_arm_identities: [], preview: null, result: null, previewing: false, executing: false, error: "" });

export default {
	name: "EduEdgeClassArms",
	data() {
		return {
			loading: true, loadedOnce: false, error: "", optionsLoading: false, saving: false, saveError: "", menuItems: EDUEDGE_MENU_ITEMS,
			filters: { branch: "", academic_year: "", search: "" }, data: emptyData(), options: emptyOptions(), draft: emptyDraft(), bulk: emptyBulk(),
			studentSearch: "", initialCreateMode: false,
		};
	},
	computed: {
		selectedBranch() { return this.data.selected_branch || {}; },
		classArmSingular() { return this.term("student_group", false, "Class Arm"); },
		classArmPlural() { return this.term("student_group", true, "Class Arms"); },
		programmeSingular() { return this.term("programme", false, "Programme / Class"); },
		offeringSingular() { return this.term("programme_offering", false, "Programme Offering"); },
		academicYearSingular() { return this.term("academic_year", false, "Academic Session"); },
		academicYearPlural() { return this.term("academic_year", true, "Academic Sessions"); },
		courseSingular() { return this.term("course", false, "Course / Subject"); },
		studentPlural() { return this.term("student", true, "Students"); },
		canCreate() { return Boolean(this.data.permissions.can_create); },
		canWrite() { return Boolean(this.data.permissions.can_write); },
		canSave() {
			const permitted = this.draft.name ? this.draft.can_write && this.canWrite : this.canCreate;
			return Boolean(!this.draft.legacy_term_bound && permitted && this.draft.branch && this.draft.offering && this.draft.display_name && (this.draft.group_based_on !== "Course" || this.draft.course));
		},
		academicYearChoices() {
			const values = new Set((this.options.academic_years || []).map((row) => row.name).filter(Boolean));
			for (const row of this.data.class_arms || []) if (row.academic_year) values.add(row.academic_year);
			return [...values];
		},
		bulkDestinationYears() { return this.laterAcademicYears(this.bulk.source_academic_year).map((row) => row.name); },
		selectedBulkCount() { return (this.bulk.selected_class_arm_identities || []).length; },
		contextInstitutionName() {
			const branch = this.data.allowed_branches.find((row) => row.name === this.draft.branch);
			return branch?.institution_name || this.options.context?.institution || this.draft.institution || "Not resolved";
		},
		studentChoices() {
			const rows = new Map();
			for (const row of this.options.students || []) rows.set(row.name, { ...row });
			for (const row of this.draft.students || []) if (row.student) rows.set(row.student, { name: row.student, student_name: row.student_name || row.student, ...(rows.get(row.student) || {}) });
			return [...rows.values()];
		},
		filteredStudentChoices() {
			const query = this.studentSearch.toLowerCase();
			return query ? this.studentChoices.filter((row) => `${row.student_name || ""} ${row.name || ""}`.toLowerCase().includes(query)) : this.studentChoices;
		},
		activeRosterCount() { return (this.draft.students || []).filter((row) => Number(row.active ?? 1) === 1).length; },
		bulkReady() { return Boolean(this.bulk.branch && this.bulk.source_academic_year && this.bulk.destination_academic_year && this.bulk.source_academic_year !== this.bulk.destination_academic_year); },
		canCarryDraftForward() { return Boolean(this.canCreate && this.draft.name && !this.draft.disabled && !this.draft.legacy_term_bound && this.draft.academic_year && this.draft.class_arm_identity); },
		draftAsListRow() { return { name: this.draft.name, display_name: this.draft.display_name, academic_year: this.draft.academic_year, disabled: this.draft.disabled, legacy_term_bound: this.draft.legacy_term_bound, class_arm_identity: this.draft.class_arm_identity }; },
	},
	async mounted() {
		const params = new URLSearchParams(window.location.search || "");
		this.filters.branch = params.get("branch") || "";
		this.filters.academic_year = params.get("academic_year") || "";
		this.initialCreateMode = params.get("mode") === "create";
		await this.load(true);
		await this.loadOptions(false);
		this.bulk.branch = this.filters.branch || this.data.selected_branch?.name || "";
		this.bulk.source_academic_year = this.filters.academic_year || "";
		if (this.initialCreateMode && this.canCreate) await this.newClassArm();
	},
	methods: {
		openRoute: openEduEdgeRoute,
		term(key, plural = false, fallback = "") { return frappe.eduedge?.term?.(key, { plural, context: this.selectedBranch, fallback }) || fallback; },
		async load(resetStart = false) {
			if (resetStart) this.data.paging.start = 0;
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.class_arms.get_class_arms_page", { ...this.filters, start: this.data.paging.start || 0, page_length: this.data.paging.page_length || 25 });
				this.data = response.message || emptyData();
				this.filters = { ...this.filters, ...(this.data.filters || {}) };
				this.loadedOnce = true;
				if (!this.draft.branch) this.draft.branch = this.filters.branch || "";
				if (!this.bulk.branch) this.bulk.branch = this.filters.branch || "";
			} catch (error) { this.error = error?.message || `${this.classArmPlural} could not be loaded.`; }
			finally { this.loading = false; }
		},
		async loadOptions(includeOffering = true) {
			const branch = this.draft.branch || this.filters.branch;
			if (!branch) return;
			this.optionsLoading = true; this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.class_arms.get_class_arm_options", { branch, offering: includeOffering && this.draft.offering ? this.draft.offering : undefined, class_arm: includeOffering && this.draft.name ? this.draft.name : undefined });
				const result = response.message || {};
				this.options = { ...emptyOptions(), ...result, context: result.context || {} };
				if (!this.data.allowed_branches.length && result.allowed_branches) this.data.allowed_branches = result.allowed_branches;
				if (result.context?.name) this.applyOfferingContext(result.context);
			} catch (error) { this.saveError = error?.message || "Class Arm options could not be loaded."; }
			finally { this.optionsLoading = false; }
		},
		applyOfferingContext(context) { this.draft.institution = context.institution || ""; this.draft.program = context.program || ""; this.draft.academic_year = context.academic_year || ""; this.draft.academic_term = ""; this.draft.batch = context.student_batch || ""; },
		async newClassArm() { this.draft = { ...emptyDraft(), branch: this.filters.branch || this.data.selected_branch?.name || "" }; this.options = emptyOptions(); this.studentSearch = ""; this.saveError = ""; await this.loadOptions(false); },
		async editClassArm(name) {
			this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.class_arms.get_class_arm", { name });
				const row = response.message || {};
				this.draft = { ...emptyDraft(), ...row, offering: row.offering || "", branch: row.branch || this.filters.branch, disabled: Boolean(row.disabled), legacy_term_bound: Boolean(row.legacy_term_bound), students: row.students || [] };
				await this.loadOptions(!this.draft.legacy_term_bound);
			} catch (error) { this.saveError = error?.message || `${this.classArmSingular} could not be opened.`; }
		},
		async filterBranchChanged() { this.filters.academic_year = ""; this.bulk = { ...emptyBulk(), branch: this.filters.branch }; await this.load(true); await this.newClassArm(); },
		async clearFilters() { const branch = this.filters.branch; this.filters = { branch, academic_year: "", search: "" }; await this.load(true); },
		async draftBranchChanged() { this.filters.branch = this.draft.branch; this.draft.offering = ""; this.draft.institution = ""; this.draft.program = ""; this.draft.academic_year = ""; this.draft.academic_term = ""; this.draft.batch = ""; this.draft.course = ""; this.draft.students = []; await this.load(true); await this.loadOptions(false); },
		async draftOfferingChanged() { this.draft.course = ""; this.draft.students = []; await this.loadOptions(true); },
		groupBasisChanged() { if (this.draft.group_based_on !== "Course") this.draft.course = ""; },
		isStudentSelected(name) { return this.draft.students.some((row) => row.student === name && Number(row.active ?? 1) === 1); },
		toggleStudent(student) { const row = this.draft.students.find((item) => item.student === student.name); if (row) row.active = Number(row.active ?? 1) === 1 ? 0 : 1; else this.draft.students.push({ student: student.name, student_name: student.student_name || student.name, group_roll_number: "", active: 1 }); },
		studentRoll(name) { return this.draft.students.find((row) => row.student === name)?.group_roll_number || ""; },
		setStudentRoll(name, value) { const row = this.draft.students.find((item) => item.student === name); if (row) row.group_roll_number = value ? Number(value) : ""; },
		async saveClassArm() {
			if (!this.canSave) return;
			this.saving = true; this.saveError = "";
			try {
				const response = await frappe.call({ method: "eduedge.api.class_arms.save_class_arm", type: "POST", args: { class_arm: this.draft.name || undefined, display_name: this.draft.display_name, branch: this.draft.branch, offering: this.draft.offering, group_based_on: this.draft.group_based_on, course: this.draft.course || undefined, max_strength: this.draft.max_strength || 0, disabled: this.draft.disabled ? 1 : 0, students: JSON.stringify((this.draft.students || []).filter((row) => Number(row.active ?? 1) === 1)) } });
				const saved = response.message || {};
				frappe.show_alert({ message: __(`${this.classArmSingular} saved for ${saved.academic_year || 'Academic Session'}`), indicator: "green" });
				this.filters.branch = saved.branch || this.filters.branch; this.filters.academic_year = saved.academic_year || this.filters.academic_year;
				await this.load(true); await this.loadOptions(false); if (saved.name) await this.editClassArm(saved.name);
			} catch (error) { this.saveError = error?.message || `${this.classArmSingular} could not be saved.`; }
			finally { this.saving = false; }
		},
		canCarryForward(row) { return Boolean(this.canCreate && row?.name && !row.disabled && !row.legacy_term_bound && row.academic_year && row.class_arm_identity); },
		laterAcademicYears(sourceYear) {
			if (!sourceYear) return [];
			const rows = [...(this.options.academic_years || [])];
			const source = rows.find((row) => row.name === sourceYear);
			return rows
				.filter((row) => row.name !== sourceYear && (!source?.year_start_date || !row.year_start_date || row.year_start_date > source.year_start_date))
				.sort((a, b) => String(a.year_start_date || a.name).localeCompare(String(b.year_start_date || b.name)));
		},
		carryClassArmForward(row) {
			if (!this.canCarryForward(row)) return;
			const destinations = this.laterAcademicYears(row.academic_year);
			if (!destinations.length) {
				frappe.msgprint({ title: __("No Later Academic Session"), message: __("Create the next Academic Session and its sessional Programme Offering before carrying this Class Arm forward."), indicator: "orange" });
				return;
			}
			frappe.prompt(
				[{ fieldname: "destination_academic_year", fieldtype: "Select", label: this.academicYearSingular, options: destinations.map((item) => item.name).join("\n"), default: destinations[0].name, reqd: 1 }],
				(values) => this.previewSingleCarry(row, values.destination_academic_year),
				__(`Carry ${row.display_name || this.classArmSingular} Forward`),
				__("Preview"),
			);
		},
		async previewSingleCarry(row, destinationAcademicYear) {
			try {
				const response = await frappe.call({ method: "eduedge.api.class_arm_session_rollover.preview_single_class_arm_session_rollover", type: "POST", args: { source: row.name, destination_academic_year: destinationAcademicYear } });
				const preview = response.message || {}; const planRow = preview.row || {};
				if (planRow.status === "blocked") { frappe.msgprint({ title: __("Carry Forward Blocked"), message: __(planRow.reason || "This Class Arm cannot be carried forward."), indicator: "red" }); return; }
				if (planRow.status === "existing") { frappe.msgprint({ title: __("Already Prepared"), message: __(`${row.display_name || this.classArmSingular} already exists in ${destinationAcademicYear}.`), indicator: "blue" }); return; }
				frappe.confirm(
					__(`Prepare ${row.display_name || this.classArmSingular} structure for ${destinationAcademicYear}? ${planRow.source_student_count || 0} current source students will remain in the source Session until Student Progression creates and submits their destination Enrollments.`),
					() => this.executeSingleCarry(row, destinationAcademicYear),
				);
			} catch (error) { frappe.msgprint({ title: __("Carry Forward Could Not Be Previewed"), message: __(error?.message || "The next-session preview failed."), indicator: "red" }); }
		},
		async executeSingleCarry(row, destinationAcademicYear) {
			try {
				const response = await frappe.call({ method: "eduedge.api.class_arm_session_rollover.execute_single_class_arm_session_rollover", type: "POST", args: { source: row.name, destination_academic_year: destinationAcademicYear } });
				const result = response.message || {};
				frappe.show_alert({ message: result.created_count ? __(`${row.display_name || this.classArmSingular} structure prepared for ${destinationAcademicYear}`) : __(`${row.display_name || this.classArmSingular} was already prepared for ${destinationAcademicYear}`), indicator: "green" });
				await this.load(true);
			} catch (error) { frappe.msgprint({ title: __("Carry Forward Failed"), message: __(error?.message || "The Class Arm could not be carried forward."), indicator: "red" }); }
		},
		openBulkRollover() {
			this.bulk.branch = this.filters.branch || this.data.selected_branch?.name || this.bulk.branch;
			this.bulk.source_academic_year = this.filters.academic_year || this.bulk.source_academic_year;
			this.$nextTick(() => this.$refs.bulkRolloverPanel?.scrollIntoView({ behavior: "smooth", block: "start" }));
		},
		bulkSourceChanged() { this.bulk.destination_academic_year = ""; this.resetBulkPreview(); },
		resetBulkPreview() { this.bulk.preview = null; this.bulk.result = null; this.bulk.error = ""; this.bulk.selected_class_arm_identities = []; },
		isBulkSelected(identity) { return (this.bulk.selected_class_arm_identities || []).includes(identity); },
		toggleBulkSelection(identity) { const selected = new Set(this.bulk.selected_class_arm_identities || []); if (selected.has(identity)) selected.delete(identity); else selected.add(identity); this.bulk.selected_class_arm_identities = [...selected]; },
		selectAllBulkReady() { this.bulk.selected_class_arm_identities = (this.bulk.preview?.rows || []).filter((row) => row.status === "ready" && row.class_arm_identity).map((row) => row.class_arm_identity); },
		clearBulkSelection() { this.bulk.selected_class_arm_identities = []; },
		async previewSessionRollover() {
			if (!this.bulkReady) return;
			this.bulk.previewing = true; this.bulk.error = ""; this.bulk.preview = null; this.bulk.result = null; this.bulk.selected_class_arm_identities = [];
			try {
				const response = await frappe.call({ method: "eduedge.api.class_arm_session_rollover.preview_class_arm_session_rollover", type: "POST", args: { branch: this.bulk.branch, source_academic_year: this.bulk.source_academic_year, destination_academic_year: this.bulk.destination_academic_year } });
				this.bulk.preview = response.message || null;
			} catch (error) { this.bulk.error = error?.message || "Next-session Class Arm preparation could not be previewed."; }
			finally { this.bulk.previewing = false; }
		},
		confirmExecuteSessionRollover() {
			if (!this.selectedBulkCount) return;
			frappe.confirm(__(`Prepare ${this.selectedBulkCount} selected ${this.classArmPlural} as empty next-session structures for ${this.bulk.destination_academic_year}? Students remain in the source Session until Student Progression is approved.`), () => this.executeSessionRollover());
		},
		async executeSessionRollover() {
			if (!this.selectedBulkCount) return;
			this.bulk.executing = true; this.bulk.error = "";
			try {
				const response = await frappe.call({ method: "eduedge.api.class_arm_session_rollover.execute_selected_class_arm_session_rollover", type: "POST", args: { branch: this.bulk.branch, source_academic_year: this.bulk.source_academic_year, destination_academic_year: this.bulk.destination_academic_year, class_arm_identities: JSON.stringify(this.bulk.selected_class_arm_identities) } });
				this.bulk.result = response.message || null;
				frappe.show_alert({ message: __(`${this.bulk.result?.created_count || 0} selected ${this.classArmPlural} prepared for the next Academic Session`), indicator: "green" });
				await this.load(true); await this.loadOptions(false); await this.previewSessionRollover();
			} catch (error) { this.bulk.error = error?.message || "Selected next-session Class Arms could not be prepared."; }
			finally { this.bulk.executing = false; }
		},
		rolloverStatusLabel(status) { return status === "ready" ? "Ready" : status === "existing" ? "Already prepared" : "Blocked"; },
		rolloverTone(status) { return status === "ready" ? "success" : status === "existing" ? "neutral" : "danger"; },
		openStudentEnrollments() { if (!this.draft.branch || !this.draft.offering) return; const params = new URLSearchParams({ branch: this.draft.branch, offering: this.draft.offering, mode: "create" }); window.location.href = `/app/eduedge-student-enrollments?${params.toString()}`; },
		openStudentProgression() { const params = new URLSearchParams({ branch: this.bulk.branch || this.filters.branch, academic_year: this.bulk.source_academic_year || this.filters.academic_year }); window.location.href = `/app/eduedge-student-progression?${params.toString()}`; },
		openInstructorAssignments() { if (!this.draft.name) return; const params = new URLSearchParams({ branch: this.draft.branch, offering: this.draft.offering, student_group: this.draft.name }); window.location.href = `/app/eduedge-instructor-assignments?${params.toString()}`; },
		openInstructors() { window.location.href = "/app/eduedge-instructors"; },
		openFullForm(name) { if (name) window.open(`/app/student-group/${encodeURIComponent(name)}`, "_blank", "noopener,noreferrer"); },
		previousPage() { this.data.paging.start = Math.max(0, this.data.paging.start - this.data.paging.page_length); this.load(false); },
		nextPage() { if (this.data.paging.has_more) { this.data.paging.start = this.data.paging.next_start; this.load(false); } },
	},
};
</script>

<style scoped>
.class-arm-filter-grid,.rollover-controls{display:grid;grid-template-columns:repeat(auto-fit,minmax(12rem,1fr));gap:.75rem;width:100%}.class-arm-filter-grid label,.editor label,.rollover-controls label{display:grid;gap:.35rem;font-weight:600}.class-arm-search{grid-column:span 2}.session-rule{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.75rem;margin:1rem 0}.session-rule>div{display:grid;gap:.2rem;padding:.8rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.session-rule span,.class-arm-context span,.rollover-summary span{color:var(--text-muted);font-size:.78rem}.class-arm-layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(24rem,.95fr);gap:1rem;margin-top:1rem}.class-arm-panel{display:grid;gap:1rem;align-content:start;padding:1rem;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}.class-arm-heading,.class-arm-title,.class-arm-subheading,.class-arm-actions,.class-arm-paging,.class-arm-heading-actions,.class-arm-card-actions,.rollover-selection-actions,.rollover-execution-actions{display:flex;align-items:center;justify-content:space-between;gap:.6rem}.class-arm-heading h2,.class-arm-subheading h3{margin:.2rem 0 0}.class-arm-list,.choice-list,.class-arm-roster,.rollover-list{display:grid;gap:.75rem}.class-arm-card{display:grid;gap:.75rem;width:100%;padding:.9rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.class-arm-card:hover,.class-arm-card.is-selected{border-color:var(--primary)}.class-arm-card-main{display:grid;gap:.75rem;width:100%;padding:0;border:0;background:transparent;color:inherit;text-align:left}.class-arm-card-actions{justify-content:flex-end;padding-top:.65rem;border-top:1px solid var(--border-color)}.class-arm-action-note{color:var(--text-muted);font-size:.78rem}.class-arm-title>span,.choice-row span,.rollover-row>div{display:grid;gap:.15rem}.class-arm-title small,.choice-row small,.editor small,.roster-help,.rollover-row small,.bulk-rollover-panel p{color:var(--text-muted)}.class-arm-badges{display:flex;flex-wrap:wrap;gap:.35rem}.class-arm-meta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.5rem;color:var(--text-muted);font-size:.82rem}.class-arm-context,.rollover-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.75rem;padding:.8rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.class-arm-context>div,.rollover-summary>div{display:grid;gap:.15rem}.two-column{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem}.class-arm-check{display:flex!important;align-items:center;gap:.5rem!important;font-weight:500!important}.class-arm-roster{padding-top:.75rem;border-top:1px solid var(--border-color)}.choice-list{max-height:18rem;overflow:auto;padding-right:.25rem}.choice-row{display:grid;grid-template-columns:minmax(0,1fr) 6rem;align-items:center;gap:.75rem;padding:.65rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.choice-row>label{display:flex!important;align-items:center;gap:.6rem!important;font-weight:500!important}.legacy-warning,.rollover-result,.downstream-note{display:grid;gap:.25rem;padding:.8rem;border:1px solid var(--orange-300,#f4b860);border-radius:8px;background:var(--control-bg)}.downstream-note{border-color:var(--border-color)}.downstream-note span{color:var(--text-muted)}.bulk-rollover-panel{margin-top:1rem}.rollover-toolbar{flex-wrap:wrap}.rollover-row{display:grid;grid-template-columns:2rem minmax(12rem,1fr) auto minmax(14rem,1.5fr);gap:.75rem;align-items:center;padding:.7rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.rollover-select{display:flex!important;align-items:center;justify-content:center!important}.class-arm-error{margin:0;color:var(--red-600,#b42318)}@media(max-width:1100px){.class-arm-layout{grid-template-columns:1fr}}@media(max-width:700px){.class-arm-search{grid-column:auto}.session-rule,.class-arm-meta,.class-arm-context,.rollover-summary,.two-column,.choice-row,.rollover-row{grid-template-columns:1fr}.class-arm-heading,.class-arm-title,.class-arm-subheading,.class-arm-actions,.class-arm-paging,.rollover-toolbar{align-items:stretch;flex-direction:column}.class-arm-heading-actions,.class-arm-card-actions,.rollover-selection-actions,.rollover-execution-actions{flex-wrap:wrap;justify-content:flex-start}}
</style>
