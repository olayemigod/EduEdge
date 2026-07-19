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

				<section v-if="readiness.blockers.length" class="eduedge-panel eduedge-panel--blocker">
					<div class="eduedge-panel__heading">
						<EdgeIcon name="shield" size="sm" />
						<div>
							<h3>Blockers</h3>
							<p>Resolve these items before the school can be treated as operationally ready.</p>
						</div>
					</div>
					<ul><li v-for="item in readiness.blockers" :key="item">{{ item }}</li></ul>
				</section>

				<section v-if="readiness.warnings.length" class="eduedge-panel eduedge-panel--warning">
					<div class="eduedge-panel__heading">
						<EdgeIcon name="bell" size="sm" />
						<div>
							<h3>Warnings</h3>
							<p>These items do not always block access, but they should be reviewed before rollout.</p>
						</div>
					</div>
					<ul><li v-for="item in readiness.warnings" :key="item">{{ item }}</li></ul>
				</section>

				<section class="eduedge-panel">
					<div class="eduedge-panel__heading">
						<EdgeIcon name="settings" size="sm" />
						<div>
							<h3>Recommended actions</h3>
							<p>Use these guided actions to complete only the foundation items that remain outstanding.</p>
						</div>
					</div>
					<div v-if="!readiness.recommended_actions.length" class="eduedge-ready-message">
						<EdgeIcon name="check" size="sm" />
						<span>No setup actions are outstanding.</span>
					</div>
					<div v-else class="eduedge-actions">
						<button
							v-for="(action, index) in readiness.recommended_actions"
							:key="action.key || action.route || action.label"
							type="button"
							class="edge-button eduedge-setup-action"
							:class="{ 'edge-button--primary': index === 0 }"
							:title="action.description || action.label"
							@click="runAction(action)"
						>
							<span class="eduedge-setup-action__icon">
								<EdgeIcon :name="action.icon || 'settings'" size="sm" />
							</span>
							<span class="eduedge-setup-action__copy">
								<strong>{{ action.label }}</strong>
								<small v-if="action.description">{{ action.description }}</small>
							</span>
						</button>
					</div>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>

	<EdgeFormDialog
		:open="recordModal.open"
		:title="recordModal.title"
		:subtitle="recordModal.subtitle"
		:fields="recordModal.fields"
		:model-value="recordModal.values"
		:field-errors="recordModal.fieldErrors"
		:error="recordModal.error"
		:loading="recordModal.loading"
		:busy="recordModal.busy"
		:submit-label="recordModal.submitLabel"
		:show-full-form="Boolean(recordModal.fullFormRoute)"
		@update:model-value="updateModalValues"
		@field-change="onModalFieldChange"
		@search-options="onModalSearch"
		@submit="saveModalRecord"
		@open-full-form="openModalFullForm"
		@close="closeModal"
	/>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";
import {
	closeRecordModal,
	createRecordModalState,
	handleRecordModalFieldChange,
	openRecordFullForm,
	openRecordModal,
	saveRecordModal,
	searchRecordModalOptions,
	updateRecordModalValues,
} from "../eduedge_ui/modal_records";

const QUICK_RESOURCES = {
	"EduEdge School Branch": "school_branch",
	"EduEdge Program Offering": "program_offering",
};

export default {
	name: "EduEdgeSetupCenter",
	data() {
		return {
			loading: true,
			error: "",
			menuItems: EDUEDGE_MENU_ITEMS,
			recordModal: createRecordModalState(),
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
		async runAction(action) {
			if (!action) return;
			const resource = QUICK_RESOURCES[action.doctype];
			if (action.action_type === "new_doc" && resource) {
				await openRecordModal(this.recordModal, {
					resource,
					context: {
						company: this.readiness.school.default_company || "",
						school_branch: this.readiness.school.default_school_branch || "",
						academic_year: this.readiness.school.current_academic_year || "",
						academic_term: this.readiness.school.current_academic_term || "",
					},
				});
				return;
			}
			if (
				action.action_type === "new_doc" &&
				action.doctype &&
				typeof frappe.new_doc === "function"
			) {
				frappe.new_doc(action.doctype);
				return;
			}
			this.openRoute(action.route);
		},
		updateModalValues(values) { updateRecordModalValues(this.recordModal, values); },
		onModalFieldChange(payload) { handleRecordModalFieldChange(this.recordModal, payload); },
		onModalSearch(payload) { return searchRecordModalOptions(this.recordModal, payload); },
		closeModal() { closeRecordModal(this.recordModal); },
		openModalFullForm() { openRecordFullForm(this.recordModal); },
		async saveModalRecord() {
			const result = await saveRecordModal(this.recordModal);
			if (!result) return;
			closeRecordModal(this.recordModal);
			frappe.show_alert({ message: __("EduEdge record saved"), indicator: "green" });
			await this.loadReadiness();
		},
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
	gap: var(--edge-card-gap, 1rem);
	margin-bottom: var(--edge-section-gap, 1.25rem);
}
.eduedge-panel {
	background: var(--edge-color-surface, var(--card-bg));
	border: 1px solid var(--edge-color-border, var(--border-color));
	border-radius: var(--edge-radius-lg, 12px);
	box-shadow: none;
	margin-bottom: var(--edge-section-gap, 1rem);
	padding: clamp(1rem, 2vw, 1.25rem);
}
.eduedge-panel--blocker { border-left: 4px solid var(--red-500, #d64545); }
.eduedge-panel--warning { border-left: 4px solid var(--orange-500, #d97706); }
.eduedge-panel__heading {
	align-items: flex-start;
	display: grid;
	gap: .75rem;
	grid-template-columns: 2rem minmax(0, 1fr);
	margin-bottom: .8rem;
}
.eduedge-panel__heading > .edge-icon {
	align-items: center;
	background: var(--edge-color-brand-50, #edf5ff);
	border: 1px solid var(--edge-color-brand-100, #dcecff);
	border-radius: .65rem;
	color: var(--edge-color-brand-700, #174ea6);
	display: inline-flex;
	height: 2rem;
	justify-content: center;
	width: 2rem;
}
.eduedge-panel h3 { margin: 0; }
.eduedge-panel p {
	color: var(--edge-color-ink-500, var(--text-muted));
	font-size: .8rem;
	line-height: 1.45;
	margin: .2rem 0 0;
}
.eduedge-panel ul { margin-bottom: 0; padding-left: 1.25rem; }
.eduedge-panel li + li { margin-top: .35rem; }
.eduedge-actions {
	display: grid;
	gap: .75rem;
	grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
}
.eduedge-setup-action {
	align-items: center;
	display: grid;
	gap: .75rem;
	grid-template-columns: 2rem minmax(0, 1fr);
	justify-content: stretch;
	min-height: 4.25rem;
	padding: .7rem .8rem;
	text-align: left;
	width: 100%;
}
.eduedge-setup-action__icon {
	align-items: center;
	background: var(--edge-color-brand-50, #edf5ff);
	border: 1px solid var(--edge-color-brand-100, #dcecff);
	border-radius: .6rem;
	color: var(--edge-color-brand-700, #174ea6);
	display: inline-flex;
	height: 2rem;
	justify-content: center;
	width: 2rem;
}
.edge-button--primary .eduedge-setup-action__icon {
	background: rgb(255 255 255 / 14%);
	border-color: rgb(255 255 255 / 28%);
	color: #fff;
}
.eduedge-setup-action__copy { display: grid; min-width: 0; }
.eduedge-setup-action__copy strong { font-size: .82rem; line-height: 1.25; }
.eduedge-setup-action__copy small {
	font-size: .7rem;
	line-height: 1.35;
	margin-top: .18rem;
	opacity: .78;
}
.eduedge-ready-message {
	align-items: center;
	background: var(--edge-color-accent-soft, #e8f8f0);
	border: 1px solid color-mix(in srgb, var(--edge-color-accent, #22a06b) 26%, transparent);
	border-radius: .75rem;
	color: var(--edge-color-accent, #14804a);
	display: flex;
	font-weight: 650;
	gap: .55rem;
	padding: .8rem .9rem;
}
@media (max-width: 35.99rem) {
	.eduedge-actions { grid-template-columns: minmax(0, 1fr); }
}
</style>
