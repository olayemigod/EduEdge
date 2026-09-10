<template>
	<section v-if="launchName" class="session-learners-shell">
		<div class="session-learners-header">
			<div>
				<p class="edge-eyebrow">Guided Learner Preparation</p>
				<h2>Progression, Admissions & Enrollment</h2>
				<p>Move returning Students through governed Progression, prepare new-admission windows, and create destination Enrollment drafts without bypassing normal submission controls.</p>
			</div>
			<button type="button" class="edge-button" :disabled="loading || working" @click="load">{{ loading ? "Refreshing..." : "Refresh" }}</button>
		</div>

		<div v-if="error" class="session-learners-message session-learners-message--error">{{ error }}</div>
		<div v-if="loading && !loaded" class="session-learners-message">Loading learner readiness...</div>
		<template v-else-if="loaded">
			<article class="session-learners-card">
				<div class="session-learners-card-header">
					<div><span class="session-learners-step">5</span><div><h3>Student Progression</h3><small>Returning Students from {{ sourceAcademicYear || "the source Session" }} into {{ academicYear }}.</small></div></div>
					<div class="session-learners-summary"><strong>{{ data.summary.finalized || 0 }}/{{ data.summary.source_enrollments || 0 }}</strong><span>decisions finalised</span></div>
				</div>

				<div v-if="!sourceAcademicYear" class="session-learners-empty">Choose a Source Academic Session to review returning Students.</div>
				<template v-else>
					<div class="session-learners-toolbar">
						<div>
							<strong>{{ data.summary.decision_required || 0 }} decision required · {{ data.summary.draft_prepared || 0 }} draft prepared · {{ data.summary.target_submitted || 0 }} ready to finalise</strong>
							<small>{{ data.summary.review_required || 0 }} learner(s) require additional evidence or a manual academic decision.</small>
						</div>
						<div class="session-learners-actions">
							<button type="button" class="edge-button" @click="$emit('save-step', 'student_progression')">Save here</button>
							<button type="button" class="edge-button" @click="openReview('/app/eduedge-student-progression', { source_academic_year: sourceAcademicYear })">Review Progression in new tab</button>
						</div>
					</div>

					<div v-if="!data.progression.length" class="session-learners-empty">No submitted source-session Enrollments are currently available in your Branch scope.</div>
					<div v-else class="session-learners-table-wrap">
						<table class="session-learners-table">
							<thead><tr><th>Student</th><th>Branch</th><th>Current Class</th><th>Recommendation</th><th>Destination state</th><th>Action</th></tr></thead>
							<tbody>
								<tr v-for="row in data.progression" :key="row.name">
									<td><strong>{{ row.student_name || row.student }}</strong><small>{{ row.student }}</small></td>
									<td>{{ row.branch_name }}</td>
									<td><strong>{{ row.program_label || row.program }}</strong><small>{{ row.source_student_group?.student_group_name || row.source_student_group?.name || "No source Class Arm" }}</small></td>
									<td><span :class="['session-learners-badge', recommendationTone(row)]">{{ row.recommendation?.label || "Review Required" }}</span><small>{{ row.recommendation?.reason || "" }}</small></td>
									<td><span :class="['session-learners-badge', progressionTone(row)]">{{ progressionLabel(row) }}</span><small v-if="row.planned_target?.name">{{ row.planned_target.name }}</small></td>
									<td>
										<div class="session-learners-actions">
											<button v-if="row.launch_state === 'decision_required'" type="button" class="edge-button edge-button--primary" :disabled="working || !data.permissions.can_prepare_progression" @click="prepareProgression(row)">Prepare Draft</button>
											<button v-if="row.launch_state === 'draft_prepared' && row.planned_target?.name" type="button" class="edge-button" @click="openNative('program-enrollment', row.planned_target.name)">Open Draft</button>
											<button v-if="row.launch_state === 'target_submitted'" type="button" class="edge-button edge-button--primary" :disabled="working || !data.permissions.can_finalize_progression" @click="finalizeProgression(row)">Finalize</button>
										</div>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</template>
				<p class="session-learners-rule"><strong>Governance:</strong> Prepare Draft never submits the destination Program Enrollment. A user must review and submit that Enrollment normally before Finalize can record the progression decision and place the Student into the selected destination Class Arm.</p>
			</article>

			<article class="session-learners-card">
				<div class="session-learners-card-header">
					<div><span class="session-learners-step">6</span><div><h3>Admissions & Enrollment</h3><small>Prepare new Student intake separately from returning Student Progression.</small></div></div>
					<div class="session-learners-summary"><strong>{{ data.summary.submitted_enrollments || 0 }}</strong><span>submitted destination Enrollments</span></div>
				</div>

				<div class="session-learners-subsection">
					<div class="session-learners-subheading">
						<div><h4>Admission Cycles</h4><small>Only Branches with admission-enabled Class Intakes require an admission cycle.</small></div>
						<div class="session-learners-actions">
							<button type="button" class="edge-button" @click="$emit('save-step', 'admissions_enrollment')">Save here</button>
							<button type="button" class="edge-button" @click="openReview('/app/eduedge-admissions')">Review Admissions in new tab</button>
						</div>
					</div>
					<div class="session-learners-list">
						<div v-for="row in data.admission_branches" :key="row.branch" class="session-learners-row">
							<div><strong>{{ row.branch_name }}</strong><small>{{ row.program_count }} admission-enabled Class Intake(s)</small></div>
							<div class="session-learners-row-side">
								<span :class="['session-learners-badge', row.status === 'ready' ? 'is-ready' : row.status === 'missing' ? 'is-warning' : 'is-neutral']">{{ admissionBranchLabel(row) }}</span>
								<button v-if="row.status === 'missing'" type="button" class="edge-button edge-button--primary" :disabled="working || !data.permissions.can_create_admission" @click="createAdmission(row)">Create Admission Cycle</button>
							</div>
						</div>
					</div>
					<div class="session-learners-metrics">
						<span><small>Applicants</small><strong>{{ data.summary.applicants_total || 0 }}</strong></span>
						<span><small>Applied</small><strong>{{ data.summary.applicants_applied || 0 }}</strong></span>
						<span><small>Approved</small><strong>{{ data.summary.applicants_approved || 0 }}</strong></span>
						<span><small>Admitted</small><strong>{{ data.summary.applicants_admitted || 0 }}</strong></span>
						<span><small>Rejected</small><strong>{{ data.summary.applicants_rejected || 0 }}</strong></span>
					</div>
					<div class="session-learners-actions"><button type="button" class="edge-button" @click="openReview('/app/eduedge-applicants')">Review Applicants in new tab</button></div>
				</div>

				<div class="session-learners-subsection">
					<div class="session-learners-subheading">
						<div><h4>Destination Enrollments</h4><small>Use direct Enrollment only for new/admitted Students. Returning Students must use Student Progression above.</small></div>
						<div class="session-learners-actions">
							<button type="button" class="edge-button edge-button--primary" :disabled="working || !data.permissions.can_create_enrollment" @click="createEnrollment">New Enrollment Draft</button>
							<button type="button" class="edge-button" @click="openReview('/app/eduedge-student-enrollments')">Review Enrollments in new tab</button>
						</div>
					</div>
					<div class="session-learners-metrics">
						<span><small>Draft</small><strong>{{ data.summary.draft_enrollments || 0 }}</strong></span>
						<span><small>Submitted</small><strong>{{ data.summary.submitted_enrollments || 0 }}</strong></span>
						<span><small>Returning / Progression</small><strong>{{ data.summary.progression_enrollments || 0 }}</strong></span>
						<span><small>New / Direct</small><strong>{{ data.summary.direct_enrollments || 0 }}</strong></span>
						<span><small>Submitted but unassigned</small><strong>{{ data.summary.submitted_unassigned || 0 }}</strong></span>
					</div>
					<div v-if="!data.enrollments.length" class="session-learners-empty">No destination-session Enrollments are available yet.</div>
					<div v-else class="session-learners-table-wrap">
						<table class="session-learners-table">
							<thead><tr><th>Student</th><th>Class</th><th>Type</th><th>Status</th><th>Class Arm</th><th></th></tr></thead>
							<tbody>
								<tr v-for="row in data.enrollments.slice(0, 100)" :key="row.name">
									<td><strong>{{ row.student_name || row.student }}</strong><small>{{ row.student }}</small></td>
									<td>{{ row.program }}</td>
									<td>{{ row.source_type }}</td>
									<td><span :class="['session-learners-badge', row.docstatus === 1 ? 'is-ready' : 'is-warning']">{{ row.status_label }}</span></td>
									<td>{{ row.assigned ? row.assigned_groups.join(', ') : "Unassigned" }}</td>
									<td><button type="button" class="edge-button" @click="openNative('program-enrollment', row.name)">Open</button></td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>
				<p class="session-learners-rule">Session Launch creates new direct Program Enrollments as <strong>Draft</strong> only. Submission remains the normal Frappe Education approval action. A returning Student with a submitted source-session Enrollment is blocked from this shortcut and must go through Student Progression.</p>
			</article>
		</template>
	</section>
</template>

<script>
const GET_METHOD = "eduedge.api.session_launch_learners.get_session_learner_context";
const OPTIONS_METHOD = "eduedge.api.session_launch_learners.get_guided_progression_options";
const PREPARE_METHOD = "eduedge.api.session_launch_learners.prepare_guided_progression";
const FINALIZE_METHOD = "eduedge.api.session_launch_learners.finalize_guided_progression";
const ADMISSION_METHOD = "eduedge.api.session_launch_learners.create_guided_admission_cycle";
const ENROLLMENT_METHOD = "eduedge.api.session_launch_learners.create_guided_enrollment_draft";
const STUDENT_QUERY = "eduedge.api.session_launch_learners.search_launch_students";

export default {
	name: "EduEdgeSessionLearnersPanel",
	props: {
		launchName: { type: String, default: "" },
		academicYear: { type: String, default: "" },
		sourceAcademicYear: { type: String, default: "" },
		institution: { type: String, default: "" },
		branch: { type: String, default: "" },
	},
	emits: ["save-step", "learners-updated"],
	data() {
		return {
			loading: false,
			loaded: false,
			working: false,
			error: "",
			data: { branches: [], target_offerings: [], progression: [], admission_branches: [], admission_cycles: [], applicants: [], enrollments: [], summary: {}, permissions: {} },
		};
	},
	watch: {
		launchName: { immediate: true, handler(value) { if (value) this.load(); else this.reset(); } },
		sourceAcademicYear() { if (this.launchName) this.load(); },
	},
	methods: {
		reset() {
			this.loaded = false;
			this.error = "";
			this.data = { branches: [], target_offerings: [], progression: [], admission_branches: [], admission_cycles: [], applicants: [], enrollments: [], summary: {}, permissions: {} };
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
				this.error = error?.message || "Learner preparation could not be loaded.";
			} finally { this.loading = false; }
		},
		applyContext(payload) {
			this.data = { branches: [], target_offerings: [], progression: [], admission_branches: [], admission_cycles: [], applicants: [], enrollments: [], summary: {}, permissions: {}, ...payload };
			this.$emit("learners-updated", this.data.summary || {});
		},
		progressionLabel(row) {
			return { decision_required: "Decision required", draft_prepared: "Draft prepared", target_submitted: "Submitted · Finalize", finalized: row.current_status || "Finalised" }[row.launch_state] || row.launch_state;
		},
		progressionTone(row) {
			return row.launch_state === "finalized" ? "is-ready" : row.launch_state === "target_submitted" ? "is-warning" : row.launch_state === "draft_prepared" ? "is-neutral" : "is-warning";
		},
		recommendationTone(row) {
			const label = row.recommendation?.label || "";
			return label === "Promotion Review Ready" ? "is-ready" : label.includes("Review") || label.includes("Manual") ? "is-warning" : "is-neutral";
		},
		admissionBranchLabel(row) {
			return row.status === "ready" ? `${row.admission_count} cycle(s) ready` : row.status === "missing" ? "Admission cycle required" : "No admission-enabled Intakes";
		},
		async prepareProgression(row) {
			let destination = null;
			const branchOptions = ["", ...(this.data.branches || []).map((item) => item.name)];
			const dialog = new frappe.ui.Dialog({
				title: __("Prepare Progression Draft"),
				fields: [
					{ fieldname: "student", fieldtype: "Data", label: __("Student"), read_only: true, default: row.student_name || row.student },
					{ fieldname: "outcome", fieldtype: "Select", label: __("Outcome"), options: ["Promote", "Repeat", "Transfer"], reqd: 1, default: "Promote", onchange: () => refreshDestination() },
					{ fieldname: "target_branch", fieldtype: "Select", label: __("Target Branch / Campus (Transfer)"), options: branchOptions, default: row.branch, onchange: () => refreshDestination() },
					{ fieldname: "target_student_group", fieldtype: "Select", label: __("Destination Class Arm"), options: [""] },
					{ fieldname: "destination_note", fieldtype: "HTML", options: "<div class='session-learners-dialog-note'>Resolving destination...</div>" },
					{ fieldname: "reason", fieldtype: "Small Text", label: __("Decision Note / Reason"), reqd: 1 },
				],
				primary_action_label: __("Prepare Enrollment Draft"),
				primary_action: async (values) => {
					if ((destination?.student_groups || []).length && !values.target_student_group) {
						frappe.msgprint({ title: __("Choose a destination Class Arm"), message: __("A destination Class Arm is available. Select it so finalisation can place the Student correctly."), indicator: "orange" });
						return;
					}
					dialog.disable_primary_action();
					this.working = true;
					try {
						const response = await frappe.call({ method: PREPARE_METHOD, type: "POST", args: { launch: this.launchName, source_enrollment: row.name, outcome: values.outcome, reason: values.reason, target_branch: values.outcome === "Transfer" ? values.target_branch : undefined, target_student_group: values.target_student_group || undefined } });
						this.applyContext(response.message?.context || {});
						dialog.hide();
						frappe.show_alert({ message: __("Destination Enrollment draft prepared"), indicator: "green" });
					} catch (error) { this.error = error?.message || "Progression draft could not be prepared."; }
					finally { this.working = false; dialog.enable_primary_action(); }
				},
			});
			const refreshDestination = async () => {
				const outcome = dialog.get_value("outcome") || "Promote";
				const targetBranch = dialog.get_value("target_branch") || row.branch;
				try {
					const response = await frappe.call(OPTIONS_METHOD, { launch: this.launchName, source_enrollment: row.name, outcome, target_branch: outcome === "Transfer" ? targetBranch : undefined });
					destination = response.message || {};
					const groups = destination.student_groups || [];
					dialog.set_df_property("target_student_group", "options", ["", ...groups.map((item) => item.name)]);
					if (groups.length === 1) dialog.set_value("target_student_group", groups[0].name);
					const offering = destination.offering || {};
					const text = offering.name ? `Destination: ${offering.offering_title || offering.name} · ${groups.length} Class Arm option(s)` : "No destination Enrollment is required for this outcome.";
					dialog.fields_dict.destination_note.$wrapper.html(`<div class="session-learners-dialog-note">${frappe.utils.escape_html(text)}</div>`);
				} catch (error) {
					destination = null;
					dialog.set_df_property("target_student_group", "options", [""]);
					dialog.fields_dict.destination_note.$wrapper.html(`<div class="session-learners-dialog-note is-error">${frappe.utils.escape_html(error?.message || "Destination could not be resolved.")}</div>`);
				}
			};
			dialog.show();
			await refreshDestination();
		},
		finalizeProgression(row) {
			const outcome = row.planned_target?.eduedge_progression_outcome || row.planned_target?.progression_outcome || "Promote";
			const dialog = new frappe.ui.Dialog({
				title: __("Finalize Student Progression"),
				fields: [
					{ fieldname: "student", fieldtype: "Data", label: __("Student"), read_only: true, default: row.student_name || row.student },
					{ fieldname: "reason", fieldtype: "Small Text", label: __("Final Decision Note"), reqd: 1 },
					{ fieldname: "effective_date", fieldtype: "Date", label: __("Effective Date"), default: frappe.datetime.get_today() },
				],
				primary_action_label: __("Finalize Progression"),
				primary_action: async (values) => {
					dialog.disable_primary_action(); this.working = true;
					try {
						const response = await frappe.call({ method: FINALIZE_METHOD, type: "POST", args: { launch: this.launchName, source_enrollment: row.name, outcome, reason: values.reason, effective_date: values.effective_date } });
						this.applyContext(response.message?.context || {});
						dialog.hide();
						frappe.show_alert({ message: __("Student Progression finalised"), indicator: "green" });
					} catch (error) { this.error = error?.message || "Progression could not be finalised."; }
					finally { this.working = false; dialog.enable_primary_action(); }
				},
			});
			dialog.show();
		},
		createAdmission(row) {
			const programs = row.programs || [];
			const checks = programs.map((item) => `<label class="session-learners-program-check"><input type="checkbox" data-program="${frappe.utils.escape_html(item.program)}" checked /> <span>${frappe.utils.escape_html(item.program)}</span></label>`).join("");
			const dialog = new frappe.ui.Dialog({
				title: __("Create Admission Cycle"),
				fields: [
					{ fieldname: "title", fieldtype: "Data", label: __("Title"), reqd: 1, default: `${this.academicYear} Admissions - ${row.branch_name}` },
					{ fieldname: "branch", fieldtype: "Data", label: __("Branch / Campus"), read_only: true, default: row.branch_name },
					{ fieldname: "admission_start_date", fieldtype: "Date", label: __("Admission Start Date") },
					{ fieldname: "admission_end_date", fieldtype: "Date", label: __("Admission End Date") },
					{ fieldname: "enable_admission_application", fieldtype: "Check", label: __("Enable Admission Applications"), default: 0 },
					{ fieldname: "published", fieldtype: "Check", label: __("Publish on Website"), default: 0 },
					{ fieldname: "programs_html", fieldtype: "HTML", options: `<div class="session-learners-programs"><strong>${__("Classes Accepting Applications")}</strong>${checks}</div>` },
				],
				primary_action_label: __("Create Draft Admission Cycle"),
				primary_action: async (values) => {
					const selected = [];
					dialog.fields_dict.programs_html.$wrapper.find("input[data-program]:checked").each(function () { selected.push($(this).data("program")); });
					if (!selected.length) { frappe.msgprint({ title: __("Select at least one Class"), message: __("Choose the Classes that will accept applications in this admission cycle."), indicator: "orange" }); return; }
					dialog.disable_primary_action(); this.working = true;
					try {
						const response = await frappe.call({ method: ADMISSION_METHOD, type: "POST", args: { launch: this.launchName, branch: row.branch, title: values.title, programs: JSON.stringify(selected), admission_start_date: values.admission_start_date || undefined, admission_end_date: values.admission_end_date || undefined, enable_admission_application: values.enable_admission_application ? 1 : 0, published: values.published ? 1 : 0 } });
						this.applyContext(response.message?.context || {});
						dialog.hide();
						frappe.show_alert({ message: __("Admission cycle draft created"), indicator: "green" });
					} catch (error) { this.error = error?.message || "Admission cycle could not be created."; }
					finally { this.working = false; dialog.enable_primary_action(); }
				},
			});
			dialog.show();
		},
		createEnrollment() {
			const branchOptions = (this.data.branches || []).map((item) => item.name);
			const defaultBranch = this.branch && branchOptions.includes(this.branch) ? this.branch : branchOptions[0] || "";
			const dialog = new frappe.ui.Dialog({
				title: __("New Destination Enrollment Draft"),
				fields: [
					{ fieldname: "guidance", fieldtype: "HTML", options: `<div class="session-learners-dialog-note">${__("Use this for new/admitted Students. Returning Students with a submitted source-session Enrollment must use Student Progression.")}</div>` },
					{ fieldname: "branch", fieldtype: "Select", label: __("Branch / Campus"), options: branchOptions, reqd: 1, default: defaultBranch, onchange: () => refreshOfferings() },
					{ fieldname: "student", fieldtype: "Link", label: __("Student"), options: "Student", reqd: 1 },
					{ fieldname: "offering", fieldtype: "Select", label: __("Class Intake"), options: [{ value: "", label: __("Select Class Intake") }], reqd: 1 },
				],
				primary_action_label: __("Create Enrollment Draft"),
				primary_action: async (values) => {
					dialog.disable_primary_action(); this.working = true;
					try {
						const response = await frappe.call({ method: ENROLLMENT_METHOD, type: "POST", args: { launch: this.launchName, branch: values.branch, student: values.student, offering: values.offering } });
						this.applyContext(response.message?.context || {});
						dialog.hide();
						frappe.show_alert({ message: __("Enrollment draft created"), indicator: "green" });
					} catch (error) { this.error = error?.message || "Enrollment draft could not be created."; }
					finally { this.working = false; dialog.enable_primary_action(); }
				},
			});
			const refreshOfferings = () => {
				const branch = dialog.get_value("branch");
				const options = (this.data.target_offerings || [])
					.filter((item) => item.school_branch === branch && Number(item.enrollment_enabled) === 1)
					.map((item) => ({
						value: item.name,
						label: item.offering_title || item.program || item.name,
					}));
				dialog.set_df_property("offering", "options", [{ value: "", label: __("Select Class Intake") }, ...options]);
				if (options.length === 1) dialog.set_value("offering", options[0].value);
			};
			dialog.$wrapper?.addClass("session-learners-dialog");
			dialog.show();
			const studentField = dialog.fields_dict.student;
			const getQuery = () => ({ query: STUDENT_QUERY, filters: { launch: this.launchName, branch: dialog.get_value("branch") || "" } });
			studentField.get_query = getQuery;
			studentField.df.get_query = getQuery;
			refreshOfferings();
		},
		openReview(route, extra = {}) {
			const params = new URLSearchParams();
			if (this.academicYear) { params.set("academic_year", this.academicYear); params.set("destination_academic_year", this.academicYear); }
			if (this.sourceAcademicYear) params.set("source_academic_year", this.sourceAcademicYear);
			if (this.institution) params.set("institution", this.institution);
			if (this.branch) params.set("branch", this.branch);
			for (const [key, value] of Object.entries(extra || {})) if (value) params.set(key, value);
			window.open(`${route}${params.toString() ? `?${params}` : ""}`, "_blank", "noopener,noreferrer");
		},
		openNative(doctypeRoute, name) { if (name) window.open(`/app/${doctypeRoute}/${encodeURIComponent(name)}`, "_blank", "noopener,noreferrer"); },
	},
};
</script>

<style scoped>
.session-learners-shell{display:grid;gap:1rem;margin-top:1rem;color:var(--text-color)}
.session-learners-shell h2,.session-learners-shell h3,.session-learners-shell h4,.session-learners-shell strong{color:var(--text-color)}
.session-learners-header{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem}.session-learners-header h2{margin:.1rem 0 .3rem}.session-learners-header p{margin:0;color:var(--text-muted)}
.session-learners-card{display:grid;gap:.9rem;padding:1rem;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}.session-learners-card-header{display:flex;justify-content:space-between;align-items:center;gap:1rem}.session-learners-card-header>div:first-child{display:flex;align-items:center;gap:.7rem}.session-learners-card-header h3,.session-learners-subheading h4{margin:0}.session-learners-card-header small,.session-learners-subheading small,.session-learners-row small,.session-learners-table small{display:block;color:var(--text-muted)}.session-learners-step{display:grid;place-items:center;width:2rem;height:2rem;border:1px solid var(--border-color);border-radius:999px;font-weight:700}.session-learners-summary{display:grid;text-align:right}.session-learners-summary strong{font-size:1.2rem}.session-learners-summary span{font-size:.78rem;color:var(--text-muted)}
.session-learners-toolbar,.session-learners-subheading{display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:.7rem;border:1px dashed var(--border-color);border-radius:8px}.session-learners-actions{display:flex;gap:.5rem;flex-wrap:wrap}.session-learners-subsection{display:grid;gap:.7rem;padding-top:.2rem}.session-learners-list{display:grid;gap:.45rem}.session-learners-row{display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:.65rem .75rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.session-learners-row-side{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap}
.session-learners-table-wrap{overflow:auto;border:1px solid var(--border-color);border-radius:8px}.session-learners-table{width:100%;border-collapse:collapse;min-width:900px;color:var(--text-color)}.session-learners-table th,.session-learners-table td{padding:.6rem .7rem;border-bottom:1px solid var(--border-color);text-align:left;vertical-align:top}.session-learners-table th{font-size:.78rem;color:var(--text-muted);background:var(--control-bg)}.session-learners-table tr:last-child td{border-bottom:0}.session-learners-badge{display:inline-flex;padding:.2rem .45rem;border:1px solid currentColor;border-radius:999px;font-size:.75rem}.is-ready{color:var(--green-600,#16803c)}.is-warning{color:var(--orange-600,#b54708)}.is-error{color:var(--red-600,#b42318)}.is-neutral{color:var(--text-muted)}
.session-learners-metrics{display:flex;flex-wrap:wrap;gap:.5rem}.session-learners-metrics>span{display:grid;gap:.1rem;min-width:8rem;padding:.45rem .55rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.session-learners-metrics small{color:var(--text-muted)}.session-learners-rule{margin:0;color:var(--text-muted);font-size:.82rem}.session-learners-empty,.session-learners-message{padding:.75rem;border-radius:8px;background:var(--control-bg);color:var(--text-muted)}.session-learners-message--error{color:var(--red-600,#b42318)}
:global(.session-learners-dialog-note){padding:.65rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg);color:var(--text-muted)}:global(.session-learners-dialog-note.is-error){color:var(--red-600,#b42318)}:global(.session-learners-programs){display:grid;gap:.45rem;padding:.65rem;border:1px solid var(--border-color);border-radius:8px}:global(.session-learners-program-check){display:flex;align-items:center;gap:.45rem;margin:0}
:global(.session-learners-dialog .modal-content){background:var(--card-bg);color:var(--text-color)}
:global(.session-learners-dialog .modal-header),:global(.session-learners-dialog .modal-body),:global(.session-learners-dialog .modal-footer){background:var(--card-bg);color:var(--text-color)}
:global(.session-learners-dialog .btn-modal-close){display:inline-flex;align-items:center;justify-content:center;min-width:2rem;min-height:2rem;opacity:1!important;color:var(--text-color)!important;--icon-stroke:var(--text-color);--icon-fill:var(--text-color)}
:global(.session-learners-dialog .btn-modal-close .icon){opacity:1!important;stroke:var(--text-color)!important;fill:var(--text-color)!important}
:global(.session-learners-dialog .awesomplete>ul),:global(.session-learners-dialog .awesomplete>[role="listbox"]){background:var(--card-bg)!important;border-color:var(--border-color)!important;color:var(--text-color)!important}
:global(.session-learners-dialog .awesomplete>ul>li),:global(.session-learners-dialog .awesomplete>[role="listbox"]>li){background:var(--card-bg)!important;color:var(--text-color)!important}
:global(.session-learners-dialog .awesomplete>ul>li *),:global(.session-learners-dialog .awesomplete>[role="listbox"]>li *){color:inherit!important}
:global(.session-learners-dialog .awesomplete>ul>li:hover),:global(.session-learners-dialog .awesomplete>ul>li[aria-selected="true"]),:global(.session-learners-dialog .awesomplete>[role="listbox"]>li:hover),:global(.session-learners-dialog .awesomplete>[role="listbox"]>li[aria-selected="true"]){background:var(--control-bg)!important;color:var(--text-color)!important}
@media(max-width:800px){.session-learners-header,.session-learners-card-header,.session-learners-toolbar,.session-learners-subheading,.session-learners-row{align-items:stretch;flex-direction:column}.session-learners-summary{text-align:left}}
</style>