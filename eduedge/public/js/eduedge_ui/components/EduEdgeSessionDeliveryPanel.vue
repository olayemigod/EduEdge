<template>
	<section v-if="launchName" class="session-delivery-shell">
		<div class="session-delivery-header">
			<div>
				<p class="edge-eyebrow">Guided Academic Delivery</p>
				<h2><span class="session-delivery-step">7</span> Academic Delivery</h2>
				<p>Validate Class Subjects, assign teaching responsibility, confirm Class Teachers where required, and see exactly which Class Arm × Subject contexts still need timetable or Scheme preparation.</p>
			</div>
			<button type="button" class="edge-button" :disabled="loading || working" @click="load">{{ loading ? "Refreshing..." : "Refresh" }}</button>
		</div>

		<div v-if="error" class="session-delivery-message session-delivery-message--error">{{ error }}</div>
		<div v-if="loading && !loaded" class="session-delivery-message">Loading Academic Delivery readiness...</div>
		<template v-else-if="loaded">
			<div class="session-delivery-metrics">
				<span><small>Class Intakes</small><strong>{{ summary.class_intakes || 0 }}</strong></span>
				<span><small>Teaching contexts</small><strong>{{ summary.expected_teaching_contexts || 0 }}</strong></span>
				<span><small>Instructor assigned</small><strong>{{ summary.assigned_teaching_contexts || 0 }}/{{ summary.expected_teaching_contexts || 0 }}</strong></span>
				<span><small>Scheduled</small><strong>{{ summary.scheduled_teaching_contexts || 0 }}/{{ summary.expected_teaching_contexts || 0 }}</strong></span>
				<span><small>Approved Schemes</small><strong>{{ summary.approved_scheme_contexts || 0 }}/{{ summary.expected_teaching_contexts || 0 }}</strong></span>
			</div>

			<div class="session-delivery-readiness">
				<span :class="statusClass(summary.subjects_ready)">Subjects {{ summary.subjects_ready ? "Ready" : "Need attention" }}</span>
				<span :class="statusClass(summary.assignments_ready)">Teaching Assignments {{ summary.assignments_ready ? "Ready" : "Need attention" }}</span>
				<span v-if="summary.class_responsibility_required" :class="statusClass(summary.class_responsibility_ready)">Class Teachers {{ summary.class_responsibility_ready ? "Ready" : "Need attention" }}</span>
				<span :class="statusClass(summary.schedule_ready)">Teaching Schedule {{ summary.schedule_ready ? "Ready" : "Need attention" }}</span>
				<span :class="statusClass(summary.scheme_ready)">Scheme of Work {{ summary.scheme_ready ? "Ready" : "Need attention" }}</span>
			</div>

			<article class="session-delivery-card">
				<div class="session-delivery-card-heading">
					<div><h3>Subjects & Class Curriculum</h3><small>Classes are persistent masters. Session Launch verifies the Subjects attached to each destination Class Intake and lets you add an existing Institution Subject without leaving the flow.</small></div>
					<div class="session-delivery-actions"><button type="button" class="edge-button" @click="openReview('/app/eduedge-programs')">Review Classes in new tab</button></div>
				</div>
				<div v-if="!curriculumRows.length" class="session-delivery-empty">No active destination Class Intakes are available yet.</div>
				<div v-else class="session-delivery-table-wrap">
					<table class="session-delivery-table">
						<thead><tr><th>Branch</th><th>Class Intake</th><th>Class</th><th>Subjects</th><th>Status</th><th></th></tr></thead>
						<tbody>
							<tr v-for="row in curriculumRows" :key="row.program_offering">
								<td>{{ row.branch_name }}</td>
								<td><strong>{{ row.offering_label }}</strong><small>{{ academicYear }}</small></td>
								<td>{{ row.program }}</td>
								<td><div class="session-delivery-subjects"><span v-for="course in row.courses" :key="course.name">{{ course.label }}</span><em v-if="!row.courses.length">No Subjects configured</em></div></td>
								<td><span :class="statusClass(row.ready)">{{ row.ready ? `${row.course_count} configured` : "Needs Subjects" }}</span></td>
								<td><button type="button" class="edge-button" :disabled="working || !permissions.can_edit_curriculum" @click="addSubject(row)">Add Subject</button></td>
							</tr>
						</tbody>
					</table>
				</div>
			</article>

			<article class="session-delivery-card">
				<div class="session-delivery-card-heading">
					<div><h3>Subject Teaching Assignments</h3><small>One row represents one exact destination Class / Class Arm / Subject responsibility. Existing valid assignments are recognised; missing rows can be assigned in a governed batch.</small></div>
					<div class="session-delivery-actions">
						<button type="button" class="edge-button edge-button--primary" :disabled="working || !selectedTeaching.length || !permissions.can_manage_assignments" @click="assignTeaching">Assign Selected ({{ selectedTeaching.length }})</button>
						<button type="button" class="edge-button" @click="openReview('/app/eduedge-instructor-assignments')">Review Assignments in new tab</button>
					</div>
				</div>
				<div v-if="!teachingRows.length" class="session-delivery-empty">No Subject teaching contexts can be derived until destination Class Intakes and Class curriculum are ready.</div>
				<div v-else class="session-delivery-table-wrap">
					<table class="session-delivery-table session-delivery-table--teaching">
						<thead><tr><th></th><th>Branch</th><th>Class Intake</th><th>Class Arm</th><th>Subject</th><th>Instructor</th><th>Status</th></tr></thead>
						<tbody>
							<tr v-for="row in teachingRows" :key="row.context_key">
								<td><input v-if="!row.assigned" v-model="selectedTeaching" type="checkbox" :value="row.context_key" aria-label="Select missing teaching assignment" /></td>
								<td>{{ row.branch_name }}</td>
								<td>{{ row.offering_label }}</td>
								<td>{{ row.student_group_label }}</td>
								<td><strong>{{ row.course_label }}</strong></td>
								<td><span v-if="row.assignments.length">{{ row.assignments.map((item) => item.instructor_name).join(', ') }}</span><span v-else class="session-delivery-muted">Unassigned</span></td>
								<td><span :class="statusClass(row.assigned)">{{ row.assigned ? "Assigned" : "Needs Teacher" }}</span></td>
							</tr>
						</tbody>
					</table>
				</div>
			</article>

			<article v-if="summary.class_responsibility_required || responsibilityRows.length" class="session-delivery-card">
				<div class="session-delivery-card-heading">
					<div><h3>Class Teacher Responsibility</h3><small v-if="summary.class_responsibility_required">Primary/Secondary Session readiness expects every active destination Class Arm to have a Class Teacher or Form Teacher.</small><small v-else>Class responsibility is optional for this Institution type.</small></div>
					<div class="session-delivery-actions"><button type="button" class="edge-button edge-button--primary" :disabled="working || !selectedResponsibilities.length || !permissions.can_manage_assignments" @click="assignClassTeacher">Assign Selected ({{ selectedResponsibilities.length }})</button></div>
				</div>
				<div class="session-delivery-table-wrap">
					<table class="session-delivery-table">
						<thead><tr><th></th><th>Branch</th><th>Class Intake</th><th>Class Arm</th><th>Responsible Teacher</th><th>Status</th></tr></thead>
						<tbody>
							<tr v-for="row in responsibilityRows" :key="row.student_group">
								<td><input v-if="!row.assigned" v-model="selectedResponsibilities" type="checkbox" :value="row.student_group" aria-label="Select Class Arm responsibility" /></td>
								<td>{{ row.branch_name }}</td><td>{{ row.offering_label }}</td><td><strong>{{ row.student_group_label }}</strong></td>
								<td>{{ row.assignments.length ? row.assignments.map((item) => `${item.instructor_name} (${item.assignment_type})`).join(', ') : "Unassigned" }}</td>
								<td><span :class="statusClass(row.assigned)">{{ row.assigned ? "Assigned" : "Needs Class Teacher" }}</span></td>
							</tr>
						</tbody>
					</table>
				</div>
			</article>

			<article class="session-delivery-card">
				<div class="session-delivery-card-heading">
					<div><h3>Teaching Schedule & Scheme Readiness</h3><small>Session Launch audits real Course Schedule and Scheme of Work records. Historical schedules, lesson delivery and results are never copied forward.</small></div>
					<div class="session-delivery-actions">
						<button type="button" class="edge-button" @click="openReview('/app/eduedge-academic-operations')">Review Teaching Schedule in new tab</button>
						<button type="button" class="edge-button" @click="openReview('/app/eduedge-schemes-of-work')">Review Schemes in new tab</button>
					</div>
				</div>
				<div v-if="!teachingRows.length" class="session-delivery-empty">No teaching contexts are available for schedule/Scheme validation yet.</div>
				<div v-else class="session-delivery-table-wrap">
					<table class="session-delivery-table">
						<thead><tr><th>Branch</th><th>Class Intake</th><th>Class Arm</th><th>Subject</th><th>Teaching Schedule</th><th>Scheme of Work</th></tr></thead>
						<tbody>
							<tr v-for="row in teachingRows" :key="`delivery-${row.context_key}`">
								<td>{{ row.branch_name }}</td><td>{{ row.offering_label }}</td><td>{{ row.student_group_label }}</td><td><strong>{{ row.course_label }}</strong></td>
								<td><span :class="statusClass(row.schedule_ready)">{{ row.schedule_ready ? `${row.schedule_count} scheduled` : row.student_group ? "Not scheduled" : "Class-wide context" }}</span></td>
								<td><span :class="statusClass(row.scheme_status === 'Approved')">{{ row.scheme_status }}</span></td>
							</tr>
						</tbody>
					</table>
				</div>
				<p class="session-delivery-rule"><strong>Timetable safety:</strong> this slice audits scheduling readiness but does not generate Course Schedule records. Timetable creation stays in Academic Operations until a shared governed bulk scheduler can validate time, room and Instructor conflicts before writing.</p>
			</article>

			<div class="session-delivery-footer">
				<button type="button" class="edge-button" @click="$emit('save-step', 'academic_delivery')">Save here</button>
				<strong v-if="summary.academic_delivery_ready" class="session-delivery-ready-text">Academic Delivery is ready for {{ academicYear }}.</strong>
				<span v-else class="session-delivery-muted">Resolve the highlighted delivery gaps, then Refresh. Readiness is always recalculated from the underlying academic records.</span>
			</div>
		</template>
	</section>
</template>

<script>
const GET_METHOD = "eduedge.api.session_launch_delivery.get_session_delivery_context";
const ADD_SUBJECT_METHOD = "eduedge.api.session_launch_delivery.add_guided_class_subject";
const ASSIGN_SUBJECT_METHOD = "eduedge.api.session_launch_delivery.assign_guided_subject_instructor";
const ASSIGN_CLASS_METHOD = "eduedge.api.session_launch_delivery.assign_guided_class_teacher";
const INSTRUCTOR_QUERY = "eduedge.api.session_launch_delivery.guided_instructor_query";
const COURSE_QUERY = "eduedge.api.session_launch_delivery.guided_course_query";

export default {
	name: "EduEdgeSessionDeliveryPanel",
	props: {
		launchName: { type: String, default: "" },
		academicYear: { type: String, default: "" },
		institution: { type: String, default: "" },
		branch: { type: String, default: "" },
	},
	emits: ["save-step", "delivery-updated"],
	data() {
		return {
			loading: false,
			loaded: false,
			working: false,
			error: "",
			payload: { branches: [], summary: {}, permissions: {}, defaults: {} },
			selectedTeaching: [],
			selectedResponsibilities: [],
		};
	},
	computed: {
		summary() { return this.payload.summary || {}; },
		permissions() { return this.payload.permissions || {}; },
		curriculumRows() {
			return (this.payload.branches || []).flatMap((branch) => (branch.curriculum || []).map((row) => ({ ...row, branch_name: branch.branch_name })));
		},
		teachingRows() {
			return (this.payload.branches || []).flatMap((branch) => (branch.teaching_contexts || []).map((row) => ({ ...row, branch_name: branch.branch_name })));
		},
		responsibilityRows() {
			return (this.payload.branches || []).flatMap((branch) => (branch.class_responsibilities || []).map((row) => ({ ...row, branch_name: branch.branch_name })));
		},
	},
	watch: {
		launchName: { immediate: true, handler(value) { if (value) this.load(); else this.reset(); } },
	},
	methods: {
		reset() {
			this.loaded = false; this.error = ""; this.selectedTeaching = []; this.selectedResponsibilities = [];
			this.payload = { branches: [], summary: {}, permissions: {}, defaults: {} };
		},
		applyPayload(payload) {
			this.payload = { branches: [], summary: {}, permissions: {}, defaults: {}, ...(payload || {}) };
			const missingTeaching = new Set(this.teachingRows.filter((row) => !row.assigned).map((row) => row.context_key));
			this.selectedTeaching = this.selectedTeaching.filter((key) => missingTeaching.has(key));
			const missingResponsibilities = new Set(this.responsibilityRows.filter((row) => !row.assigned).map((row) => row.student_group));
			this.selectedResponsibilities = this.selectedResponsibilities.filter((name) => missingResponsibilities.has(name));
			this.$emit("delivery-updated", this.summary);
		},
		async load() {
			if (!this.launchName) return;
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call(GET_METHOD, { launch: this.launchName });
				this.applyPayload(response.message || {}); this.loaded = true;
			} catch (error) { this.error = error?.message || "Academic Delivery readiness could not be loaded."; }
			finally { this.loading = false; }
		},
		statusClass(ready) { return ["session-delivery-status", ready ? "is-ready" : "is-warning"]; },
		addSubject(row) {
			const dialog = new frappe.ui.Dialog({
				title: __("Add Subject to Class Curriculum"),
				fields: [
					{ fieldname: "class", fieldtype: "Data", label: __("Class"), read_only: true, default: row.program },
					{ fieldname: "subject", fieldtype: "Link", label: __("Institution Subject"), options: "Course", reqd: 1 },
				],
				primary_action_label: __("Add Subject"),
				primary_action: async (values) => {
					dialog.disable_primary_action(); this.working = true;
					try {
						const response = await frappe.call({ method: ADD_SUBJECT_METHOD, type: "POST", args: { launch: this.launchName, program_offering: row.program_offering, course: values.subject } });
						this.applyPayload(response.message?.context || {}); dialog.hide();
						frappe.show_alert({ message: __("Subject added to Class curriculum"), indicator: "green" });
					} catch (error) { this.error = error?.message || "Subject could not be added."; }
					finally { this.working = false; dialog.enable_primary_action(); }
				},
			});
			const field = dialog.fields_dict.subject;
			const getQuery = () => ({ query: COURSE_QUERY, filters: { launch: this.launchName, program_offering: row.program_offering } });
			field.get_query = getQuery; field.df.get_query = getQuery;
			dialog.show();
		},
		assignTeaching() {
			if (!this.selectedTeaching.length) return;
			const defaultType = this.payload.defaults?.subject_assignment_type || "Subject Instructor";
			const types = Array.from(new Set([defaultType, "Subject Instructor", "Lecturer", "Tutor", "Practical Instructor", "Assistant Instructor"]));
			this.assignmentDialog({
				title: __("Assign Subject Teaching Responsibility"),
				assignmentTypes: types,
				defaultType,
				primaryLabel: __("Assign Selected"),
				onSubmit: async (values, dialog) => {
					const response = await frappe.call({ method: ASSIGN_SUBJECT_METHOD, type: "POST", args: { launch: this.launchName, instructor: values.instructor, contexts: JSON.stringify(this.selectedTeaching.map((context_key) => ({ context_key }))), assignment_type: values.assignment_type } });
					this.applyPayload(response.message?.context || {}); dialog.hide();
					frappe.show_alert({ message: __("Teaching assignments prepared"), indicator: "green" });
				},
			});
		},
		assignClassTeacher() {
			if (!this.selectedResponsibilities.length) return;
			this.assignmentDialog({
				title: __("Assign Class Responsibility"),
				assignmentTypes: ["Class Teacher", "Form Teacher"],
				defaultType: this.payload.defaults?.class_responsibility_type || "Class Teacher",
				primaryLabel: __("Assign Selected Class Arms"),
				onSubmit: async (values, dialog) => {
					const response = await frappe.call({ method: ASSIGN_CLASS_METHOD, type: "POST", args: { launch: this.launchName, instructor: values.instructor, student_groups: JSON.stringify(this.selectedResponsibilities), assignment_type: values.assignment_type } });
					this.applyPayload(response.message?.context || {}); dialog.hide();
					frappe.show_alert({ message: __("Class responsibility assigned"), indicator: "green" });
				},
			});
		},
		assignmentDialog({ title, assignmentTypes, defaultType, primaryLabel, onSubmit }) {
			const dialog = new frappe.ui.Dialog({
				title,
				fields: [
					{ fieldname: "instructor", fieldtype: "Link", label: __("Teacher / Instructor"), options: "Instructor", reqd: 1 },
					{ fieldname: "assignment_type", fieldtype: "Select", label: __("Responsibility Type"), options: assignmentTypes, default: defaultType, reqd: 1 },
				],
				primary_action_label: primaryLabel,
				primary_action: async (values) => {
					dialog.disable_primary_action(); this.working = true; this.error = "";
					try { await onSubmit(values, dialog); }
					catch (error) { this.error = error?.message || "Academic responsibility could not be assigned."; }
					finally { this.working = false; dialog.enable_primary_action(); }
				},
			});
			const field = dialog.fields_dict.instructor;
			const getQuery = () => ({ query: INSTRUCTOR_QUERY, filters: { launch: this.launchName } });
			field.get_query = getQuery; field.df.get_query = getQuery;
			dialog.show();
		},
		openReview(route) {
			const params = new URLSearchParams();
			if (this.academicYear) params.set("academic_year", this.academicYear);
			if (this.institution) params.set("institution", this.institution);
			if (this.branch) params.set("branch", this.branch);
			window.open(`${route}${params.toString() ? `?${params}` : ""}`, "_blank", "noopener,noreferrer");
		},
	},
};
</script>

<style scoped>
.session-delivery-shell{display:grid;gap:1rem;margin-top:1rem;color:var(--text-color)}
.session-delivery-shell h2,.session-delivery-shell h3,.session-delivery-shell strong{color:var(--text-color)}
.session-delivery-header{display:flex;justify-content:space-between;align-items:flex-start;gap:1rem}.session-delivery-header h2{display:flex;align-items:center;gap:.6rem;margin:.1rem 0 .3rem}.session-delivery-header p{max-width:70rem;margin:0;color:var(--text-muted)}
.session-delivery-step{display:grid;place-items:center;width:2rem;height:2rem;border:1px solid var(--border-color);border-radius:999px;font-size:.9rem}.session-delivery-metrics{display:flex;flex-wrap:wrap;gap:.5rem}.session-delivery-metrics>span{display:grid;gap:.1rem;min-width:10rem;padding:.55rem .65rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.session-delivery-metrics small{color:var(--text-muted)}.session-delivery-metrics strong{font-size:1.05rem}
.session-delivery-readiness{display:flex;flex-wrap:wrap;gap:.45rem}.session-delivery-status{display:inline-flex;padding:.22rem .48rem;border:1px solid currentColor;border-radius:999px;font-size:.76rem}.session-delivery-status.is-ready{color:var(--green-600,#16803c)}.session-delivery-status.is-warning{color:var(--orange-600,#b54708)}
.session-delivery-card{display:grid;gap:.8rem;padding:1rem;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}.session-delivery-card-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:1rem}.session-delivery-card-heading h3{margin:0}.session-delivery-card-heading small{display:block;max-width:65rem;color:var(--text-muted)}.session-delivery-actions{display:flex;gap:.5rem;flex-wrap:wrap}
.session-delivery-table-wrap{overflow:auto;border:1px solid var(--border-color);border-radius:8px}.session-delivery-table{width:100%;min-width:900px;border-collapse:collapse;color:var(--text-color)}.session-delivery-table--teaching{min-width:1050px}.session-delivery-table th,.session-delivery-table td{padding:.6rem .7rem;border-bottom:1px solid var(--border-color);text-align:left;vertical-align:top}.session-delivery-table th{font-size:.78rem;color:var(--text-muted);background:var(--control-bg)}.session-delivery-table tr:last-child td{border-bottom:0}.session-delivery-table small{display:block;color:var(--text-muted)}
.session-delivery-subjects{display:flex;flex-wrap:wrap;gap:.3rem}.session-delivery-subjects span{padding:.15rem .35rem;border:1px solid var(--border-color);border-radius:999px;font-size:.75rem}.session-delivery-subjects em,.session-delivery-muted{color:var(--text-muted);font-style:normal}.session-delivery-empty,.session-delivery-message{padding:.75rem;border-radius:8px;background:var(--control-bg);color:var(--text-muted)}.session-delivery-message--error{color:var(--red-600,#b42318)}.session-delivery-rule{margin:0;color:var(--text-muted);font-size:.82rem}.session-delivery-footer{display:flex;align-items:center;gap:.65rem;flex-wrap:wrap}.session-delivery-ready-text{color:var(--green-600,#16803c)!important}
@media(max-width:800px){.session-delivery-header,.session-delivery-card-heading{align-items:stretch;flex-direction:column}}
</style>
