<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="globalInstitutionName"
		:branch-name="globalBranchName"
		:menu-items="menuItems"
		active-route="/app/eduedge-instructor-assignments"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="People & Academic Operations"
					:title="pageTitle"
					:subtitle="pageSubtitle"
					:action-label="canManage ? 'Manage Instructors' : ''"
					@action="openInstructors"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loaded" message="Loading Instructor Assignments..." :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loaded" title="Instructor Assignments could not load" :message="error" action-label="Try again" @retry="load" />
			<template v-else>
				<p v-if="error" class="assignment-error">{{ error }}</p>

				<template v-if="canManage">
				<section class="assignment-panel">
					<div class="assignment-heading">
						<div>
							<p class="edge-eyebrow">Exact responsibility planner</p>
							<h2>Who is being assigned?</h2>
						</div>
						<div class="assignment-actions">
							<button type="button" class="edge-button" @click="addAcademicRow">Add Academic Row</button>
							<button type="button" class="edge-button" @click="addBranchAccessRow">Add Branch Access Row</button>
							<button type="button" class="edge-button" @click="resetPlanner">Reset</button>
						</div>
					</div>

					<label class="instructor-field">
						<span>Instructor *</span>
						<select v-model="instructor" class="form-control" @change="instructorChanged">
							<option value="">Select Instructor</option>
							<option v-for="row in data.instructors" :key="row.name" :value="row.name">
								{{ row.instructor_name || row.name }}{{ row.home_institution_name ? ` · ${row.home_institution_name}` : '' }}{{ row.department ? ` · ${row.department}` : '' }}
							</option>
						</select>
					</label>

					<EdgeActionBar :label="workingScopeLabel" />
					<EdgeActionBar label="Each row owns one Branch and one Class. Multiple Subjects or Class Arms selected inside that row apply only to that row. Classes in another Branch must be added as another row." />
				</section>

				<section class="rows-stack">
					<article v-for="(row, index) in rows" :key="row.row_id" class="assignment-row">
						<div class="assignment-heading">
							<div>
								<p class="edge-eyebrow">Assignment Row {{ index + 1 }}</p>
								<h3>{{ rowTitle(row) }}</h3>
							</div>
							<div class="assignment-actions">
								<button type="button" class="edge-button" @click="duplicateRow(row)">Duplicate</button>
								<button type="button" class="edge-button" :disabled="rows.length === 1" @click="removeRow(index)">Remove</button>
							</div>
						</div>

						<div class="row-grid">
							<label>
								<span>Responsibility Scope *</span>
								<select v-model="row.assignment_scope" class="form-control" @change="scopeChanged(row)">
									<option v-for="scope in data.assignment_scopes" :key="scope" :value="scope">{{ scope }}</option>
								</select>
							</label>
							<label v-if="row.assignment_scope !== branchOnlyScope">
								<span>Assignment Type *</span>
								<select v-model="row.assignment_type" class="form-control" @change="typeChanged(row)">
									<option v-for="value in data.assignment_types" :key="value" :value="value">{{ value }}</option>
								</select>
							</label>
							<label>
								<span>Branch / Campus *</span>
								<select v-model="row.branch" class="form-control" @change="branchChanged(row)">
									<option value="">Select Branch / Campus</option>
									<optgroup v-for="group in branchGroups" :key="group.institution" :label="group.institution_name">
										<option v-for="branch in group.rows" :key="branch.name" :value="branch.name">{{ branch.branch_name || branch.name }}</option>
									</optgroup>
								</select>
							</label>

							<label v-if="row.assignment_scope !== branchOnlyScope" class="wide">
								<span>Class / Programme Offering *</span>
								<select v-model="row.program_offering" class="form-control" :disabled="!row.branch" @change="offeringChanged(row)">
									<option value="">Select Class / Programme Offering</option>
									<option v-for="offering in offeringsFor(row)" :key="offering.name" :value="offering.name">
										{{ offering.offering_title || offering.name }} · {{ offering.academic_year }}{{ offering.academic_term ? ` · ${offering.academic_term}` : '' }}
									</option>
								</select>
							</label>

							<label v-if="row.assignment_scope === classArmScope" class="wide">
								<span>Class Arms *</span>
								<select v-model="row.student_groups" multiple class="form-control multi-select" :disabled="!row.program_offering" @change="invalidatePreview">
									<option v-for="group in groupsFor(row)" :key="group.name" :value="group.name">{{ group.eduedge_display_name || group.student_group_name || group.name }}</option>
								</select>
								<small>Select one or several Class Arms that should receive the same responsibility.</small>
							</label>

							<label v-if="requiresSubjects(row)" class="wide">
								<span>{{ courseLabel(row, true) }} *</span>
								<select v-model="row.courses" multiple class="form-control multi-select" :disabled="!row.program_offering" @change="invalidatePreview">
									<option v-for="course in coursesFor(row)" :key="course.name" :value="course.name">{{ course.course_name || course.name }}</option>
								</select>
								<small>These {{ courseLabel(row, true).toLowerCase() }} apply only to this row's selected Class{{ row.assignment_scope === classArmScope ? ' Arm(s)' : '' }}.</small>
							</label>

							<div v-if="isClassResponsibility(row)" class="row-note wide">
								<strong>Class responsibility</strong>
								<span>{{ row.assignment_type }} does not grant Subject, Topic, CBT or Assessment access. Add a separate Subject Instructor row for academic content responsibility.</span>
							</div>

							<label>
								<span>Valid From</span>
								<input v-model="row.valid_from" type="date" class="form-control" @change="invalidatePreview" />
							</label>
							<label>
								<span>Valid To</span>
								<input v-model="row.valid_to" type="date" class="form-control" @change="invalidatePreview" />
							</label>
							<label>
								<span>Status</span>
								<select v-model.number="row.enabled" class="form-control" @change="invalidatePreview">
									<option :value="1">Active</option>
									<option :value="0">Disabled / planned only</option>
								</select>
							</label>
							<label class="wide">
								<span>Notes</span>
								<textarea v-model.trim="row.notes" rows="2" class="form-control" placeholder="Optional assignment, handover or responsibility note" @input="invalidatePreview"></textarea>
							</label>
						</div>

						<div class="row-summary">
							<span>{{ institutionForRow(row) }}</span>
							<span>{{ branchLabel(row.branch) }}</span>
							<span v-if="row.program_offering">{{ offeringLabel(row.program_offering) }}</span>
							<span v-if="row.student_groups.length">{{ row.student_groups.length }} Class Arm(s)</span>
							<span v-if="row.courses.length">{{ row.courses.length }} {{ courseLabel(row, row.courses.length !== 1) }}</span>
						</div>
					</article>
				</section>

				<section class="assignment-panel">
					<EdgeActionBar label="Preview expands every row into the exact records to be created. Invalid Subject/Class combinations and primary responsibility conflicts block the plan; nothing is silently skipped.">
						<template #actions>
							<button type="button" class="edge-button" :disabled="previewing || !canPreview" @click="previewPlan">{{ previewing ? 'Checking...' : 'Preview Exact Plan' }}</button>
							<button type="button" class="edge-button edge-button--primary" :disabled="saving || !canSave" @click="savePlan">{{ saving ? 'Saving...' : 'Save Instructor Assignments' }}</button>
						</template>
					</EdgeActionBar>
					<p v-if="saveError" class="assignment-error">{{ saveError }}</p>

					<section v-if="preview" class="preview">
						<div class="preview-metrics">
							<div><span>Planner rows</span><strong>{{ preview.row_count }}</strong></div>
							<div><span>Institutions</span><strong>{{ preview.institution_count }}</strong></div>
							<div><span>Academic records</span><strong>{{ preview.academic_record_count }}</strong></div>
							<div><span>New records</span><strong>{{ preview.create_count }}</strong></div>
							<div><span>Existing</span><strong>{{ preview.existing_count }}</strong></div>
							<div><span>Branch access changes</span><strong>{{ preview.branch_change_count }}</strong></div>
							<div><span>Conflicts</span><strong>{{ preview.conflict_count }}</strong></div>
						</div>
						<div v-if="preview.conflicts?.length" class="preview-list danger">
							<strong>Resolve these conflicts before saving</strong>
							<span v-for="(item, index) in preview.conflicts" :key="`${item.name}-${index}`">{{ item.row_id }} · {{ item.label }} · {{ item.reason }}</span>
						</div>
						<div v-if="preview.create?.length" class="preview-list">
							<strong>Exact academic records to create</strong>
							<span v-for="(item, index) in preview.create" :key="`${item.row_id}-${index}`">{{ item.row_id }} · {{ item.label }}</span>
						</div>
						<div v-if="preview.existing?.length" class="preview-list">
							<strong>Exact existing records</strong>
							<span v-for="item in preview.existing" :key="item.name">{{ item.row_id }} · {{ item.label }} · {{ item.name }}</span>
						</div>
					</section>
				</section>
				</template>

				<section v-if="!canManage" class="assignment-panel">
					<EdgeActionBar label="My Teaching Assignments is read-only. Academic administrators manage Branch, Class, Class Arm, Subject and effective-date responsibilities." />
				</section>

				<section v-if="instructor" class="register-layout">
					<article v-if="canManage" class="assignment-panel">
						<div class="assignment-heading">
							<div><p class="edge-eyebrow">Explicit and generated periods</p><h2>Branch Eligibility Periods</h2></div>
							<span>{{ branchEligibilityGroups.length }} Branch{{ branchEligibilityGroups.length === 1 ? '' : 'es' }} · {{ data.branch_assignments.length }} Period{{ data.branch_assignments.length === 1 ? '' : 's' }}</span>
						</div>
						<EdgeEmptyState v-if="!data.branch_assignments.length" title="No Branch eligibility period" description="Active academic rows create only the required contiguous Branch periods. Separate periods remain separate rather than bridging inactive gaps." />
						<div v-else class="branch-eligibility-list">
							<article v-for="group in branchEligibilityGroups" :key="group.school_branch" class="branch-eligibility-group">
								<div class="branch-eligibility-heading">
									<span>
										<strong>{{ institutionForBranch(group.school_branch) }} · {{ branchLabel(group.school_branch) }}</strong>
										<small>{{ group.periods.length }} eligibility period{{ group.periods.length === 1 ? '' : 's' }}</small>
									</span>
								</div>
								<div class="branch-period-list">
									<div v-for="item in group.periods" :key="item.name" class="branch-period-row">
										<span><small>{{ item.valid_from || 'No start restriction' }} → {{ item.valid_to || 'Open ended' }} · {{ item.is_primary ? 'Primary' : 'Additional' }}</small></span>
										<EdgeStatusBadge :label="branchPeriodStatus(item).label" :status="branchPeriodStatus(item).status" :tone="branchPeriodStatus(item).tone" />
									</div>
								</div>
							</article>
						</div>
					</article>

					<article class="assignment-panel">
						<div class="assignment-heading">
							<div><p class="edge-eyebrow">Academic responsibility</p><h2>Current Instructor Assignments</h2></div>
							<span>{{ data.assignments.length }}</span>
						</div>
						<EdgeEmptyState v-if="!data.assignments.length" title="No academic assignment" description="Add exact Class, Class Arm and Subject responsibility rows above." />
						<div v-else class="register-list">
							<article v-for="item in data.assignments" :key="item.name">
								<span>
									<strong>{{ item.assignment_title || item.assignment_type }}</strong>
									<small>{{ institutionForBranch(item.school_branch) }} · {{ branchLabel(item.school_branch) }} · {{ offeringLabel(item.program_offering) }} · {{ item.student_group || 'All Class Arms' }} · {{ courseName(item.course) || 'Whole class' }}</small>
									<small>{{ item.valid_from || 'No start restriction' }} → {{ item.valid_to || 'Open ended' }}</small>
								</span>
								<div class="assignment-actions">
									<EdgeStatusBadge :label="item.enabled ? 'Active' : 'Disabled'" :status="item.enabled ? 'active' : 'disabled'" :tone="item.enabled ? 'success' : 'danger'" />
									<button type="button" class="edge-button" @click="openAssignment(item.name)">Open</button>
								</div>
							</article>
						</div>
					</article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const BRANCH_ONLY_SCOPE = "Branch Access Only";
const CLASS_SCOPE = "Class / Programme Offering";
const CLASS_ARM_SCOPE = "Class Arm";
const SUBJECT_INSTRUCTOR = "Subject Instructor";
// Compatibility labels retained for older static contracts while the live flow is row-based.
const ASSIGNMENT_FLOW_LABELS = Object.freeze(["Institutions and Branches / Campuses", "Classes / Programme Offerings", "Preview Assignment Batch"]);
void ASSIGNMENT_FLOW_LABELS;
let rowSequence = 0;

function nextRowId() {
	rowSequence += 1;
	return `assignment-row-${Date.now()}-${rowSequence}`;
}

function newRow(preset = {}) {
	return {
		row_id: preset.row_id || nextRowId(),
		assignment_scope: preset.assignment_scope || CLASS_ARM_SCOPE,
		assignment_type: preset.assignment_type || SUBJECT_INSTRUCTOR,
		branch: preset.branch || "",
		program_offering: preset.program_offering || "",
		student_groups: Array.isArray(preset.student_groups) ? [...preset.student_groups] : [],
		courses: Array.isArray(preset.courses) ? [...preset.courses] : [],
		valid_from: preset.valid_from || "",
		valid_to: preset.valid_to || "",
		enabled: preset.enabled === 0 ? 0 : 1,
		notes: preset.notes || "",
	};
}

const blankData = () => ({
	allowed_branches: [], selected_branches: [], instructors: [], selected_instructor: null,
	offerings: [], groups: [], courses: [], course_map: {}, assignments: [], branch_assignments: [],
	assignment_types: [], assignment_scopes: [], subject_required_types: [], class_responsibility_types: [], permissions: {},
});

export default {
	name: "EduEdgeInstructorAssignments",
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS,
			loading: true,
			loaded: false,
			previewing: false,
			saving: false,
			error: "",
			saveError: "",
			data: blankData(),
			instructor: "",
			rows: [newRow()],
			preview: null,
			routePresetApplied: false,
		};
	},
	computed: {
		canManage() { return Boolean(this.data.permissions?.can_manage); },
		pageTitle() { return this.canManage ? "Instructor Assignments" : "My Teaching Assignments"; },
		pageSubtitle() { return this.canManage ? "Plan exact Branch, Class, Class Arm and Subject responsibilities without creating unintended combinations." : "Review only your own active and historical teaching responsibilities."; },
		branchOnlyScope() { return BRANCH_ONLY_SCOPE; },
		classScope() { return CLASS_SCOPE; },
		classArmScope() { return CLASS_ARM_SCOPE; },
		globalInstitutionName() { return frappe.boot?.eduedge_ui_identity?.tenant_name || "EduEdge Institution"; },
		globalBranchName() { return frappe.boot?.eduedge_ui_identity?.branch_name || "Select Branch"; },
		branchGroups() {
			const groups = new Map();
			for (const branch of this.data.allowed_branches || []) {
				const key = branch.institution || "unclassified";
				if (!groups.has(key)) groups.set(key, { institution: key, institution_name: branch.institution_name || key, rows: [] });
				groups.get(key).rows.push(branch);
			}
			return [...groups.values()].sort((a, b) => a.institution_name.localeCompare(b.institution_name));
		},
		branchEligibilityGroups() {
			const groups = new Map();
			for (const period of this.data.branch_assignments || []) {
				const key = period.school_branch || "unclassified";
				if (!groups.has(key)) groups.set(key, { school_branch: key, periods: [] });
				groups.get(key).periods.push(period);
			}
			for (const group of groups.values()) {
				group.periods.sort((a, b) => String(b.valid_from || "").localeCompare(String(a.valid_from || "")));
			}
			return [...groups.values()].sort((a, b) => this.branchLabel(a.school_branch).localeCompare(this.branchLabel(b.school_branch)));
		},
		selectedBranches() { return [...new Set(this.rows.map((row) => row.branch).filter(Boolean))]; },
		selectedInstitutions() { return [...new Set(this.selectedBranches.map((name) => this.branchRecord(name)?.institution).filter(Boolean))]; },
		workingScopeLabel() {
			if (!this.selectedBranches.length) return "Working scope: no Branch selected yet. The global header remains your default navigation context.";
			return `Working scope: ${this.selectedInstitutions.length} Institution(s) · ${this.selectedBranches.length} Branch(es) · ${this.rows.length} explicit row(s). The global header remains your default context.`;
		},
		canPreview() { return Boolean(this.canManage && this.instructor && this.rows.length); },
		canSave() { return Boolean(this.canManage && this.preview && !this.preview.conflict_count && (this.preview.create_count || this.preview.existing_count || this.preview.branch_change_count)); },
	},
	mounted() {
		const params = new URLSearchParams(window.location.search || "");
		this.instructor = params.get("instructor") || "";
		this.load().then(() => this.applyRoutePreset({
			branch: params.get("branch") || "",
			program_offering: params.get("offering") || params.get("program_offering") || "",
			student_group: params.get("student_group") || "",
			course: params.get("course") || "",
		}));
	},
	methods: {
		openRoute: openEduEdgeRoute,
		async load() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.instructor_assignments.get_instructor_assignments_page", {
					instructor: this.instructor || undefined,
					branches: this.selectedBranches,
					offerings: this.rows.map((row) => row.program_offering).filter(Boolean),
				});
				this.data = response.message || blankData();
				if (!this.instructor && this.data.selected_instructor?.name) this.instructor = this.data.selected_instructor.name;
				if (this.canManage && !this.rows.some((row) => row.branch) && this.data.selected_branches?.length) this.rows[0].branch = this.data.selected_branches[0];
				this.loaded = true;
			} catch (error) {
				this.error = error?.message || "Instructor Assignments could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		invalidatePreview() { this.preview = null; this.saveError = ""; },
		async instructorChanged() { this.invalidatePreview(); await this.load(); },
		addAcademicRow() {
			this.rows.push(newRow({ branch: this.selectedBranches[0] || this.data.selected_branches?.[0] || "" }));
			this.invalidatePreview();
		},
		addBranchAccessRow() {
			this.rows.push(newRow({ assignment_scope: BRANCH_ONLY_SCOPE, assignment_type: "", branch: this.selectedBranches[0] || this.data.selected_branches?.[0] || "" }));
			this.invalidatePreview();
		},
		duplicateRow(row) {
			this.rows.push(newRow({ ...row, student_groups: row.student_groups, courses: row.courses }));
			this.invalidatePreview();
		},
		removeRow(index) { if (this.rows.length > 1) this.rows.splice(index, 1); this.invalidatePreview(); },
		resetPlanner() {
			this.instructor = "";
			this.rows = [newRow({ branch: this.data.selected_branches?.[0] || "" })];
			this.preview = null;
			this.saveError = "";
			this.load();
		},
		scopeChanged(row) {
			if (row.assignment_scope === BRANCH_ONLY_SCOPE) {
				row.assignment_type = "";
				row.program_offering = "";
				row.student_groups = [];
				row.courses = [];
			} else {
				if (!row.assignment_type) row.assignment_type = SUBJECT_INSTRUCTOR;
				if (row.assignment_scope === CLASS_SCOPE) row.student_groups = [];
			}
			this.invalidatePreview();
		},
		typeChanged(row) {
			if (this.isClassResponsibility(row)) row.courses = [];
			if (["Class Teacher", "Form Teacher"].includes(row.assignment_type)) row.assignment_scope = CLASS_ARM_SCOPE;
			if (row.assignment_type === "Head of Class / Level") { row.assignment_scope = CLASS_SCOPE; row.student_groups = []; }
			this.invalidatePreview();
		},
		branchChanged(row) {
			row.program_offering = "";
			row.student_groups = [];
			row.courses = [];
			this.invalidatePreview();
		},
		offeringChanged(row) {
			row.student_groups = [];
			row.courses = [];
			const offering = this.offeringRecord(row.program_offering);
			if (offering) {
				row.branch = offering.school_branch;
				if (!row.valid_from && offering.period_start_date) row.valid_from = offering.period_start_date;
				if (!row.valid_to && offering.period_end_date) row.valid_to = offering.period_end_date;
			}
			this.invalidatePreview();
		},
		applyRoutePreset(preset = {}) {
			if (this.routePresetApplied || !this.loaded || !this.canManage) return;
			this.routePresetApplied = true;
			if (!preset.branch && !preset.program_offering && !preset.student_group && !preset.course) return;
			const row = newRow({
				branch: preset.branch,
				program_offering: preset.program_offering,
				assignment_scope: preset.student_group ? CLASS_ARM_SCOPE : CLASS_SCOPE,
				student_groups: preset.student_group ? [preset.student_group] : [],
				courses: preset.course ? [preset.course] : [],
			});
			this.rows = [row];
			this.offeringChanged(row);
			if (preset.student_group) row.student_groups = [preset.student_group];
			if (preset.course) row.courses = [preset.course];
			this.invalidatePreview();
		},
		branchRecord(name) { return this.data.allowed_branches.find((row) => row.name === name); },
		offeringRecord(name) { return this.data.offerings.find((row) => row.name === name); },
		branchLabel(name) { return this.branchRecord(name)?.branch_name || name || "Branch"; },
		institutionForBranch(name) { const row = this.branchRecord(name); return row?.institution_name || row?.institution || "Institution"; },
		institutionForRow(row) { return this.institutionForBranch(row.branch); },
		offeringLabel(name) { return this.offeringRecord(name)?.offering_title || name || "Class"; },
		courseName(name) { return this.data.courses.find((row) => row.name === name)?.course_name || name || ""; },
		branchPeriodStatus(item) {
			if (!Number(item.enabled)) return { label: "Disabled", status: "disabled", tone: "danger" };
			const today = frappe.datetime?.get_today?.() || new Date().toISOString().slice(0, 10);
			const start = String(item.valid_from || "").slice(0, 10);
			const end = String(item.valid_to || "").slice(0, 10);
			if (start && today < start) return { label: "Scheduled", status: "scheduled", tone: "warning" };
			if (end && today > end) return { label: "Ended", status: "ended", tone: "neutral" };
			return { label: "Current", status: "current", tone: "success" };
		},
		offeringsFor(row) { return (this.data.offerings || []).filter((offering) => offering.school_branch === row.branch); },
		groupsFor(row) {
			const offering = this.offeringRecord(row.program_offering);
			if (!offering) return [];
			return (this.data.groups || []).filter((group) => {
				if (group.eduedge_program_offering) return group.eduedge_program_offering === offering.name;
				return group.eduedge_school_branch === offering.school_branch && group.program === offering.program && group.academic_year === offering.academic_year && (!group.academic_term || group.academic_term === offering.academic_term);
			});
		},
		coursesFor(row) {
			const offering = this.offeringRecord(row.program_offering);
			if (!offering) return [];
			const names = new Set(this.data.course_map?.[offering.program] || []);
			return (this.data.courses || []).filter((course) => names.has(course.name) && (!course.eduedge_institution || course.eduedge_institution === offering.institution));
		},
		requiresSubjects(row) { return (this.data.subject_required_types || []).includes(row.assignment_type); },
		isClassResponsibility(row) { return (this.data.class_responsibility_types || []).includes(row.assignment_type); },
		courseLabel(row, plural = false) {
			const type = String(this.branchRecord(row.branch)?.institution_type || "").toLowerCase();
			if (type.includes("primary") || type.includes("secondary")) return plural ? "Subjects" : "Subject";
			if (type.includes("tertiary") || type.includes("university") || type.includes("college")) return plural ? "Courses" : "Course";
			if (type.includes("training")) return plural ? "Training Courses" : "Training Course";
			return plural ? "Subjects / Courses" : "Subject / Course";
		},
		rowTitle(row) {
			if (row.assignment_scope === BRANCH_ONLY_SCOPE) return `${this.branchLabel(row.branch)} · Branch access`;
			return `${row.assignment_type || 'Academic responsibility'} · ${this.offeringLabel(row.program_offering)}`;
		},
		payload() { return { instructor: this.instructor, rows: this.rows.map((row, index) => ({ ...row, row_label: `Assignment Row ${index + 1}` })) }; },
		async previewPlan() {
			if (!this.canPreview) return;
			this.previewing = true;
			this.saveError = "";
			try {
				const response = await frappe.call({
					method: "eduedge.api.instructor_assignments.preview_instructor_assignment_batch",
					type: "POST",
					args: { payload: JSON.stringify(this.payload()) },
				});
				this.preview = response.message || null;
			} catch (error) {
				this.preview = null;
				this.saveError = error?.message || "Instructor Assignment plan could not be previewed.";
			} finally {
				this.previewing = false;
			}
		},
		async savePlan() {
			if (!this.canSave) return;
			this.saving = true;
			this.saveError = "";
			try {
				const response = await frappe.call({
					method: "eduedge.api.instructor_assignments.save_instructor_assignment_batch",
					type: "POST",
					args: { payload: JSON.stringify(this.payload()) },
				});
				const summary = response.message?.summary || {};
				frappe.show_alert({ message: __(`${summary.assignments_created || 0} Instructor Assignment(s) created from ${summary.rows_processed || this.rows.length} explicit row(s)`), indicator: "green" });
				this.preview = null;
				await this.load();
			} catch (error) {
				this.saveError = error?.message || "Instructor Assignments could not be saved.";
			} finally {
				this.saving = false;
			}
		},
		openInstructors() { window.location.href = "/app/eduedge-instructors"; },
		openAssignment(name) { window.open(`/app/eduedge-instructor-assignment/${encodeURIComponent(name)}`, "_blank", "noopener,noreferrer"); },
	},
};
</script>

<style scoped>
.assignment-panel,.assignment-row{display:grid;gap:1rem;align-content:start;padding:1rem;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}.rows-stack{display:grid;gap:1rem;margin:1rem 0}.assignment-row{border-left:4px solid var(--primary)}.assignment-heading,.assignment-actions,.row-summary{display:flex;align-items:center;justify-content:space-between;gap:.75rem;flex-wrap:wrap}.assignment-heading h2,.assignment-heading h3{margin:.2rem 0 0}.instructor-field{display:grid;gap:.35rem;font-weight:600;max-width:52rem}.row-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.75rem}.row-grid label{display:grid;gap:.35rem;font-weight:600}.row-grid .wide{grid-column:1/-1}.multi-select{min-height:8rem}.row-note{display:grid;gap:.25rem;padding:.75rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.row-note span,.row-summary{color:var(--text-muted)}.row-summary{justify-content:flex-start;font-size:.8rem}.row-summary span{padding:.25rem .5rem;border-radius:999px;background:var(--control-bg)}.preview{display:grid;gap:.75rem;margin-top:1rem}.preview-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(8rem,1fr));gap:.65rem}.preview-metrics>div{display:grid;gap:.2rem;padding:.75rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.preview-metrics span{color:var(--text-muted);font-size:.75rem}.preview-metrics strong{font-size:1.3rem}.preview-list,.register-list,.branch-eligibility-list,.branch-period-list{display:grid;gap:.6rem}.preview-list{padding:.75rem;border:1px solid var(--border-color);border-radius:8px}.preview-list.danger{border-color:var(--red-400)}.preview-list span{display:block}.register-layout{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin-top:1rem}.register-list article{display:flex;align-items:center;justify-content:space-between;gap:.75rem;padding:.7rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.register-list article>span{display:grid;gap:.15rem}.register-list small{color:var(--text-muted)}.branch-eligibility-group{display:grid;gap:.65rem;padding:.75rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.branch-eligibility-heading{display:flex;align-items:center;justify-content:space-between;gap:.75rem}.branch-eligibility-heading>span,.branch-period-row>span{display:grid;gap:.15rem}.branch-eligibility-heading small,.branch-period-row small{color:var(--text-muted)}.branch-period-row{display:flex;align-items:center;justify-content:space-between;gap:.75rem;padding:.6rem;border:1px solid var(--border-color);border-radius:8px;background:var(--card-bg)}.assignment-error{color:var(--red-600,#b42318)}@media(max-width:900px){.row-grid,.register-layout{grid-template-columns:1fr}.row-grid .wide{grid-column:auto}}@media(max-width:600px){.assignment-heading,.register-list article,.branch-eligibility-heading,.branch-period-row{align-items:stretch;flex-direction:column}}
</style>
