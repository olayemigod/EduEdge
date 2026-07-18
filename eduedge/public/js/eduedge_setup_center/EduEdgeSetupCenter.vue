<template>
	<EdgeAppShell app-name="EduEdge">
		<EdgePageLayout>
			<EdgePageHeader
				title="EduEdge Setup Center"
				subtitle="Complete the school, academic, and platform foundation before operational rollout."
			/>
			<EdgeLoadingState v-if="loading" message="Checking EduEdge readiness..." />
			<EdgeErrorState v-else-if="error" title="Unable to check setup" :message="error" />
			<template v-else>
				<div class="eduedge-stat-grid">
					<EdgeStatCard
						label="Overall Readiness"
						:value="readiness.ready ? 'Ready' : 'Action Required'"
					/>
					<EdgeStatCard label="Enabled Branches" :value="readiness.school.enabled_branch_count" />
					<EdgeStatCard
						label="Program Offerings"
						:value="readiness.school.active_program_offering_count || 0"
					/>
					<EdgeStatCard
						label="Current Academic Year"
						:value="readiness.school.current_academic_year || 'Not configured'"
					/>
				</div>

				<section v-if="readiness.blockers.length" class="eduedge-panel">
					<h3>Blockers</h3>
					<ul>
						<li v-for="item in readiness.blockers" :key="item">{{ item }}</li>
					</ul>
				</section>

				<section v-if="readiness.warnings.length" class="eduedge-panel">
					<h3>Warnings</h3>
					<ul>
						<li v-for="item in readiness.warnings" :key="item">{{ item }}</li>
					</ul>
				</section>

				<section class="eduedge-panel">
					<h3>Recommended actions</h3>
					<div v-if="!readiness.recommended_actions.length">No setup actions are outstanding.</div>
					<div class="eduedge-actions">
						<button
							v-for="action in readiness.recommended_actions"
							:key="action.route"
							class="btn btn-primary btn-sm"
							@click="openRoute(action.route)"
						>
							{{ action.label }}
						</button>
					</div>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
export default {
	name: "EduEdgeSetupCenter",
	data() {
		return {
			loading: true,
			error: "",
			readiness: {
				ready: false,
				blockers: [],
				warnings: [],
				recommended_actions: [],
				school: {},
				platform: {},
			},
		};
	},
	async mounted() {
		try {
			const response = await frappe.call("eduedge.api.setup.get_setup_readiness");
			this.readiness = response.message || this.readiness;
		} catch (error) {
			this.error = error?.message || "EduEdge setup readiness could not be loaded.";
		} finally {
			this.loading = false;
		}
	},
	methods: {
		openRoute(route) {
			window.location.href = route;
		},
	},
};
</script>

<style scoped>
.eduedge-stat-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
	gap: var(--edge-space-4, 1rem);
	margin-bottom: var(--edge-space-5, 1.25rem);
}

.eduedge-panel {
	border: 1px solid var(--border-color);
	border-radius: var(--edge-radius-lg, 12px);
	padding: var(--edge-space-5, 1.25rem);
	margin-bottom: var(--edge-space-4, 1rem);
	background: var(--card-bg);
}

.eduedge-panel h3 {
	margin-top: 0;
}

.eduedge-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 0.75rem;
}
</style>
