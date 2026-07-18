<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="readiness.school.default_company || ''"
		:branch-name="readiness.school.default_school_branch || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-setup-center"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Foundation"
					title="EduEdge Setup Center"
					subtitle="Complete the school, academic, and platform foundation before operational rollout."
					action-label="Open Branch Governance"
					@action="openRoute('/app/eduedge-branch-governance')"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Checking EduEdge readiness..." />
			<EdgeErrorState
				v-else-if="error"
				title="Unable to check setup"
				:message="error"
				action-label="Try again"
				@retry="loadReadiness"
			/>
			<template v-else>
				<div class="eduedge-stat-grid">
					<EdgeStatCard label="Overall Readiness" :value="readiness.ready ? 'Ready' : 'Action Required'" />
					<EdgeStatCard label="Enabled Branches" :value="readiness.school.enabled_branch_count" />
					<EdgeStatCard label="Active Branch Assignments" :value="readiness.school.active_branch_access_count || 0" />
					<EdgeStatCard
						label="Branch Enforcement"
						:value="readiness.school.branch_access_enforcement_enabled ? 'Active' : 'Not Active'"
					/>
					<EdgeStatCard
						label="Accounting Ready Branches"
						:value="`${readiness.school.accounting_ready_branch_count || 0}/${readiness.school.enabled_branch_count || 0}`"
					/>
					<EdgeStatCard label="Programme Offerings" :value="readiness.school.active_program_offering_count || 0" />
					<EdgeStatCard label="Platform Mode" :value="readiness.platform.mode" />
					<EdgeStatCard label="Current Academic Year" :value="readiness.school.current_academic_year || 'Not configured'" />
				</div>

				<section v-if="readiness.blockers.length" class="eduedge-panel">
					<h3>Blockers</h3>
					<ul><li v-for="item in readiness.blockers" :key="item">{{ item }}</li></ul>
				</section>

				<section v-if="readiness.warnings.length" class="eduedge-panel">
					<h3>Warnings</h3>
					<ul><li v-for="item in readiness.warnings" :key="item">{{ item }}</li></ul>
				</section>

				<section class="eduedge-panel">
					<h3>Recommended actions</h3>
					<div v-if="!readiness.recommended_actions.length">No setup actions are outstanding.</div>
					<div class="eduedge-actions">
						<button
							v-for="action in readiness.recommended_actions"
							:key="action.route"
							class="edge-button edge-button--primary"
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
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

export default {
	name: "EduEdgeSetupCenter",
	data() {
		return {
			loading: true,
			error: "",
			menuItems: EDUEDGE_MENU_ITEMS,
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
	mounted() { this.loadReadiness(); },
	methods: {
		openRoute: openEduEdgeRoute,
		async loadReadiness() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.setup.get_setup_readiness");
				this.readiness = response.message || this.readiness;
			} catch (error) {
				this.error = error?.message || "EduEdge setup readiness could not be loaded.";
			} finally { this.loading = false; }
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
.eduedge-panel h3 { margin-top: 0; }
.eduedge-actions { display: flex; flex-wrap: wrap; gap: 0.75rem; }
</style>
