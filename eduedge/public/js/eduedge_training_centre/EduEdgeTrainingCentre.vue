<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="identity.tenant_name || ''"
		:branch-name="identity.branch_name || ''"
		:user-name="overview.user?.full_name || ''"
		:menu-items="shellMenu"
		active-route="/app/eduedge-training-centre"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Guided Learning"
					title="EduEdge Training Centre"
					subtitle="Role-based, step-by-step learning for students, teachers, school leaders, administrators, and ProcessEdge support staff."
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Preparing your training path..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error"
				title="Training Centre could not load"
				:message="error"
				action-label="Try again"
				@retry="loadOverview"
			/>
			<template v-else>
				<section v-if="!activeModule" class="etc-overview">
					<div class="etc-path-panel">
						<div>
							<p class="edge-eyebrow">Your learning path</p>
							<h2>{{ selectedAudienceLabel }}</h2>
							<p>{{ selectedAudienceDescription }}</p>
						</div>
						<label v-if="overview.audiences.length > 1" class="etc-path-select">
							<span>View training for</span>
							<select v-model="selectedAudience" class="form-control" @change="changeAudience">
								<option v-for="audience in overview.audiences" :key="audience.key" :value="audience.key">
									{{ audience.label }}
								</option>
							</select>
						</label>
					</div>

					<EdgeDashboardLayout min-column-width="11rem">
						<EdgeStatCard label="Modules" :value="overview.summary.total" helper="Required and shared guides" />
						<EdgeStatCard label="Completed" :value="overview.summary.completed" helper="Finished modules" />
						<EdgeStatCard label="In progress" :value="overview.summary.in_progress" helper="Continue where you stopped" />
						<EdgeStatCard label="Estimated time" :value="`${overview.summary.estimated_minutes} min`" helper="Approximate guided time" />
						<EdgeStatCard label="Path progress" :value="`${overview.summary.progress_percent}%`" helper="Completed module ratio" />
					</EdgeDashboardLayout>

					<EdgeActionBar label="Training modules">
						<template #actions>
							<input v-model="query" class="form-control input-sm etc-search" placeholder="Search your modules" />
						</template>
					</EdgeActionBar>

					<div v-if="filteredModules.length" class="etc-module-grid">
						<article v-for="module in filteredModules" :key="module.module_id" class="etc-module-card" :class="{ 'is-locked': module.locked }">
							<div class="etc-module-card__top">
								<div>
									<p class="edge-eyebrow">{{ module.category }} · {{ module.estimated_minutes }} min</p>
									<h3>{{ module.title }}</h3>
								</div>
								<EdgeStatusBadge :label="module.locked ? 'Locked' : module.status" :status="module.status" :tone="moduleTone(module)" />
							</div>
							<p>{{ module.short_description }}</p>
							<div class="etc-progress-track" aria-hidden="true"><span :style="{ width: `${module.progress_percent}%` }"></span></div>
							<div class="etc-module-meta">
								<span>{{ module.step_count }} guided steps</span>
								<span>{{ module.has_video ? 'Video available' : module.video_display_status }}</span>
							</div>
							<p v-if="module.locked" class="etc-lock-message">Complete: {{ module.missing_prerequisites.join(', ') }}</p>
							<button type="button" class="edge-button edge-button--primary" :disabled="module.locked" @click="openModule(module)">
								{{ moduleButtonLabel(module) }}
							</button>
						</article>
					</div>
					<EdgeEmptyState v-else title="No training modules found" message="Try a different search term or training path." />
				</section>

				<section v-else class="etc-reader">
					<div class="etc-reader-header">
						<button type="button" class="edge-button" @click="closeModule">Back to modules</button>
						<div class="etc-reader-heading">
							<p class="edge-eyebrow">{{ activeModule.category }} · {{ activeModule.role_group }}</p>
							<h2>{{ activeModule.title }}</h2>
							<p>{{ activeModule.short_description }}</p>
						</div>
						<EdgeStatusBadge :label="activeModule.status" :status="activeModule.status" :tone="moduleTone(activeModule)" />
					</div>

					<div class="etc-progress-summary">
						<strong>{{ activeModule.progress_percent }}% complete</strong>
						<div class="etc-progress-track"><span :style="{ width: `${activeModule.progress_percent}%` }"></span></div>
					</div>

					<div class="etc-tabs" role="tablist" aria-label="Training module sections">
						<button v-for="tab in tabs" :key="tab.key" type="button" class="edge-button" :class="{ 'edge-button--primary': activeTab === tab.key }" @click="showTab(tab.key)">
							{{ tab.label }}
						</button>
					</div>

					<EdgeLoadingState v-if="moduleLoading" message="Loading training guide..." />
					<div v-else-if="activeTab === 'guide'" ref="guide" class="etc-panel" @click="handleGuideClick" v-html="guideHtml"></div>
					<div v-else-if="activeTab === 'steps'" class="etc-panel etc-step-list">
						<label v-for="(step, index) in activeModule.steps" :key="step.step_id" class="etc-step" :class="{ 'is-complete': completedSteps.includes(step.step_id) }">
							<input type="checkbox" :checked="completedSteps.includes(step.step_id)" :disabled="saving" @change="toggleStep(step, $event.target.checked)" />
							<span class="etc-step__number">{{ index + 1 }}</span>
							<span class="etc-step__copy">
								<strong>{{ step.title }}</strong>
								<small>{{ step.description }}</small>
								<button v-if="step.action_route" type="button" class="edge-button etc-step__action" @click.prevent="openRoute(step.action_route)">
									{{ step.action_label || 'Open related page' }}
								</button>
							</span>
						</label>
						<div class="etc-complete-row">
							<span>{{ completedSteps.length }} of {{ activeModule.steps.length }} steps complete</span>
							<button type="button" class="edge-button edge-button--primary" :disabled="saving || completedSteps.length !== activeModule.steps.length" @click="markComplete">
								Mark module complete
							</button>
						</div>
					</div>
					<div v-else-if="activeTab === 'video'" class="etc-panel">
						<div v-if="activeModule.video_embed_url" class="etc-video-frame">
							<iframe :src="activeModule.video_embed_url" :title="activeModule.video_title || activeModule.title" loading="lazy" allowfullscreen></iframe>
						</div>
						<div v-else class="etc-video-placeholder">
							<h3>{{ activeModule.video_display_status }}</h3>
							<p>The training guide and step checklist are available now. ProcessEdge can add an approved YouTube video without changing the page.</p>
						</div>
					</div>
					<div v-else class="etc-panel" ref="practice" v-html="practiceHtml"></div>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { openEduEdgeRoute } from "../eduedge_ui/navigation";
import { renderTrainingFlowcharts, renderTrainingMarkdown } from "./markdown";

const EMPTY_OVERVIEW = {
	user: {},
	selected_audience: "",
	primary_audience: "",
	audiences: [],
	modules: [],
	summary: { total: 0, completed: 0, in_progress: 0, estimated_minutes: 0, progress_percent: 0 },
};

export default {
	name: "EduEdgeTrainingCentre",
	data() {
		return {
			loading: true,
			error: "",
			moduleLoading: false,
			saving: false,
			query: "",
			overview: { ...EMPTY_OVERVIEW },
			selectedAudience: "",
			activeModule: null,
			activeTab: "guide",
			guideHtml: "",
			practiceHtml: "",
			completedSteps: [],
			tabs: [
				{ key: "guide", label: "Read Guide" },
				{ key: "steps", label: "Step Checklist" },
				{ key: "video", label: "Watch Video" },
				{ key: "practice", label: "Practice Exercise" },
			],
		};
	},
	computed: {
		identity() {
			const boot = frappe.boot?.eduedge_ui_identity || {};
			return {
				tenant_name: boot.tenant_name || "",
				branch_name: boot.active_branch?.label || boot.branch_name || "",
			};
		},
		shellMenu() {
			const menu = [
				{ section: "Help & Training", sectionIcon: "book", label: "Training Centre", route: "/app/eduedge-training-centre", icon: "book", description: "Role-based guided learning" },
			];
			if (this.overview.primary_audience !== "student") {
				menu.unshift({ section: "Overview", sectionIcon: "home", label: "EduEdge Home", route: "/app/eduedge-home", icon: "home", description: "School command centre" });
			}
			return menu;
		},
		filteredModules() {
			const query = this.query.trim().toLowerCase();
			if (!query) return this.overview.modules;
			return this.overview.modules.filter((module) =>
				`${module.title} ${module.short_description} ${module.category} ${module.role_group}`.toLowerCase().includes(query),
			);
		},
		selectedAudienceRecord() {
			return this.overview.audiences.find((item) => item.key === this.selectedAudience) || {};
		},
		selectedAudienceLabel() {
			return this.selectedAudienceRecord.label || "Your EduEdge training";
		},
		selectedAudienceDescription() {
			return this.selectedAudienceRecord.description || "Complete the modules in order and use the practice exercises to confirm readiness.";
		},
	},
	mounted() {
		this.loadOverview();
	},
	methods: {
		openRoute: openEduEdgeRoute,
		moduleTone(module) {
			if (module.locked) return "neutral";
			if (module.status === "Completed") return "success";
			if (module.status === "In Progress") return "warning";
			return "neutral";
		},
		moduleButtonLabel(module) {
			if (module.locked) return "Complete prerequisite first";
			if (module.status === "Completed") return "Review module";
			if (module.status === "In Progress") return "Continue module";
			return "Start module";
		},
		async loadOverview() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.training_centre.get_training_overview", {
					audience: this.selectedAudience || undefined,
				});
				this.overview = response.message || { ...EMPTY_OVERVIEW };
				this.selectedAudience = this.overview.selected_audience;
				const requested = new URLSearchParams(window.location.search).get("module");
				if (requested && !this.activeModule) {
					const module = this.overview.modules.find((item) => item.module_id === requested);
					if (module && !module.locked) await this.openModule(module, false);
				}
			} catch (error) {
				this.error = error?.message || "Your EduEdge training path could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		async changeAudience() {
			this.activeModule = null;
			this.updateUrl();
			await this.loadOverview();
		},
		async openModule(module, updateUrl = true) {
			if (module.locked) return;
			this.moduleLoading = true;
			this.activeTab = "guide";
			try {
				const response = await frappe.call("eduedge.api.training_centre.get_training_module_content", { module_id: module.module_id });
				const payload = response.message || {};
				this.activeModule = payload.module;
				this.completedSteps = [...(this.activeModule.completed_step_ids || [])];
				this.guideHtml = renderTrainingMarkdown(payload.markdown || "");
				this.practiceHtml = renderTrainingMarkdown(payload.practice_exercise || "## Practice Exercise\nNo practice exercise has been published yet.");
				if (updateUrl) this.updateUrl(module.module_id);
				await frappe.call("eduedge.api.training_centre.save_training_progress", {
					module_id: module.module_id,
					completed_step_ids: this.completedSteps,
					status: this.activeModule.status === "Completed" ? "Completed" : "In Progress",
				});
				this.$nextTick(() => renderTrainingFlowcharts(this.$refs.guide));
			} catch (error) {
				frappe.msgprint({ title: __("Unable to open training module"), message: error?.message || __("The guide could not be loaded."), indicator: "red" });
				this.activeModule = null;
			} finally {
				this.moduleLoading = false;
			}
		},
		closeModule() {
			this.activeModule = null;
			this.activeTab = "guide";
			this.updateUrl();
			this.loadOverview();
		},
		showTab(tab) {
			this.activeTab = tab;
			this.$nextTick(() => {
				if (tab === "guide") renderTrainingFlowcharts(this.$refs.guide);
				if (tab === "practice") renderTrainingFlowcharts(this.$refs.practice);
			});
		},
		async toggleStep(step, checked) {
			const previous = [...this.completedSteps];
			this.completedSteps = checked
				? [...new Set([...this.completedSteps, step.step_id])]
				: this.completedSteps.filter((item) => item !== step.step_id);
			try {
				await this.saveProgress("In Progress");
			} catch (_error) {
				this.completedSteps = previous;
			}
		},
		async markComplete() {
			await this.saveProgress("Completed");
			frappe.show_alert({ message: __("Training module completed"), indicator: "green" });
		},
		async saveProgress(status) {
			if (!this.activeModule) return;
			this.saving = true;
			try {
				const response = await frappe.call("eduedge.api.training_centre.save_training_progress", {
					module_id: this.activeModule.module_id,
					completed_step_ids: this.completedSteps,
					status,
				});
				const progress = response.message || {};
				Object.assign(this.activeModule, progress);
				this.completedSteps = [...(progress.completed_step_ids || this.completedSteps)];
			} catch (error) {
				frappe.msgprint({ title: __("Progress could not be saved"), message: error?.message || __("Try again."), indicator: "red" });
				throw error;
			} finally {
				this.saving = false;
			}
		},
		handleGuideClick(event) {
			const link = event.target.closest?.("[data-training-module]");
			if (!link) return;
			event.preventDefault();
			const module = this.overview.modules.find((item) => item.module_id === link.dataset.trainingModule);
			if (module && !module.locked) this.openModule(module);
		},
		updateUrl(moduleId = "") {
			const params = new URLSearchParams();
			if (this.selectedAudience) params.set("audience", this.selectedAudience);
			if (moduleId) params.set("module", moduleId);
			const query = params.toString();
			window.history.pushState({}, "", `/app/eduedge-training-centre${query ? `?${query}` : ""}`);
		},
	},
};
</script>

<style scoped>
.etc-overview, .etc-reader { display: grid; gap: var(--edge-section-gap, 1rem); }
.etc-path-panel, .etc-reader-header, .etc-progress-summary { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 1rem; border: 1px solid var(--edge-color-border, var(--border-color)); border-radius: var(--edge-radius-lg, 12px); background: var(--edge-color-surface, var(--card-bg)); }
.etc-path-panel h2, .etc-reader-heading h2 { margin: .2rem 0 .35rem; }
.etc-path-panel p, .etc-reader-heading p, .etc-module-card p { color: var(--text-muted); margin-bottom: 0; }
.etc-path-select { display: grid; gap: .35rem; min-width: min(22rem, 100%); font-size: .75rem; font-weight: 650; }
.etc-search { min-width: min(22rem, 70vw); }
.etc-module-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr)); gap: 1rem; }
.etc-module-card { display: flex; flex-direction: column; gap: .8rem; min-height: 17rem; padding: 1rem; border: 1px solid var(--edge-color-border, var(--border-color)); border-radius: var(--edge-radius-lg, 12px); background: var(--edge-color-surface, var(--card-bg)); }
.etc-module-card.is-locked { opacity: .72; }
.etc-module-card__top, .etc-module-meta, .etc-complete-row { display: flex; align-items: flex-start; justify-content: space-between; gap: .75rem; }
.etc-module-card h3 { margin: .25rem 0 0; font-size: 1rem; }
.etc-module-meta { color: var(--text-muted); font-size: .72rem; margin-top: auto; }
.etc-lock-message { color: var(--orange-700, #b54708) !important; font-size: .72rem; }
.etc-progress-track { height: .45rem; overflow: hidden; border-radius: 999px; background: var(--edge-color-surface-muted, var(--fg-color)); }
.etc-progress-track span { display: block; height: 100%; border-radius: inherit; background: var(--edge-color-brand-600, var(--primary)); transition: width .2s ease; }
.etc-reader-header { align-items: flex-start; }
.etc-reader-heading { flex: 1; min-width: 0; }
.etc-progress-summary { display: grid; grid-template-columns: auto minmax(12rem, 1fr); }
.etc-tabs { display: flex; flex-wrap: wrap; gap: .5rem; }
.etc-panel { padding: 1rem; border: 1px solid var(--edge-color-border, var(--border-color)); border-radius: var(--edge-radius-lg, 12px); background: var(--edge-color-surface, var(--card-bg)); }
.etc-step-list { display: grid; gap: .75rem; }
.etc-step { display: grid; grid-template-columns: auto 2rem minmax(0, 1fr); gap: .7rem; align-items: flex-start; padding: .9rem; border: 1px solid var(--edge-color-border, var(--border-color)); border-radius: .75rem; cursor: pointer; }
.etc-step.is-complete { background: color-mix(in srgb, var(--edge-color-success-50, #ecfdf3) 80%, transparent); }
.etc-step__number { display: inline-flex; align-items: center; justify-content: center; width: 1.8rem; height: 1.8rem; border-radius: 50%; background: var(--edge-color-brand-50, var(--fg-color)); color: var(--edge-color-brand-700, var(--primary)); font-weight: 750; }
.etc-step__copy { display: grid; gap: .25rem; }
.etc-step__copy small { color: var(--text-muted); }
.etc-step__action { justify-self: start; margin-top: .35rem; }
.etc-complete-row { align-items: center; padding-top: .5rem; }
.etc-video-frame { aspect-ratio: 16 / 9; width: 100%; overflow: hidden; border-radius: .75rem; background: #000; }
.etc-video-frame iframe { width: 100%; height: 100%; border: 0; }
.etc-video-placeholder { display: grid; place-items: center; min-height: 16rem; padding: 2rem; text-align: center; color: var(--text-muted); }
:deep(.edge-training-markdown) { line-height: 1.65; }
:deep(.edge-training-markdown h2), :deep(.edge-training-markdown h3), :deep(.edge-training-markdown h4) { margin-top: 1.4rem; }
:deep(.edge-training-markdown pre) { overflow: auto; padding: .8rem; border: 1px solid var(--edge-color-border, var(--border-color)); border-radius: .6rem; background: var(--edge-color-surface-muted, var(--fg-color)); }
:deep(.edge-training-markdown blockquote) { margin: 1rem 0; padding: .75rem 1rem; border-left: 3px solid var(--edge-color-brand-600, var(--primary)); background: var(--edge-color-brand-50, var(--fg-color)); }
:deep(.edge-training-guide-bullet), :deep(.edge-training-guide-number), :deep(.edge-training-guide-check) { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: .5rem; margin: .35rem 0; }
:deep(.edge-training-table-wrap) { overflow-x: auto; }
:deep(.edge-training-table) { width: 100%; border-collapse: collapse; }
:deep(.edge-training-table th), :deep(.edge-training-table td) { padding: .55rem; border: 1px solid var(--edge-color-border, var(--border-color)); text-align: left; }
:deep(.edge-training-flow) { display: flex; align-items: center; gap: .55rem; overflow-x: auto; padding: 1rem; border: 1px solid var(--edge-color-border, var(--border-color)); border-radius: .75rem; background: var(--edge-color-surface-muted, var(--fg-color)); }
:deep(.edge-training-flow--td), :deep(.edge-training-flow--tb), :deep(.edge-training-flow--bt) { flex-direction: column; }
:deep(.edge-training-flow__node) { min-width: 10rem; max-width: 18rem; padding: .65rem .8rem; border: 1px solid var(--edge-color-brand-200, var(--border-color)); border-radius: .6rem; background: var(--edge-color-surface, var(--card-bg)); text-align: center; font-weight: 650; }
:deep(.edge-training-flow__node.is-decision) { border-radius: 999px; }
:deep(.edge-training-flow__arrow) { color: var(--edge-color-brand-700, var(--primary)); font-size: 1.25rem; font-weight: 800; }
@media (max-width: 700px) { .etc-path-panel, .etc-reader-header, .etc-complete-row { align-items: stretch; flex-direction: column; } .etc-progress-summary { grid-template-columns: 1fr; } .etc-step { grid-template-columns: auto 1.8rem minmax(0, 1fr); } }
</style>
