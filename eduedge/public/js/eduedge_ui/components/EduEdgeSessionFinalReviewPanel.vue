<template>
	<section class="session-final-shell">
		<header class="session-final-header">
			<div>
				<p class="edge-eyebrow">Final Review & Activation</p>
				<h3>Activate Academic Session</h3>
				<p>Review the live readiness evidence, resolve hard blockers, acknowledge any remaining warnings, then activate the Session.</p>
			</div>
			<button type="button" class="edge-button" :disabled="loading" @click="load">{{ loading ? "Refreshing..." : "Refresh review" }}</button>
		</header>

		<div v-if="error" class="session-final-message is-error">{{ error }}</div>
		<div v-else-if="loading && !payload" class="session-final-message">Loading final review...</div>
		<template v-else-if="payload">
			<div :class="['session-final-gate', statusClass(payload.readiness?.overall?.status)]">
				<div>
					<small>Activation gate</small>
					<strong>{{ payload.status === 'Active' ? 'Active' : payload.readiness?.overall?.status }}</strong>
					<span>{{ payload.activation?.message }}</span>
				</div>
				<div class="session-final-counts">
					<span><small>Hard blockers</small><strong>{{ payload.activation?.hard_blockers || 0 }}</strong></span>
					<span><small>Warnings</small><strong>{{ payload.activation?.warnings || 0 }}</strong></span>
				</div>
			</div>

			<div v-if="payload.previous_active" class="session-final-previous">
				<div><small>Current active Session</small><strong>{{ payload.previous_active.academic_year }}</strong></div>
				<span>Activating this Session will close launch {{ payload.previous_active.name }} while preserving its activation audit.</span>
			</div>

			<div v-if="payload.readiness?.blockers?.length" class="session-final-section">
				<h4>Hard blockers</h4>
				<article v-for="row in payload.readiness.blockers" :key="row.key" class="session-final-item is-blocked">
					<div><strong>{{ row.label }}</strong><small>{{ row.message }}</small></div>
					<ul v-if="row.issues?.length"><li v-for="issue in row.issues" :key="issue">{{ issue }}</li></ul>
					<button v-if="row.route" type="button" class="edge-button" @click="openRoute(row.route)">Resolve</button>
				</article>
			</div>

			<div v-if="payload.readiness?.warnings?.length" class="session-final-section">
				<h4>Warnings requiring review</h4>
				<article v-for="row in payload.readiness.warnings" :key="row.key" class="session-final-item is-attention">
					<div><strong>{{ row.label }}</strong><small>{{ row.message }}</small></div>
					<ul v-if="row.issues?.length"><li v-for="issue in row.issues" :key="issue">{{ issue }}</li></ul>
					<button v-if="row.route" type="button" class="edge-button" @click="openRoute(row.route)">Review</button>
				</article>
			</div>

			<div v-if="!payload.readiness?.blockers?.length && !payload.readiness?.warnings?.length" class="session-final-clear">
				<strong>No readiness exceptions remain.</strong>
				<span>The current Session records satisfy all implemented launch checks.</span>
			</div>

			<div v-if="payload.status === 'Active'" class="session-final-audit">
				<strong>Activation recorded</strong>
				<div><span>Activated by</span><b>{{ payload.audit?.activated_by }}</b></div>
				<div><span>Activated on</span><b>{{ formatDateTime(payload.audit?.activated_on) }}</b></div>
				<div><span>Snapshot hash</span><code>{{ payload.audit?.readiness_snapshot_hash }}</code></div>
				<div v-if="payload.audit?.previous_active_academic_year"><span>Previous active Session</span><b>{{ payload.audit.previous_active_academic_year }}</b></div>
			</div>

			<div class="session-final-policy">
				<strong>Activation policy</strong>
				<span>Hard blockers cannot be overridden. Warnings require an explicit acknowledgement. Activation stores a hashed immutable readiness snapshot and serialises the Institution so two Sessions cannot be activated concurrently.</span>
			</div>

			<div class="session-final-actions">
				<button type="button" class="edge-button" @click="$emit('save-step', 'final_review')">Save Final Review here</button>
				<button
					v-if="payload.status !== 'Active'"
					type="button"
					class="edge-button edge-button--primary"
					:disabled="activating || !payload.activation?.allowed"
					@click="requestActivation"
				>
					{{ activating ? "Activating..." : "Activate Session" }}
				</button>
				<span v-else class="session-final-active-label">Academic Session Active</span>
			</div>
		</template>
	</section>
</template>

<script>
const GET_METHOD = "eduedge.api.session_launch_final_review.get_session_launch_final_review";
const ACTIVATE_METHOD = "eduedge.api.session_launch_final_review.activate_session_launch";

export default {
	name: "EduEdgeSessionFinalReviewPanel",
	props: {
		launchName: { type: String, required: true },
		academicYear: { type: String, default: "" },
		institution: { type: String, default: "" },
		branch: { type: String, default: "" },
	},
	emits: ["save-step", "final-review-updated", "activated"],
	data() {
		return { loading: false, activating: false, error: "", payload: null };
	},
	watch: {
		launchName() { this.load(); },
		academicYear() { this.load(); },
	},
	mounted() { this.load(); },
	methods: {
		async load() {
			if (!this.launchName) return;
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call(GET_METHOD, { launch: this.launchName });
				this.payload = response.message || null;
				this.$emit("final-review-updated", {
					status: this.payload?.status || "",
					ready: Boolean(this.payload?.activation?.allowed),
					message: this.payload?.activation?.message || "",
				});
			} catch (error) {
				this.error = error?.message || "Final Session review could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		statusClass(status) {
			if (status === "Ready") return "is-ready";
			if (status === "Blocked") return "is-blocked";
			return "is-attention";
		},
		requestActivation() {
			if (!this.payload?.activation?.allowed || this.activating) return;
			if (this.payload.activation.warning_acknowledgement_required) {
				this.openWarningAcknowledgement();
				return;
			}
			frappe.confirm(
				__("Activate Academic Session {0}? This will preserve an immutable readiness snapshot and close any previously active Session Launch for this Institution.", [this.academicYear || ""]),
				() => this.activate("")
			);
		},
		openWarningAcknowledgement() {
			const dialog = new frappe.ui.Dialog({
				title: __("Acknowledge Session readiness warnings"),
				fields: [
					{ fieldname: "guidance", fieldtype: "HTML", options: `<div class="session-final-dialog-guidance">${frappe.utils.escape_html(__("Hard blockers are already clear. Explain why the remaining non-blocking warnings are accepted for this activation. This acknowledgement is stored in the immutable activation snapshot."))}</div>` },
					{ fieldname: "warning_acknowledgement", fieldtype: "Small Text", label: __("Warning acknowledgement"), reqd: 1 },
				],
				primary_action_label: __("Acknowledge & Activate"),
				primary_action: async (values) => {
					const note = String(values.warning_acknowledgement || "").trim();
					if (note.length < 10) {
						frappe.msgprint({ title: __("More detail required"), message: __("Enter a meaningful acknowledgement before activating with warnings."), indicator: "orange" });
						return;
					}
					dialog.hide();
					await this.activate(note);
				},
			});
			dialog.$wrapper?.addClass("session-final-dialog");
			dialog.show();
		},
		async activate(warningAcknowledgement) {
			this.activating = true;
			this.error = "";
			try {
				const response = await frappe.call({
					method: ACTIVATE_METHOD,
					type: "POST",
					args: { launch: this.launchName, warning_acknowledgement: warningAcknowledgement || undefined },
				});
				this.payload = response.message?.context || this.payload;
				frappe.show_alert({ message: __("Academic Session activated"), indicator: "green" });
				this.$emit("activated", this.payload);
				this.$emit("final-review-updated", { status: "Active", ready: true, message: "Academic Session activated." });
			} catch (error) {
				this.error = error?.message || "Academic Session could not be activated.";
			} finally {
				this.activating = false;
			}
		},
		openRoute(route) {
			const params = new URLSearchParams();
			if (this.academicYear) params.set("academic_year", this.academicYear);
			if (this.institution) params.set("institution", this.institution);
			if (this.branch) params.set("branch", this.branch);
			window.open(`${route}${params.toString() ? `?${params}` : ""}`, "_blank", "noopener,noreferrer");
		},
		formatDateTime(value) { return value ? frappe.datetime.str_to_user(value) : ""; },
	},
};
</script>

<style scoped>
.session-final-shell{display:grid;gap:1rem;padding:1rem;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg);color:var(--text-color)}
.session-final-header{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start}.session-final-header h3{margin:.1rem 0 .3rem;color:var(--text-color)}.session-final-header p{margin:0;max-width:62rem;color:var(--text-muted)}
.session-final-gate{display:flex;justify-content:space-between;gap:1rem;padding:.85rem;border:1px solid var(--border-color);border-radius:10px;background:var(--control-bg)}.session-final-gate>div:first-child{display:grid;gap:.2rem}.session-final-gate small,.session-final-gate span{color:var(--text-muted)}.session-final-gate.is-ready{border-color:var(--green-500,#16803c)}.session-final-gate.is-blocked{border-color:var(--red-500,#b42318)}
.session-final-counts{display:grid;grid-template-columns:repeat(2,minmax(6rem,1fr));gap:.45rem}.session-final-counts>span{display:grid;gap:.1rem;padding:.45rem;border:1px solid var(--border-color);border-radius:7px;background:var(--card-bg)}
.session-final-previous,.session-final-clear,.session-final-policy,.session-final-audit{display:grid;gap:.3rem;padding:.75rem;border:1px dashed var(--border-color);border-radius:8px}.session-final-previous>div{display:grid;gap:.1rem}.session-final-previous span,.session-final-clear span,.session-final-policy span{color:var(--text-muted)}
.session-final-section{display:grid;gap:.55rem}.session-final-section h4{margin:0;color:var(--text-color)}.session-final-item{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:.5rem;padding:.75rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg)}.session-final-item>div{display:grid;gap:.15rem}.session-final-item small{color:var(--text-muted)}.session-final-item ul{grid-column:1/-1;margin:0;padding-left:1.1rem}.session-final-item.is-blocked{border-color:var(--red-400,#b42318)}.session-final-item.is-attention{border-color:var(--orange-400,#b54708)}
.session-final-audit>div{display:grid;grid-template-columns:10rem minmax(0,1fr);gap:.5rem}.session-final-audit span{color:var(--text-muted)}.session-final-audit code{overflow-wrap:anywhere}.session-final-actions{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap}.session-final-active-label{font-weight:700;color:var(--green-600,#16803c)}.session-final-message{padding:.7rem;border-radius:8px;background:var(--control-bg);color:var(--text-muted)}.session-final-message.is-error{color:var(--red-600,#b42318)}
:global(.session-final-dialog-guidance){padding:.75rem;border:1px solid var(--border-color);border-radius:8px;background:var(--control-bg);color:var(--text-muted)}
@media(max-width:900px){.session-final-header,.session-final-gate{flex-direction:column}.session-final-item{grid-template-columns:1fr}.session-final-counts{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
