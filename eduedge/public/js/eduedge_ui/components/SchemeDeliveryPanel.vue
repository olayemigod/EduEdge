<template>
	<section class="delivery-panel">
		<div class="delivery-heading">
			<div><p class="edge-eyebrow">Curriculum delivery</p><h3>Teaching Progress</h3></div>
			<button type="button" class="edge-button" :disabled="loading" @click="load">Refresh Progress</button>
		</div>
		<EdgeLoadingState v-if="loading && !loaded" message="Loading teaching progress..." />
		<EdgeErrorState v-else-if="error && !loaded" title="Teaching progress could not load" :message="error" action-label="Try again" @retry="load" />
		<template v-else>
			<div class="delivery-summary">
				<div><span>Coverage</span><strong>{{ state.summary.coverage_percent }}%</strong></div>
				<div><span>Completed Topics</span><strong>{{ state.summary.completed_items }} / {{ state.summary.item_count }}</strong></div>
				<div><span>Periods Delivered</span><strong>{{ formatNumber(state.summary.periods_delivered) }} / {{ state.summary.estimated_periods }}</strong></div>
				<div><span>Pending Topics</span><strong>{{ state.summary.pending_items }}</strong></div>
			</div>
			<div class="coverage-track"><span :style="{ width: `${Math.min(Math.max(state.summary.coverage_percent || 0, 0), 100)}%` }"></span></div>
			<EdgeActionBar
				v-if="scheme.status === 'Approved'"
				label="Delivery updates are append-only. Each update records the exact Instructor Assignment active on the delivery date. An Approved Lesson Plan and classroom evidence can be linked without changing the approved Scheme."
			/>
			<EdgeActionBar
				v-else
				label="This Scheme is historical. Delivery history remains visible, but new delivery updates can be recorded only against an Approved Scheme."
			/>

			<div class="delivery-items">
				<article v-for="row in state.items" :key="row.scheme_item_reference" class="delivery-item">
					<div class="delivery-item-main">
						<span class="sequence">{{ row.sequence }}</span>
						<div><strong>{{ row.topic_name }}</strong><small>Week {{ row.week_no }} · {{ formatNumber(row.periods_delivered) }} / {{ row.estimated_periods }} periods · {{ row.progress_percent }}%</small><small v-if="row.learning_objective">{{ row.learning_objective }}</small></div>
						<EdgeStatusBadge :label="row.latest_status" :status="row.latest_status" :tone="deliveryTone(row.latest_status)" />
					</div>
					<div class="item-progress"><span :style="{ width: `${Math.min(Math.max(row.progress_percent || 0, 0), 100)}%` }"></span></div>
					<div class="delivery-item-actions">
						<small>{{ row.latest_delivery_date ? `Last update ${row.latest_delivery_date}` : 'No delivery update yet' }} · {{ row.log_count }} log{{ row.log_count === 1 ? '' : 's' }}</small>
						<button v-if="scheme.status === 'Approved' && row.available_updates?.length" type="button" class="edge-button" @click="openUpdate(row)">Record Update</button>
					</div>
				</article>
			</div>

			<div v-if="form.item_reference" class="delivery-form">
				<div class="delivery-heading"><div><p class="edge-eyebrow">Append delivery event</p><h4>{{ form.topic_name }}</h4></div><button type="button" class="edge-button" @click="closeUpdate">Cancel</button></div>
				<div class="delivery-form-grid">
					<label><span>Delivery Update</span><select v-model="form.delivery_status" class="form-control" @change="statusChanged"><option v-for="status in form.available_updates" :key="status" :value="status">{{ status }}</option></select></label>
					<label><span>Delivery Date</span><input v-model="form.delivered_on" type="date" class="form-control" :min="scheme.period_start_date || undefined" :max="scheme.period_end_date || undefined" @change="deliveryDateChanged" /></label>
					<label><span>Periods Delivered</span><input v-model.number="form.periods_delivered" type="number" min="0" step="0.5" class="form-control" /></label>
					<label v-if="isManager"><span>Instructor</span><select v-model="form.instructor" class="form-control" :disabled="instructorsLoading" @change="instructorChanged"><option value="">Select Instructor</option><option v-for="row in instructorOptions" :key="row.value" :value="row.value">{{ row.label }}</option></select><small>Only Instructors with an effective exact Subject assignment on this date are shown.</small></label>
					<label class="wide"><span>Approved Lesson Plan</span><select v-model="form.lesson_plan" class="form-control" :disabled="lessonPlansLoading || !form.instructor"><option value="">No linked Lesson Plan</option><option v-for="row in lessonPlanOptions" :key="row.value" :value="row.value">{{ row.label }}</option></select><small>Optional. Only Approved Lesson Plans for this exact Scheme item, Instructor and Delivery Date are shown.</small></label>
					<label class="wide"><span>Delivery Notes</span><textarea v-model.trim="form.notes" class="form-control" rows="2" placeholder="Optional teaching progress, challenges, follow-up or deferment note"></textarea></label>
					<div class="evidence-field wide"><span>Teaching Evidence</span><div class="evidence-actions"><button type="button" class="edge-button" @click="attachEvidence">{{ form.evidence ? 'Replace Evidence' : 'Attach Evidence' }}</button><button v-if="form.evidence" type="button" class="edge-button" @click="form.evidence = ''">Remove</button><a v-if="form.evidence" :href="form.evidence" target="_blank" rel="noopener noreferrer">Open attached evidence</a></div><small>Optional classroom evidence such as a worksheet, teaching material, activity output or appropriate classroom photo. Avoid unnecessary sensitive Student data.</small></div>
				</div>
				<div class="form-actions"><button type="button" class="edge-button edge-button--primary" :disabled="saving || !canSubmit" @click="submitUpdate">{{ saving ? 'Recording...' : 'Record Delivery Update' }}</button></div>
				<p v-if="formError" class="delivery-error">{{ formError }}</p>
			</div>

			<div class="delivery-history">
				<div class="delivery-heading"><div><p class="edge-eyebrow">Audit history</p><h4>Recent Delivery Updates</h4></div></div>
				<EdgeEmptyState v-if="!state.logs.length" title="No delivery history" description="Delivery updates will appear here after teaching progress is recorded." />
				<div v-else class="history-list">
					<article v-for="row in state.logs.slice(0, 20)" :key="row.name">
						<div><strong>{{ row.topic_name_snapshot }} · {{ row.delivery_status }}</strong><small>{{ row.delivered_on }} · {{ formatNumber(row.periods_delivered) }} periods · {{ row.instructor }}</small><small v-if="row.lesson_plan || row.evidence">{{ row.lesson_plan ? 'Approved Lesson Plan linked' : '' }}{{ row.lesson_plan && row.evidence ? ' · ' : '' }}{{ row.evidence ? 'Teaching evidence attached' : '' }}</small></div>
						<div class="history-meta"><small>{{ row.notes || `Logged by ${row.logged_by}` }}</small><span><button v-if="row.lesson_plan" type="button" class="link-button" @click="openLessonPlan(row.lesson_plan)">Open Lesson Plan</button><a v-if="row.evidence" :href="row.evidence" target="_blank" rel="noopener noreferrer">Open Evidence</a></span></div>
					</article>
				</div>
			</div>
		</template>
	</section>
</template>

<script>
const blankState = () => ({
	scheme: "", status: "", items: [], logs: [],
	summary: { item_count: 0, completed_items: 0, pending_items: 0, estimated_periods: 0, periods_delivered: 0, coverage_percent: 0 },
});
const today = () => {
	const value = frappe.datetime?.get_today?.();
	if (value) return value;
	return new Date().toISOString().slice(0, 10);
};

export default {
	name: "SchemeDeliveryPanel",
	props: {
		scheme: { type: Object, required: true },
		isManager: { type: Boolean, default: false },
	},
	emits: ["updated"],
	data() {
		return {
			state: blankState(), loading: false, loaded: false, error: "", saving: false, formError: "",
			instructorOptions: [], instructorsLoading: false, lessonPlanOptions: [], lessonPlansLoading: false,
			form: { item_reference: "", topic_name: "", available_updates: [], delivery_status: "", delivered_on: today(), periods_delivered: 1, instructor: "", lesson_plan: "", notes: "", evidence: "" },
		};
	},
	computed: {
		canSubmit() {
			if (!this.form.item_reference || !this.form.delivery_status || !this.form.delivered_on) return false;
			if (this.form.delivery_status !== "Deferred" && Number(this.form.periods_delivered || 0) <= 0) return false;
			if (this.isManager && !this.form.instructor) return false;
			return true;
		},
	},
	watch: {
		"scheme.name": {
			immediate: true,
			handler(value) { if (value) this.load(); },
		},
	},
	methods: {
		formatNumber(value) { const number = Number(value || 0); return Number.isInteger(number) ? String(number) : number.toFixed(1); },
		deliveryTone(status) { return status === "Completed" ? "success" : status === "Deferred" ? "danger" : status === "Not Started" ? "neutral" : "warning"; },
		async load() {
			if (!this.scheme?.name) return;
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.scheme_delivery.get_scheme_delivery_state", { name: this.scheme.name });
				this.state = response.message || blankState();
				this.loaded = true;
			} catch (error) { this.error = error?.message || "Teaching progress could not be loaded."; }
			finally { this.loading = false; }
		},
		async openUpdate(row) {
			this.formError = "";
			this.form = {
				item_reference: row.scheme_item_reference,
				topic_name: row.topic_name,
				available_updates: [...(row.available_updates || [])],
				delivery_status: row.available_updates?.[0] || "",
				delivered_on: today(),
				periods_delivered: row.available_updates?.[0] === "Deferred" ? 0 : 1,
				instructor: "",
				lesson_plan: "",
				notes: "",
				evidence: "",
			};
			await this.loadInstructorOptions();
		},
		closeUpdate() { this.form.item_reference = ""; this.formError = ""; this.instructorOptions = []; this.lessonPlanOptions = []; },
		statusChanged() { if (this.form.delivery_status === "Deferred" && Number(this.form.periods_delivered || 0) === 1) this.form.periods_delivered = 0; else if (this.form.delivery_status !== "Deferred" && Number(this.form.periods_delivered || 0) <= 0) this.form.periods_delivered = 1; },
		async deliveryDateChanged() { this.form.lesson_plan = ""; this.lessonPlanOptions = []; await this.loadInstructorOptions(); },
		async instructorChanged() { this.form.lesson_plan = ""; await this.loadLessonPlanOptions(); },
		async loadInstructorOptions() {
			if (!this.scheme?.name || !this.form.delivered_on) return;
			this.instructorsLoading = true; this.formError = ""; this.form.lesson_plan = ""; this.lessonPlanOptions = [];
			try {
				const response = await frappe.call("eduedge.api.scheme_delivery.get_delivery_instructor_options", { name: this.scheme.name, delivered_on: this.form.delivered_on });
				this.instructorOptions = response.message || [];
				if (this.instructorOptions.length === 1) this.form.instructor = this.instructorOptions[0].value;
				else if (!this.instructorOptions.some((row) => row.value === this.form.instructor)) this.form.instructor = "";
				if (this.form.instructor) await this.loadLessonPlanOptions();
			} catch (error) { this.instructorOptions = []; this.form.instructor = ""; this.formError = error?.message || "Eligible Instructors could not be loaded."; }
			finally { this.instructorsLoading = false; }
		},
		async loadLessonPlanOptions() {
			if (!this.scheme?.name || !this.form.item_reference || !this.form.delivered_on || !this.form.instructor) { this.lessonPlanOptions = []; return; }
			this.lessonPlansLoading = true; this.formError = "";
			try {
				const response = await frappe.call("eduedge.api.scheme_delivery.get_delivery_lesson_plan_options", {
					name: this.scheme.name,
					item_reference: this.form.item_reference,
					delivered_on: this.form.delivered_on,
					instructor: this.form.instructor,
				});
				this.lessonPlanOptions = response.message || [];
				if (!this.lessonPlanOptions.some((row) => row.value === this.form.lesson_plan)) this.form.lesson_plan = "";
			} catch (error) { this.lessonPlanOptions = []; this.form.lesson_plan = ""; this.formError = error?.message || "Approved Lesson Plans could not be loaded."; }
			finally { this.lessonPlansLoading = false; }
		},
		attachEvidence() {
			if (!frappe.ui?.FileUploader) {
				this.formError = __("File upload is unavailable in this session.");
				return;
			}
			new frappe.ui.FileUploader({
				allow_multiple: false,
				on_success: (file) => {
					this.form.evidence = file?.file_url || "";
					this.formError = "";
				},
			});
		},
		openLessonPlan(name) { window.open(`/app/eduedge-lesson-plan/${encodeURIComponent(name)}`, "_blank", "noopener,noreferrer"); },
		async submitUpdate() {
			if (!this.canSubmit || this.saving) return;
			this.saving = true; this.formError = "";
			try {
				const response = await frappe.call({
					method: "eduedge.api.scheme_delivery.log_scheme_delivery",
					type: "POST",
					args: {
						name: this.scheme.name,
						item_reference: this.form.item_reference,
						delivery_status: this.form.delivery_status,
						delivered_on: this.form.delivered_on,
						periods_delivered: this.form.periods_delivered,
						instructor: this.form.instructor || undefined,
						lesson_plan: this.form.lesson_plan || undefined,
						notes: this.form.notes || undefined,
						evidence: this.form.evidence || undefined,
					},
				});
				this.state = response.message?.state || this.state;
				this.closeUpdate();
				frappe.show_alert({ message: __("Scheme delivery update recorded"), indicator: "green" });
				this.$emit("updated", this.state);
			} catch (error) { this.formError = error?.message || "Scheme delivery update could not be recorded."; }
			finally { this.saving = false; }
		},
	},
};
</script>

<style scoped>
.delivery-panel { display:grid; gap:1rem; padding-top:.4rem; border-top:1px solid var(--border-color); }.delivery-heading,.delivery-item-main,.delivery-item-actions,.form-actions { display:flex; align-items:center; justify-content:space-between; gap:.65rem; flex-wrap:wrap; }.delivery-heading h3,.delivery-heading h4 { margin:0; }.delivery-summary { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.6rem; }.delivery-summary div { display:grid; gap:.15rem; padding:.65rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); }.delivery-summary span { font-size:.78rem; color:var(--text-muted); }.delivery-summary strong { font-size:1.15rem; }.coverage-track,.item-progress { height:.4rem; overflow:hidden; border-radius:999px; background:var(--control-bg); }.coverage-track span,.item-progress span { display:block; height:100%; background:var(--primary); }.delivery-items,.history-list { display:grid; gap:.6rem; }.delivery-item,.delivery-form,.history-list article { display:grid; gap:.6rem; padding:.75rem; border:1px solid var(--border-color); border-radius:9px; background:var(--control-bg); }.delivery-item-main { display:grid; grid-template-columns:auto minmax(0,1fr) auto; }.delivery-item-main > div,.history-list article > div { display:grid; gap:.16rem; }.delivery-item-main small,.delivery-item-actions small,.history-list small,.delivery-form-grid small,.evidence-field small { color:var(--text-muted); }.sequence { display:grid; place-items:center; width:2rem; height:2rem; border-radius:50%; border:1px solid var(--border-color); font-weight:700; }.delivery-form-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.65rem; }.delivery-form-grid label,.evidence-field { display:grid; gap:.3rem; font-weight:600; }.delivery-form-grid .wide { grid-column:1/-1; }.evidence-actions,.history-meta span { display:flex; align-items:center; gap:.6rem; flex-wrap:wrap; }.evidence-actions a,.history-meta a,.link-button { color:var(--primary); font-weight:600; text-decoration:none; }.link-button { border:0; background:transparent; padding:0; cursor:pointer; }.delivery-error { color:var(--red-600,#b42318); }.history-list article { grid-template-columns:minmax(0,1fr) minmax(12rem,.6fr); }.history-meta { display:grid; gap:.35rem; justify-items:end; }.history-list article > small { text-align:right; } @media (max-width:750px) { .delivery-summary,.delivery-form-grid { grid-template-columns:1fr 1fr; }.delivery-item-main,.history-list article { grid-template-columns:1fr; }.history-meta { justify-items:start; } } @media (max-width:520px) { .delivery-summary,.delivery-form-grid { grid-template-columns:1fr; }.delivery-form-grid .wide { grid-column:auto; } }
</style>
