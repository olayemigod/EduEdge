<template>
	<section class="eduedge-assignment-register-filters" data-eduedge-assignment-register-filters>
		<div class="eduedge-register-filter-heading">
			<div>
				<p class="edge-eyebrow">Smart register filters</p>
				<strong>Find current, upcoming and historical responsibilities without loading the whole register.</strong>
			</div>
			<button type="button" class="edge-button" :disabled="busy" @click="resetFilters">Clear Filters</button>
		</div>

		<div class="eduedge-register-presets" aria-label="Instructor Assignment smart presets">
			<button
				v-for="preset in presets"
				:key="preset.value"
				type="button"
				class="eduedge-register-preset"
				:class="{ 'is-active': draft.preset === preset.value && !draft.lifecycle_status }"
				:disabled="busy"
				@click="applyPreset(preset.value)"
			>
				{{ preset.label }}
			</button>
		</div>

		<div class="eduedge-register-status-counts">
			<button
				v-for="status in statuses"
				:key="status"
				type="button"
				class="eduedge-register-count"
				:class="{ 'is-active': draft.lifecycle_status === status }"
				:disabled="busy"
				@click="filterStatus(status)"
			>
				<span>{{ status }}</span>
				<strong>{{ register.counts?.[status] || 0 }}</strong>
			</button>
		</div>

		<div class="eduedge-register-filter-grid">
			<label>
				<span>Instructor</span>
				<select v-model="draft.instructor" class="form-control" :disabled="busy || !canManage" @change="instructorChanged">
					<option value="">Select Instructor</option>
					<option v-for="row in instructors" :key="row.name" :value="row.name">{{ row.instructor_name || row.name }}</option>
				</select>
			</label>

			<label>
				<span>Branch / Campus</span>
				<select v-model="draft.branch" class="form-control" :disabled="busy" @change="branchChanged">
					<option value="">All available Branches</option>
					<option v-for="row in branches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option>
				</select>
			</label>

			<label>
				<span>Academic Session</span>
				<select v-model="draft.academic_year" class="form-control" :disabled="busy" @change="academicYearChanged">
					<option value="">All Sessions</option>
					<option v-for="value in academicYears" :key="value" :value="value">{{ value }}</option>
				</select>
			</label>

			<label>
				<span>Term / Semester</span>
				<select v-model="draft.academic_term" class="form-control" :disabled="busy || !draft.academic_year" @change="academicTermChanged">
					<option value="">All Terms / Semesters</option>
					<option v-for="value in academicTerms" :key="value" :value="value">{{ value }}</option>
				</select>
			</label>

			<label class="wide">
				<span>Class / Programme Offering</span>
				<select v-model="draft.program_offering" class="form-control" :disabled="busy" @change="offeringChanged">
					<option value="">All Classes / Programme Offerings</option>
					<option v-for="row in offeringOptions" :key="row.name" :value="row.name">{{ row.offering_title || row.program || row.name }}</option>
				</select>
			</label>

			<label>
				<span>Class Arm</span>
				<select v-model="draft.student_group" class="form-control" :disabled="busy || !draft.program_offering" @change="invalidatePreset">
					<option value="">All Class Arms</option>
					<option v-for="row in groupOptions" :key="row.name" :value="row.name">{{ row.eduedge_display_name || row.student_group_name || row.name }}</option>
				</select>
			</label>

			<label>
				<span>Subject / Course</span>
				<select v-model="draft.course" class="form-control" :disabled="busy || !draft.program_offering" @change="invalidatePreset">
					<option value="">All Subjects / Courses</option>
					<option v-for="row in courseOptions" :key="row.name" :value="row.name">{{ row.course_name || row.name }}</option>
				</select>
			</label>

			<label>
				<span>Assignment Type</span>
				<select v-model="draft.assignment_type" class="form-control" :disabled="busy" @change="invalidatePreset">
					<option value="">All Types</option>
					<option v-for="value in assignmentTypes" :key="value" :value="value">{{ value }}</option>
				</select>
			</label>

			<label>
				<span>Assignment Scope</span>
				<select v-model="draft.assignment_scope" class="form-control" :disabled="busy" @change="invalidatePreset">
					<option value="">All Scopes</option>
					<option v-for="value in assignmentScopes" :key="value" :value="value">{{ value }}</option>
				</select>
			</label>

			<label>
				<span>Lifecycle Status</span>
				<select v-model="draft.lifecycle_status" class="form-control" :disabled="busy" @change="statusChanged">
					<option value="">Preset / All Statuses</option>
					<option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
				</select>
			</label>

			<label>
				<span>Origin</span>
				<select v-model="draft.origin" class="form-control" :disabled="busy" @change="invalidatePreset">
					<option value="">Any Origin</option>
					<option value="Normal">Normal assignment</option>
					<option value="Prepared">Prepared from earlier period</option>
					<option value="Replacement">Replacement / Handover</option>
					<option value="Transfer">Transfer</option>
				</select>
			</label>

			<label>
				<span>History From</span>
				<input v-model="draft.date_from" type="date" class="form-control" :disabled="busy" @change="invalidatePreset" />
			</label>

			<label>
				<span>History To</span>
				<input v-model="draft.date_to" type="date" class="form-control" :disabled="busy" @change="invalidatePreset" />
			</label>

			<label class="wide">
				<span>Search</span>
				<input
					v-model.trim="draft.search_text"
					type="search"
					class="form-control"
					placeholder="Instructor, Class, Subject, Branch, Assignment Type..."
					:disabled="busy"
					@keyup.enter="applyFilters"
				/>
			</label>
		</div>

		<div v-if="activeChips.length" class="eduedge-register-chips">
			<button v-for="chip in activeChips" :key="chip.key" type="button" :disabled="busy" @click="clearChip(chip.key)">
				{{ chip.label }} ×
			</button>
		</div>

		<div class="eduedge-register-filter-footer">
			<div>
				<strong v-if="register.total">Showing {{ register.from_row }}–{{ register.to_row }} of {{ register.total }} assignment{{ register.total === 1 ? '' : 's' }}</strong>
				<strong v-else>No assignments match the current filters</strong>
				<small v-if="register.scan_truncated">The register scan reached {{ register.max_filter_scan }} rows. Narrow the filters for complete history beyond this range.</small>
			</div>
			<div class="eduedge-register-pagination">
				<button type="button" class="edge-button" :disabled="busy || !register.has_previous" @click="previousPage">Previous</button>
				<span>Page {{ register.page || 1 }} of {{ register.page_count || 1 }}</span>
				<button type="button" class="edge-button" :disabled="busy || !register.has_next" @click="nextPage">Next</button>
				<button type="button" class="edge-button edge-button--primary" :disabled="busy" @click="applyFilters">{{ busy ? 'Filtering...' : 'Apply Filters' }}</button>
			</div>
		</div>
	</section>
</template>

<script>
const STATUSES = ["Current", "Scheduled", "Ended", "Replaced", "Transferred", "Disabled"];
const PRESETS = [
	{ value: "current_upcoming", label: "Current + Upcoming" },
	{ value: "current", label: "Current" },
	{ value: "scheduled", label: "Scheduled" },
	{ value: "ended", label: "Ended" },
	{ value: "replaced", label: "Replaced / Handed Over" },
	{ value: "transferred", label: "Transferred" },
	{ value: "prepared", label: "Prepared for Next Period" },
	{ value: "all", label: "All History" },
];

function unique(values) {
	return [...new Set(values.filter(Boolean))];
}

export default {
	name: "InstructorAssignmentRegisterFilters",
	props: {
		controller: { type: Object, required: true },
	},
	data() {
		return {
			draft: { ...(this.controller.registerFilters || {}) },
		};
	},
	computed: {
		busy() { return Boolean(this.controller.registerFilterLoading || this.controller.loading); },
		canManage() { return Boolean(this.controller.canManage); },
		register() { return this.controller.registerMeta || {}; },
		statuses() { return STATUSES; },
		presets() { return PRESETS; },
		instructors() { return this.controller.data?.instructors || []; },
		branches() { return this.controller.data?.allowed_branches || []; },
		offerings() { return this.controller.data?.offerings || []; },
		groups() { return this.controller.data?.groups || []; },
		courses() { return this.controller.data?.courses || []; },
		assignmentTypes() { return this.controller.data?.assignment_types || []; },
		assignmentScopes() { return (this.controller.data?.assignment_scopes || []).filter((value) => value !== "Branch Access Only"); },
		academicYears() {
			return unique(this.offerings
				.filter((row) => !this.draft.branch || row.school_branch === this.draft.branch)
				.map((row) => row.academic_year)).sort().reverse();
		},
		academicTerms() {
			return unique(this.offerings
				.filter((row) => !this.draft.branch || row.school_branch === this.draft.branch)
				.filter((row) => !this.draft.academic_year || row.academic_year === this.draft.academic_year)
				.map((row) => row.academic_term));
		},
		offeringOptions() {
			return this.offerings
				.filter((row) => !this.draft.branch || row.school_branch === this.draft.branch)
				.filter((row) => !this.draft.academic_year || row.academic_year === this.draft.academic_year)
				.filter((row) => !this.draft.academic_term || row.academic_term === this.draft.academic_term);
		},
		selectedOffering() {
			return this.offerings.find((row) => row.name === this.draft.program_offering) || null;
		},
		groupOptions() {
			if (!this.selectedOffering) return [];
			const offering = this.selectedOffering;
			return this.groups.filter((row) => {
				const linked = row.eduedge_program_offering || row.program_offering || "";
				if (linked) return linked === offering.name;
				return (row.eduedge_school_branch || row.school_branch) === offering.school_branch
					&& (!row.program || row.program === offering.program)
					&& (!row.academic_year || row.academic_year === offering.academic_year)
					&& (!row.academic_term || row.academic_term === offering.academic_term);
			});
		},
		courseOptions() {
			if (!this.selectedOffering) return [];
			const configured = new Set(this.controller.data?.configured_course_map?.[this.selectedOffering.program] || []);
			return this.courses.filter((row) => configured.has(row.name));
		},
		activeChips() {
			const labels = {
				branch: this.branchLabel(this.draft.branch),
				academic_year: this.draft.academic_year,
				academic_term: this.draft.academic_term,
				program_offering: this.offeringLabel(this.draft.program_offering),
				student_group: this.groupLabel(this.draft.student_group),
				course: this.courseLabel(this.draft.course),
				assignment_type: this.draft.assignment_type,
				assignment_scope: this.draft.assignment_scope,
				lifecycle_status: this.draft.lifecycle_status,
				origin: this.draft.origin,
				date_from: this.draft.date_from ? `From ${this.draft.date_from}` : "",
				date_to: this.draft.date_to ? `To ${this.draft.date_to}` : "",
				search_text: this.draft.search_text ? `Search: ${this.draft.search_text}` : "",
			};
			return Object.entries(labels)
				.filter(([, label]) => Boolean(label))
				.map(([key, label]) => ({ key, label }));
		},
	},
	methods: {
		branchLabel(name) { return this.branches.find((row) => row.name === name)?.branch_name || ""; },
		offeringLabel(name) { const row = this.offerings.find((item) => item.name === name); return row?.offering_title || row?.program || ""; },
		groupLabel(name) { const row = this.groups.find((item) => item.name === name); return row?.eduedge_display_name || row?.student_group_name || ""; },
		courseLabel(name) { return this.courses.find((row) => row.name === name)?.course_name || ""; },
		invalidatePreset() {
			this.draft.lifecycle_status = this.draft.lifecycle_status || "";
		},
		instructorChanged() {
			this.draft.branch = "";
			this.draft.academic_year = "";
			this.draft.academic_term = "";
			this.draft.program_offering = "";
			this.draft.student_group = "";
			this.draft.course = "";
		},
		branchChanged() {
			this.draft.academic_year = "";
			this.draft.academic_term = "";
			this.draft.program_offering = "";
			this.draft.student_group = "";
			this.draft.course = "";
		},
		academicYearChanged() {
			this.draft.academic_term = "";
			this.draft.program_offering = "";
			this.draft.student_group = "";
			this.draft.course = "";
		},
		academicTermChanged() {
			this.draft.program_offering = "";
			this.draft.student_group = "";
			this.draft.course = "";
		},
		offeringChanged() {
			this.draft.student_group = "";
			this.draft.course = "";
			const offering = this.selectedOffering;
			if (offering) {
				this.draft.branch = offering.school_branch || this.draft.branch;
				this.draft.academic_year = offering.academic_year || this.draft.academic_year;
				this.draft.academic_term = offering.academic_term || this.draft.academic_term;
			}
		},
		statusChanged() {
			if (this.draft.lifecycle_status) this.draft.preset = "all";
		},
		filterStatus(status) {
			this.draft.lifecycle_status = this.draft.lifecycle_status === status ? "" : status;
			this.draft.preset = "all";
			this.applyFilters();
		},
		applyPreset(value) {
			this.draft.preset = value;
			this.draft.lifecycle_status = "";
			this.applyFilters();
		},
		clearChip(key) {
			this.draft[key] = "";
			if (key === "branch") this.branchChanged();
			if (key === "academic_year") this.academicYearChanged();
			if (key === "academic_term") this.academicTermChanged();
			if (key === "program_offering") this.offeringChanged();
		},
		applyFilters() {
			this.controller.applyRegisterFilters?.({ ...this.draft });
		},
		resetFilters() {
			this.draft = this.controller.defaultRegisterFilters?.() || {};
			this.controller.applyRegisterFilters?.({ ...this.draft });
		},
		previousPage() { this.controller.setRegisterPage?.((this.register.page || 1) - 1); },
		nextPage() { this.controller.setRegisterPage?.((this.register.page || 1) + 1); },
	},
};
</script>

<style scoped>
.eduedge-assignment-register-filters { border: 1px solid var(--edge-color-border, #d8e2ee); border-radius: 12px; display: grid; gap: .85rem; margin: .85rem 0 1rem; padding: .9rem; }
.eduedge-register-filter-heading, .eduedge-register-filter-footer { align-items: center; display: flex; gap: .75rem; justify-content: space-between; }
.eduedge-register-filter-heading > div, .eduedge-register-filter-footer > div:first-child { display: grid; gap: .2rem; }
.eduedge-register-filter-heading strong { font-size: .83rem; }
.eduedge-register-filter-heading p { margin: 0; }
.eduedge-register-presets, .eduedge-register-status-counts, .eduedge-register-chips { display: flex; flex-wrap: wrap; gap: .4rem; }
.eduedge-register-preset, .eduedge-register-count, .eduedge-register-chips button { background: var(--edge-color-surface-subtle, #f6f9fc); border: 1px solid var(--edge-color-border, #d8e2ee); border-radius: 999px; cursor: pointer; font-size: .7rem; font-weight: 700; padding: .34rem .58rem; }
.eduedge-register-preset.is-active, .eduedge-register-count.is-active { border-color: var(--edge-color-brand-500, #2e7bc4); color: var(--edge-color-brand-700, #12558f); }
.eduedge-register-count { align-items: center; display: inline-flex; gap: .35rem; }
.eduedge-register-count strong { font-size: .76rem; }
.eduedge-register-filter-grid { display: grid; gap: .7rem; grid-template-columns: repeat(4, minmax(0, 1fr)); }
.eduedge-register-filter-grid label { display: grid; gap: .32rem; min-width: 0; }
.eduedge-register-filter-grid label > span { font-size: .7rem; font-weight: 800; }
.eduedge-register-filter-grid .wide { grid-column: span 2; }
.eduedge-register-filter-footer small { color: var(--edge-color-ink-500, #687a90); font-size: .68rem; }
.eduedge-register-pagination { align-items: center; display: flex; flex-wrap: wrap; gap: .45rem; justify-content: flex-end; }
.eduedge-register-pagination span { font-size: .72rem; font-weight: 700; }
@media (max-width: 900px) { .eduedge-register-filter-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 600px) { .eduedge-register-filter-heading, .eduedge-register-filter-footer { align-items: stretch; flex-direction: column; } .eduedge-register-filter-grid { grid-template-columns: 1fr; } .eduedge-register-filter-grid .wide { grid-column: auto; } .eduedge-register-pagination { justify-content: flex-start; } }
</style>
