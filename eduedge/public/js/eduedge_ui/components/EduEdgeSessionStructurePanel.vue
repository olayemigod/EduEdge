<template>
	<section v-if="launchName" class="session-structure-shell">
		<div class="session-structure-header">
			<div>
				<p class="edge-eyebrow">Guided Session Structure</p>
				<h2>Classes, Class Intakes & Class Arms</h2>
				<p>Validate the Classes intended for {{ academicYear }}, create missing Class Intakes, then prepare next-session Class Arm structure without copying Students.</p>
			</div>
			<button type="button" class="edge-button" :disabled="loading || working" @click="load">{{ loading ? "Refreshing..." : "Refresh" }}</button>
		</div>

		<div v-if="error" class="session-structure-message session-structure-message--error">{{ error }}</div>
		<div v-if="loading && !loaded" class="session-structure-message">Loading Session structure...</div>
		<template v-else-if="loaded">
			<article class="session-structure-card">
				<div class="session-structure-card-header">
					<div><span class="session-structure-step">2</span><div><h3>Class Structure</h3><small>Persistent Institution Classes intended to operate in this Session.</small></div></div>
				<div class="session-structure-summary"><strong>{{ data.summary.classes || 0 }}</strong><span>intended Classes</span></div>
			</div>
			<div v-if="!data.classes.length" class="session-structure-empty">No Institution Classes are available. Create the required Classes before preparing Class Intakes.</div>
			<div v-else class="session-structure-list">
				<div v-for="row in data.classes" :key="row.name" class="session-structure-row">
					<div><strong>{{ row.program_name || row.name }}</strong><small>{{ row.department || "No School Section / Department" }}</small></div>
					<div class="session-structure-row-metrics">
						<span>{{ row.existing_intakes }}/{{ row.expected_intakes }} Intakes</span>
						<span :class="row.missing_intakes ? 'is-warning' : 'is-ready'">{{ row.missing_intakes ? `${row.missing_intakes} missing` : "Ready" }}</span>
					</div>
				</div>
			</div>
			<div class="session-structure-actions">
				<button type="button" class="edge-button" @click="openReview('/app/eduedge-programs')">Review Classes in new tab</button>
			</div>
			<p class="session-structure-rule">Classes are persistent masters. EduEdge validates them here; it does not recreate JSS 1, JSS 2, SS 1, etc. every Session.</p>
			</article>

			<article class="session-structure-card">
				<div class="session-structure-card-header">
					<div><span class="session-structure-step">3</span><div><h3>Class Intakes</h3><small>One sessional Intake per selected Branch + Class.</small></div></div>
				<div class="session-structure-summary"><strong>{{ data.summary.existing_intakes || 0 }}/{{ data.summary.expected_intakes || 0 }}</strong><span>prepared</span></div>
			</div>
			<div class="session-structure-toolbar">
				<div><strong>{{ data.summary.missing_intakes || 0 }} missing</strong><small>Select only the Branch/Class combinations that should operate in {{ academicYear }}.</small></div>
				<div class="session-structure-actions">
					<button type="button" class="edge-button" :disabled="!missingIntakes.length" @click="selectAllMissingIntakes">Select missing</button>
					<button type="button" class="edge-button" :disabled="!selectedIntakeKeys.length" @click="selectedIntakeKeys = []">Clear selection</button>
					<button type="button" class="edge-button edge-button--primary" :disabled="!selectedIntakeKeys.length || working || !data.permissions.can_create_intake" @click="createIntakes">
						{{ workingAction === 'intakes' ? "Creating..." : `Create Selected (${selectedIntakeKeys.length})` }}
					</button>
				</div>
			</div>
			<div v-if="!data.class_intakes.length" class="session-structure-empty">No Branch × Class Intake rows can be prepared yet.</div>
			<div v-else class="session-structure-table-wrap">
				<table class="session-structure-table">
					<thead><tr><th></th><th>Branch</th><th>Class</th><th>School Section</th><th>Source</th><th>Destination status</th></tr></thead>
					<tbody>
						<tr v-for="row in data.class_intakes" :key="row.key">
							<td><input v-if="row.status === 'missing'" v-model="selectedIntakeKeys" type="checkbox" :value="row.key" /></td>
							<td>{{ row.branch_name }}</td>
							<td><strong>{{ row.program_name }}</strong></td>
							<td>{{ row.department || "—" }}</td>
							<td>{{ row.source_offering ? `Previous Intake · capacity ${row.source_capacity || 'unlimited'}` : "New structure" }}</td>
							<td><span :class="['session-structure-badge', row.status === 'existing' ? 'is-ready' : 'is-warning']">{{ row.status === 'existing' ? 'Existing' : 'Missing' }}</span></td>
						</tr>
					</tbody>
				</table>
			</div>
			<div class="session-structure-actions">
				<button type="button" class="edge-button" @click="openReview('/app/eduedge-program-offerings')">Review {{ academicYear }} Intakes in new tab</button>
			</div>
			<p class="session-structure-rule">Bulk creation reuses the validated Class Intake service. Existing Intakes are never duplicated; source structure may supply capacity and delivery defaults, while historical transactions are not copied.</p>
			</article>

			<article class="session-structure-card">
				<div class="session-structure-card-header">
					<div><span class="session-structure-step">4</span><div><h3>Class Arms</h3><small>Structural carry-forward from {{ sourceAcademicYear || 'the source Session' }} to {{ academicYear }}.</small></div></div>
				<div class="session-structure-summary"><strong>{{ data.summary.arms_existing || 0 }}/{{ data.summary.arms_total || 0 }}</strong><span>prepared</span></div>
			</div>
			<div v-if="!sourceAcademicYear" class="session-structure-empty">Choose a Source Academic Session to prepare existing Class Arms for the destination Session.</div>
			<template v-else>
				<div class="session-structure-toolbar">
					<div>
						<strong>{{ data.summary.arms_ready_to_create || 0 }} ready · {{ data.summary.arms_blocked || 0 }} blocked</strong>
						<small>{{ data.summary.source_students || 0 }} source Students shown for planning; Students to carry automatically = {{ data.summary.students_to_carry || 0 }}.</small>
					</div>
					<div class="session-structure-actions">
						<button type="button" class="edge-button" :disabled="!readyArms.length" @click="selectAllReadyArms">Select ready</button>
						<button type="button" class="edge-button" :disabled="!selectedArmKeys.length" @click="selectedArmKeys = []">Clear selection</button>
						<button type="button" class="edge-button edge-button--primary" :disabled="!selectedArmKeys.length || working || !data.permissions.can_create_class_arm" @click="carryArms">
							{{ workingAction === 'arms' ? "Preparing..." : `Carry Forward Selected (${selectedArmKeys.length})` }}
						</button>
					</div>
				</div>
				<div v-if="!data.class_arms.length" class="session-structure-empty">No source Class Arms are available for this source/destination pair, or destination Class Intakes are not prepared yet.</div>
				<div v-else class="session-structure-table-wrap">
					<table class="session-structure-table">
						<thead><tr><th></th><th>Branch</th><th>Class Arm</th><th>Class</th><th>Source Students</th><th>Destination</th></tr></thead>
						<tbody>
							<tr v-for="row in data.class_arms" :key="row.key">
								<td><input v-if="row.status === 'ready'" v-model="selectedArmKeys" type="checkbox" :value="row.key" /></td>
								<td>{{ row.branch_name }}</td>
								<td><strong>{{ row.display_name || row.class_arm_code || row.source || 'Class Arm' }}</strong><small v-if="row.reason" class="row-note">{{ row.reason }}</small></td>
								<td>{{ row.program || "—" }}</td>
								<td>{{ row.source_student_count || 0 }}</td>
								<td><span :class="['session-structure-badge', row.status === 'existing' ? 'is-ready' : row.status === 'ready' ? 'is-warning' : 'is-blocked']">{{ armStatus(row) }}</span></td>
							</tr>
						</tbody>
					</table>
				</div>
			</template>
			<div class="session-structure-actions">
				<button type="button" class="edge-button" @click="openReview('/app/eduedge-class-arms')">Review {{ academicYear }} Class Arms in new tab</button>
			</div>
			<p class="session-structure-rule">Carry-forward creates destination Student Group structure only. Source rosters remain unchanged and destination rosters stay empty until governed Student Progression.</p>
			</article>
		</template>
	</section>
</template>

<script>
const GET_METHOD = "eduedge.api.session_launch_structure.get_session_structure_context";
const CREATE_INTAKES_METHOD = "eduedge.api.session_launch_structure.create_selected_class_intakes";
const CARRY_ARMS_METHOD = "eduedge.api.session_launch_structure.carry_forward_selected_class_arms";

export default {
	name: "EduEdgeSessionStructurePanel",
	props: {
		launchName: { type: String, default: "" },
		academicYear: { type: String, default: "" },
		sourceAcademicYear: { type: String, default: "" },
		institution: { type: String, default: "" },
		branch: { type: String, default: "" },
	},
	data() {
		return {
			loading: false,
			loaded: false,
			working: false,
			workingAction: "",
			error: "",
			data: { classes: [], class_intakes: [], class_arms: [], summary: {}, permissions: {} },
			selectedIntakeKeys: [],
			selectedArmKeys: [],
		};
	},
	computed: {
		missingIntakes() { return (this.data.class_intakes || []).filter((row) => row.status === "missing"); },
		readyArms() { return (this.data.class_arms || []).filter((row) => row.status === "ready"); },
	},
	watch: {
		launchName: {
			immediate: true,
			handler(value) { if (value) this.load(); else this.reset(); },
		},
		sourceAcademicYear() { if (this.launchName) this.load(); },
	},
	methods: {
		reset() {
			this.loaded = false;
			this.error = "";
			this.data = { classes: [], class_intakes: [], class_arms: [], summary: {}, permissions: {} };
			this.selectedIntakeKeys = [];
			this.selectedArmKeys = [];
		},
		async load() {
			if (!this.launchName) return;
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call(GET_METHOD, { launch: this.launchName });
				this.applyContext(response.message || {});
				this.loaded = true;
			} catch (error) {
				this.error = error?.message || "Session structure could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		applyContext(payload) {
			this.data = { classes: [], class_intakes: [], class_arms: [], summary: {}, permissions: {}, ...payload };
			const intakeKeys = new Set((this.data.class_intakes || []).filter((row) => row.status === "missing").map((row) => row.key));
			this.selectedIntakeKeys = this.selectedIntakeKeys.filter((key) => intakeKeys.has(key));
			const armKeys = new Set((this.data.class_arms || []).filter((row) => row.status === "ready").map((row) => row.key));
			this.selectedArmKeys = this.selectedArmKeys.filter((key) => armKeys.has(key));
			this.$emit("structure-updated", this.data.summary || {});
		},
		selectAllMissingIntakes() { this.selectedIntakeKeys = this.missingIntakes.map((row) => row.key); },
		selectAllReadyArms() { this.selectedArmKeys = this.readyArms.map((row) => row.key); },
		selectedIntakeRows() {
			const keys = new Set(this.selectedIntakeKeys);
			return (this.data.class_intakes || []).filter((row) => keys.has(row.key)).map((row) => ({ branch: row.branch, program: row.program }));
		},
		selectedArmRows() {
			const keys = new Set(this.selectedArmKeys);
			return (this.data.class_arms || []).filter((row) => keys.has(row.key)).map((row) => ({ branch: row.branch, class_arm_identity: row.class_arm_identity }));
		},
		async createIntakes() {
			const selections = this.selectedIntakeRows();
			if (!selections.length) return;
			this.working = true;
			this.workingAction = "intakes";
			this.error = "";
			try {
				const response = await frappe.call({ method: CREATE_INTAKES_METHOD, type: "POST", args: { launch: this.launchName, selections: JSON.stringify(selections) } });
				this.applyContext(response.message?.context || {});
				this.selectedIntakeKeys = [];
				frappe.show_alert({ message: __(`${response.message?.created_count || 0} Class Intake(s) created`), indicator: "green" });
			} catch (error) {
				this.error = error?.message || "Selected Class Intakes could not be created.";
			} finally {
				this.working = false;
				this.workingAction = "";
			}
		},
		async carryArms() {
			const selections = this.selectedArmRows();
			if (!selections.length) return;
			this.working = true;
			this.workingAction = "arms";
			this.error = "";
			try {
				const response = await frappe.call({ method: CARRY_ARMS_METHOD, type: "POST", args: { launch: this.launchName, selections: JSON.stringify(selections) } });
				this.applyContext(response.message?.context || {});
				this.selectedArmKeys = [];
				frappe.show_alert({ message: __(`${response.message?.created_count || 0} Class Arm(s) prepared`), indicator: "green" });
			} catch (error) {
				this.error = error?.message || "Selected Class Arms could not be carried forward.";
			} finally {
				this.working = false;
				this.workingAction = "";
			}
		},
		openReview(route) {
			const params = new URLSearchParams();
			if (this.academicYear) {
				params.set("academic_year", this.academicYear);
				params.set("destination_academic_year", this.academicYear);
			}
			if (this.sourceAcademicYear) params.set("source_academic_year", this.sourceAcademicYear);
			if (this.institution) params.set("institution", this.institution);
			if (this.branch) params.set("branch", this.branch);
			window.open(`${route}${params.toString() ? `?${params}` : ""}`, "_blank", "noopener,noreferrer");
		},
		armStatus(row) {
			if (row.status === "existing") return "Prepared";
			if (row.status === "ready") return "Ready to carry forward";
			return "Blocked";
		},
	},
};
</script>

<style scoped>
.session-structure-shell{display:grid;gap:1rem;margin-top:1rem}.session-structure-header{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem}.session-structure-header h2{margin:.1rem 0 .3rem}.session-structure-header p{margin:0;color:var(--text-muted)}
.session-structure-card{display:grid;gap:.85rem;padding:1rem;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}.session-structure-card-header{display:flex;justify-content:space-between;align-items:center;gap:1rem}.session-structure-card-header>div:first-child{display:flex;align-items:center;gap:.7rem}.session-structure-card-header h3{margin:0}.session-structure-card-header small,.session-structure-toolbar small,.session-structure-row small{display:block;color:var(--text-muted)}.session-structure-step{display:grid;place-items:center;width:2rem;height:2rem;border:1px solid var(--border-color);border-radius:999px;font-weight:700}.session-structure-summary{display:grid;text-align:right}.session-structure-summary strong{font-size:1.2rem}.session-structure-summary span{font-size:.78rem;color:var(--text-muted)}
.session-structure-list{display:grid;gap:.45rem}.session-structure-row{display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:.65rem .75rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.session-structure-row-metrics{display:flex;gap:.6rem;align-items:center;font-size:.82rem}.is-ready{color:var(--green-600,#16803c)}.is-warning{color:var(--orange-600,#b54708)}.is-blocked{color:var(--red-600,#b42318)}
.session-structure-toolbar{display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:.7rem;border:1px dashed var(--border-color);border-radius:8px}.session-structure-actions{display:flex;gap:.5rem;flex-wrap:wrap}.session-structure-table-wrap{overflow:auto;border:1px solid var(--border-color);border-radius:8px}.session-structure-table{width:100%;border-collapse:collapse;min-width:760px}.session-structure-table th,.session-structure-table td{padding:.6rem .7rem;border-bottom:1px solid var(--border-color);text-align:left;vertical-align:top}.session-structure-table th{font-size:.78rem;color:var(--text-muted);background:var(--control-bg)}.session-structure-table tr:last-child td{border-bottom:0}.session-structure-badge{display:inline-flex;padding:.2rem .45rem;border:1px solid currentColor;border-radius:999px;font-size:.75rem}.row-note{display:block;margin-top:.15rem;color:var(--red-600,#b42318);max-width:30rem}.session-structure-rule{margin:0;color:var(--text-muted);font-size:.82rem}.session-structure-empty,.session-structure-message{padding:.75rem;border-radius:8px;background:var(--control-bg);color:var(--text-muted)}.session-structure-message--error{color:var(--red-600,#b42318)}
@media(max-width:800px){.session-structure-header,.session-structure-card-header,.session-structure-toolbar,.session-structure-row{align-items:stretch;flex-direction:column}.session-structure-summary{text-align:left}.session-structure-row-metrics{flex-wrap:wrap}}
</style>
