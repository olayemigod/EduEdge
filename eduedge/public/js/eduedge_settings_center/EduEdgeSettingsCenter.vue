<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="schoolIdentity.name || ''"
		branch-name="Settings"
		:menu-items="menuItems"
		active-route="/app/eduedge-settings-center"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Administration"
					title="EduEdge Settings"
					subtitle="Configure school defaults, branding, branch governance, report cards, and optional product features."
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading EduEdge settings..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error"
				title="Settings could not load"
				:message="error"
				action-label="Try again"
				@retry="loadSettings"
			/>
			<template v-else>
				<section class="eduedge-settings-shell">
					<nav class="eduedge-settings-tabs" aria-label="EduEdge settings sections">
						<button
							v-for="tab in tabs"
							:key="tab.key"
							type="button"
							class="eduedge-settings-tab"
							:class="{ active: activeTab === tab.key }"
							:aria-selected="activeTab === tab.key ? 'true' : 'false'"
							@click="selectTab(tab.key)"
						>
							{{ tab.label }}
						</button>
					</nav>

					<div v-if="currentTab" class="eduedge-settings-panel">
						<div class="eduedge-settings-panel__heading">
							<div>
								<p class="edge-eyebrow">{{ currentTab.label }}</p>
								<h2>{{ currentTab.label }}</h2>
								<p>{{ currentTab.description }}</p>
							</div>
							<EdgeStatusBadge
								v-if="activeTab === 'branch_access'"
								:label="branchEnforcement.enabled ? 'Enforcement active' : 'Enforcement inactive'"
								:status="branchEnforcement.enabled ? 'active' : 'inactive'"
								:tone="branchEnforcement.enabled ? 'success' : 'warning'"
							/>
						</div>

						<div class="eduedge-settings-form">
							<div
								v-for="field in currentTab.fields"
								:key="field.fieldname"
								class="eduedge-settings-field"
								:class="{ 'eduedge-settings-field--check': field.type === 'Check' }"
							>
								<label v-if="field.type === 'Check'" class="eduedge-settings-check">
									<input
										type="checkbox"
										:checked="truthy(values[field.fieldname])"
										:disabled="!canWrite || saving"
										@change="setValue(field.fieldname, $event.target.checked ? 1 : 0)"
									/>
									<span>{{ field.label }}</span>
								</label>

								<template v-else-if="field.type === 'Attach Image'">
									<label>{{ field.label }}</label>
									<div class="eduedge-branding-control">
										<div class="eduedge-branding-preview">
											<img v-if="values[field.fieldname]" :src="values[field.fieldname]" alt="EduEdge logo preview" />
											<EdgeIcon v-else name="graduation" size="md" />
										</div>
										<div class="eduedge-branding-actions">
											<button type="button" class="edge-button" :disabled="!canWrite || saving" @click="uploadLogo(field.fieldname)">
												Upload image
											</button>
											<button
												v-if="values[field.fieldname]"
												type="button"
												class="edge-button"
												:disabled="!canWrite || saving"
												@click="setValue(field.fieldname, '')"
											>
												Use default mark
											</button>
										</div>
									</div>
								</template>

								<template v-else>
									<label :for="`settings-${field.fieldname}`">{{ field.label }}</label>
									<select
										v-if="field.type === 'Link'"
										:id="`settings-${field.fieldname}`"
										:value="values[field.fieldname] || ''"
										class="form-control"
										:disabled="!canWrite || saving"
										@change="linkChanged(field, $event.target.value)"
									>
										<option value="">Not selected</option>
										<option v-for="option in field.options || []" :key="option.value" :value="option.value">
											{{ option.label }}
										</option>
									</select>
									<input
										v-else
										:id="`settings-${field.fieldname}`"
										:value="values[field.fieldname] ?? ''"
										:type="field.type === 'Percent' ? 'number' : 'text'"
										:min="field.min"
										:max="field.max"
										class="form-control"
										:disabled="!canWrite || saving"
										@input="setValue(field.fieldname, $event.target.value)"
									/>
								</template>
							</div>
						</div>

						<div v-if="activeTab === 'branch_access'" class="eduedge-enforcement-guidance">
							<div>
								<strong>User Branch Access enforcement</strong>
								<p>Activation is managed in Branch Governance so campus coverage and test-user readiness checks cannot be bypassed.</p>
							</div>
							<button type="button" class="edge-button" @click="openRoute(branchEnforcement.manage_route)">Open Branch Governance</button>
						</div>

						<p v-if="saveError" class="eduedge-settings-error" role="alert">{{ saveError }}</p>
						<EdgeActionBar :label="canWrite ? 'Changes apply after validation and normal Frappe permissions.' : 'Your role has read-only access to these settings.'">
							<template #actions>
								<button type="button" class="edge-button" :disabled="saving" @click="resetCurrentTab">Reset</button>
								<button
									v-if="canWrite"
									type="button"
									class="edge-button edge-button--primary"
									:disabled="saving"
									@click="saveCurrentTab"
								>
									{{ saving ? 'Saving...' : `Save ${currentTab.label}` }}
								</button>
							</template>
						</EdgeActionBar>
					</div>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

export default {
	name: "EduEdgeSettingsCenter",
	data() {
		return {
			loading: true,
			saving: false,
			error: "",
			saveError: "",
			activeTab: "defaults",
			tabs: [],
			values: {},
			originalValues: {},
			canWrite: false,
			branchEnforcement: { enabled: false, manage_route: "/app/eduedge-branch-governance" },
			menuItems: EDUEDGE_MENU_ITEMS,
		};
	},
	computed: {
		currentTab() {
			return this.tabs.find((tab) => tab.key === this.activeTab) || this.tabs[0] || null;
		},
		schoolIdentity() {
			return frappe.boot?.eduedge_ui_identity?.school || {};
		},
	},
	mounted() {
		this.loadSettings();
	},
	methods: {
		openRoute: openEduEdgeRoute,
		truthy(value) {
			return value === true || Number(value) === 1;
		},
		selectTab(key) {
			this.activeTab = key;
			this.saveError = "";
		},
		setValue(fieldname, value) {
			this.values = { ...this.values, [fieldname]: value };
			this.saveError = "";
		},
		async linkChanged(field, value) {
			this.setValue(field.fieldname, value);
			if (field.fieldname !== "default_company") return;
			this.setValue("default_school_branch", "");
			try {
				const response = await frappe.call("eduedge.api.settings_center.get_default_branch_options", { company: value || undefined });
				this.tabs = this.tabs.map((tab) =>
					tab.key !== "defaults"
						? tab
						: {
							...tab,
							fields: tab.fields.map((item) =>
								item.fieldname === "default_school_branch" ? { ...item, options: response.message || [] } : item
							),
						}
				);
			} catch (error) {
				this.saveError = error?.message || "School Branch options could not be loaded.";
			}
		},
		async loadSettings() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.settings_center.get_settings_center");
				const state = response.message || {};
				this.tabs = state.tabs || [];
				this.values = { ...(state.values || {}) };
				this.originalValues = { ...(state.values || {}) };
				this.canWrite = Boolean(state.can_write);
				this.branchEnforcement = state.branch_enforcement || this.branchEnforcement;
				if (!this.tabs.some((tab) => tab.key === this.activeTab)) this.activeTab = this.tabs[0]?.key || "defaults";
			} catch (error) {
				this.error = error?.message || "EduEdge Settings could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		resetCurrentTab() {
			if (!this.currentTab) return;
			const next = { ...this.values };
			for (const field of this.currentTab.fields || []) next[field.fieldname] = this.originalValues[field.fieldname];
			this.values = next;
			this.saveError = "";
		},
		async saveCurrentTab() {
			if (!this.currentTab || !this.canWrite || this.saving) return;
			this.saving = true;
			this.saveError = "";
			const payload = {};
			for (const field of this.currentTab.fields || []) payload[field.fieldname] = this.values[field.fieldname];
			try {
				const response = await frappe.call("eduedge.api.settings_center.save_settings_tab", {
					tab: this.currentTab.key,
					values: JSON.stringify(payload),
				});
				const saved = response.message?.values || payload;
				this.values = { ...this.values, ...saved };
				this.originalValues = { ...this.originalValues, ...saved };
				frappe.show_alert({ message: __("EduEdge settings saved"), indicator: "green" });
			} catch (error) {
				this.saveError = error?.message || "This settings section could not be saved.";
			} finally {
				this.saving = false;
			}
		},
		uploadLogo(fieldname) {
			if (!this.canWrite || typeof frappe.ui?.FileUploader !== "function") {
				this.saveError = "The Frappe file uploader is unavailable.";
				return;
			}
			new frappe.ui.FileUploader({
				allow_multiple: false,
				restrictions: { allowed_file_types: ["image/*"] },
				on_success: (file) => {
					this.setValue(fieldname, file.file_url || file.file_name || "");
				},
			});
		},
	},
};
</script>

<style scoped>
.eduedge-settings-shell {
	background: var(--edge-color-surface, var(--card-bg));
	border: 1px solid var(--edge-color-border, var(--border-color));
	border-radius: var(--edge-radius-lg, 12px);
	display: grid;
	grid-template-columns: minmax(12rem, 15rem) minmax(0, 1fr);
	min-height: 32rem;
	overflow: hidden;
}
.eduedge-settings-tabs {
	border-right: 1px solid var(--edge-color-border, var(--border-color));
	display: flex;
	flex-direction: column;
	gap: .25rem;
	padding: 1rem;
}
.eduedge-settings-tab {
	background: transparent;
	border: 1px solid transparent;
	border-radius: .6rem;
	color: var(--edge-color-ink-700, var(--text-color));
	font-weight: 650;
	padding: .7rem .75rem;
	text-align: left;
}
.eduedge-settings-tab:hover { background: var(--edge-color-surface-soft, var(--control-bg)); }
.eduedge-settings-tab.active {
	background: var(--edge-color-brand-50, #edf5ff);
	border-color: var(--edge-color-brand-100, #dcecff);
	color: var(--edge-color-brand-700, #174ea6);
}
.eduedge-settings-panel { padding: clamp(1rem, 2vw, 1.5rem); }
.eduedge-settings-panel__heading {
	align-items: flex-start;
	display: flex;
	gap: 1rem;
	justify-content: space-between;
	margin-bottom: 1.25rem;
}
.eduedge-settings-panel__heading h2 { margin: .2rem 0; }
.eduedge-settings-panel__heading p { color: var(--text-muted); margin-bottom: 0; max-width: 48rem; }
.eduedge-settings-form {
	display: grid;
	gap: 1rem;
	grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
	margin-bottom: 1.25rem;
}
.eduedge-settings-field { display: grid; gap: .4rem; }
.eduedge-settings-field > label { font-weight: 650; }
.eduedge-settings-field--check { align-content: center; }
.eduedge-settings-check { align-items: center; display: flex; gap: .65rem; min-height: 2.75rem; }
.eduedge-settings-check input { height: 1.05rem; width: 1.05rem; }
.eduedge-branding-control {
	align-items: center;
	border: 1px solid var(--edge-color-border, var(--border-color));
	border-radius: .75rem;
	display: flex;
	gap: 1rem;
	padding: .8rem;
}
.eduedge-branding-preview {
	align-items: center;
	background: var(--edge-color-brand-50, #edf5ff);
	border: 1px solid var(--edge-color-brand-100, #dcecff);
	border-radius: .7rem;
	display: flex;
	height: 4.5rem;
	justify-content: center;
	overflow: hidden;
	width: 4.5rem;
}
.eduedge-branding-preview img { height: 100%; object-fit: contain; width: 100%; }
.eduedge-branding-actions { display: flex; flex-wrap: wrap; gap: .5rem; }
.eduedge-enforcement-guidance {
	align-items: center;
	background: var(--edge-color-surface-soft, var(--control-bg));
	border: 1px solid var(--edge-color-border, var(--border-color));
	border-radius: .75rem;
	display: flex;
	gap: 1rem;
	justify-content: space-between;
	margin-bottom: 1rem;
	padding: .9rem;
}
.eduedge-enforcement-guidance p { color: var(--text-muted); margin: .2rem 0 0; }
.eduedge-settings-error { color: var(--red-600, #b42318); }
@media (max-width: 47.99rem) {
	.eduedge-settings-shell { grid-template-columns: 1fr; }
	.eduedge-settings-tabs { border-bottom: 1px solid var(--edge-color-border, var(--border-color)); border-right: 0; flex-direction: row; overflow-x: auto; }
	.eduedge-settings-tab { white-space: nowrap; }
	.eduedge-settings-panel__heading, .eduedge-enforcement-guidance { align-items: stretch; flex-direction: column; }
}
</style>
