<template>
	<section class="session-operational-shell">
		<header class="session-operational-header">
			<div>
				<p class="edge-eyebrow">Operational Readiness</p>
				<h3>Session Operational Readiness</h3>
				<p>Aggregate the live Session foundation, Branch scope, learner placement, academic delivery, Assessment, CBT, calendar and attendance state before Final Review.</p>
			</div>
			<button type="button" class="edge-button" :disabled="loading" @click="load">{{ loading ? "Refreshing..." : "Refresh readiness" }}</button>
		</header>

		<div v-if="error" class="session-operational-message is-error">{{ error }}</div>
		<div v-else-if="loading && !payload" class="session-operational-message">Loading operational readiness...</div>
		<template v-else-if="payload">
			<div :class="['session-operational-overall', statusClass(payload.overall.status)]">
				<div>
					<small>Overall readiness</small>
					<strong>{{ payload.overall.status }}</strong>
					<span>{{ payload.overall.message }}</span>
				</div>
				<div class="session-operational-totals">
					<span><small>Ready</small><strong>{{ payload.overall.ready_categories }}</strong></span>
					<span><small>Attention</small><strong>{{ payload.overall.attention_categories }}</strong></span>
					<span><small>Blocked</small><strong>{{ payload.overall.blocked_categories }}</strong></span>
				</div>
			</div>

			<div class="session-operational-grid">
				<article v-for="category in payload.categories" :key="category.key" class="session-operational-card">
					<header>
						<div><strong>{{ category.label }}</strong><small>{{ category.message }}</small></div>
						<span :class="['session-operational-badge', statusClass(category.status)]">{{ category.status }}</span>
					</header>
					<div v-if="metricEntries(category).length" class="session-operational-metrics">
						<span v-for="metric in metricEntries(category)" :key="metric.key"><small>{{ metric.label }}</small><strong>{{ metric.value }}</strong></span>
					</div>
					<ul v-if="category.issues?.length" class="session-operational-issues">
						<li v-for="issue in category.issues" :key="issue">{{ issue }}</li>
					</ul>
					<button v-if="category.route" type="button" class="edge-button" @click="openRoute(category.route)">Review {{ category.label }}</button>
				</article>
			</div>

			<div class="session-operational-note">
				<strong>Read-only readiness</strong>
				<span>This review does not create or alter academic records. It recalculates from the current source records whenever refreshed.</span>
			</div>
			<div class="session-operational-actions">
				<button type="button" class="edge-button edge-button--primary" @click="$emit('save-step', 'operational_readiness')">Save Operational Readiness here</button>
			</div>
		</template>
	</section>
</template>

<script>
const GET_METHOD = "eduedge.api.session_launch_operational_readiness.get_session_launch_operational_readiness";

export default {
	name: "EduEdgeSessionOperationalReadinessPanel",
	props: {
		launchName: { type: String, required: true },
		academicYear: { type: String, default: "" },
		institution: { type: String, default: "" },
		branch: { type: String, default: "" },
	},
	emits: ["save-step", "operational-updated"],
	data() {
		return { loading: false, error: "", payload: null };
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
				this.$emit("operational-updated", this.payload?.overall || {});
			} catch (error) {
				this.error = error?.message || "Operational readiness could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		statusClass(status) {
			if (status === "Ready") return "is-ready";
			if (status === "Blocked") return "is-blocked";
			return "is-attention";
		},
		metricEntries(category) {
			return Object.entries(category?.metrics || {})
				.filter(([, value]) => value !== "" && value !== null && value !== undefined)
				.map(([key, value]) => ({ key, label: key.replaceAll("_", " "), value }));
		},
		openRoute(route) {
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
.session-operational-shell{display:grid;gap:1rem;padding:1rem;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg);color:var(--text-color)}
.session-operational-header{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start}.session-operational-header h3{margin:.1rem 0 .3rem;color:var(--text-color)}.session-operational-header p{margin:0;max-width:62rem;color:var(--text-muted)}
.session-operational-overall{display:flex;justify-content:space-between;gap:1rem;padding:.85rem;border:1px solid var(--border-color);border-radius:10px;background:var(--control-bg)}.session-operational-overall>div:first-child{display:grid;gap:.2rem}.session-operational-overall small,.session-operational-overall span{color:var(--text-muted)}.session-operational-overall.is-ready{border-color:var(--green-500,#16803c)}.session-operational-overall.is-blocked{border-color:var(--red-500,#b42318)}
.session-operational-totals{display:grid;grid-template-columns:repeat(3,minmax(5rem,1fr));gap:.45rem}.session-operational-totals>span{display:grid;gap:.1rem;min-width:5rem;padding:.45rem;border:1px solid var(--border-color);border-radius:7px;background:var(--card-bg)}
.session-operational-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem}.session-operational-card{display:grid;align-content:start;gap:.65rem;padding:.8rem;border:1px solid var(--border-color);border-radius:10px;background:var(--control-bg)}.session-operational-card header{display:flex;justify-content:space-between;gap:.7rem}.session-operational-card header>div{display:grid;gap:.15rem}.session-operational-card header small{color:var(--text-muted)}
.session-operational-badge{align-self:start;padding:.18rem .5rem;border-radius:999px;border:1px solid var(--border-color);font-size:.76rem}.session-operational-badge.is-ready{color:var(--green-600,#16803c)}.session-operational-badge.is-attention{color:var(--orange-600,#b54708)}.session-operational-badge.is-blocked{color:var(--red-600,#b42318)}
.session-operational-metrics{display:flex;flex-wrap:wrap;gap:.4rem}.session-operational-metrics>span{display:grid;gap:.08rem;min-width:6.5rem;padding:.38rem .45rem;border:1px solid var(--border-color);border-radius:6px;background:var(--card-bg)}.session-operational-metrics small{color:var(--text-muted);text-transform:capitalize}.session-operational-issues{margin:0;padding-left:1.1rem;color:var(--orange-700,#b54708)}.session-operational-card:has(.is-blocked) .session-operational-issues{color:var(--red-700,#b42318)}
.session-operational-note{display:grid;gap:.2rem;padding:.7rem;border:1px dashed var(--border-color);border-radius:8px}.session-operational-note span{color:var(--text-muted)}.session-operational-actions{display:flex;gap:.5rem;flex-wrap:wrap}.session-operational-message{padding:.7rem;border-radius:8px;background:var(--control-bg);color:var(--text-muted)}.session-operational-message.is-error{color:var(--red-600,#b42318)}
@media(max-width:1000px){.session-operational-header,.session-operational-overall{flex-direction:column}.session-operational-grid{grid-template-columns:1fr}.session-operational-totals{grid-template-columns:repeat(3,minmax(0,1fr))}}
</style>
