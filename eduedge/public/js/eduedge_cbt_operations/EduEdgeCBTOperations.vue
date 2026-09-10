<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="context.tenant_name || ''"
		:branch-name="context.current_branch?.branch_name || ''"
		:user-name="context.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-cbt-operations"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Computer-Based Testing"
					title="CBT Operations"
					subtitle="Govern school CBT locally and review centrally activated EduEdge Exams access for this site."
					:action-label="hasAnyCreatePermission ? 'Create New' : null"
					@action="openPreferredCreateRoute"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading CBT operations..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error"
				title="CBT operations could not load"
				:message="error"
				action-label="Try again"
				@retry="loadContext"
			/>
			<template v-else>
				<EdgeFilterBar title="Examination ownership">
					<div class="eduedge-cbt-filters">
						<label>
							<span>Examination Scope</span>
							<select v-model="filters.exam_scope" class="form-control" @change="changeScope">
								<option value="School Examination">School Examination</option>
								<option v-if="context.can_manage_public" value="EduEdge Public Examination">
									EduEdge Public Examination Authoring
								</option>
							</select>
						</label>
						<label v-if="isSchoolScope">
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="changeBranch">
								<option value="">Select branch</option>
								<option v-for="branch in context.allowed_branches" :key="branch.name" :value="branch.name">
									{{ branch.branch_name || branch.name }}
								</option>
							</select>
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button edge-button--primary" @click="loadContext">Refresh</button>
					</template>
				</EdgeFilterBar>

				<div v-if="isSchoolScope && !filters.branch" class="eduedge-cbt-scope-note">
					Select a School Branch / Campus to view the CBT records allowed by your role permissions.
				</div>

				<section class="eduedge-cbt-panel eduedge-cbt-access-panel">
					<div class="eduedge-cbt-panel-heading">
						<div>
							<p class="edge-eyebrow">CoreEdge activation</p>
							<h2>EduEdge Exams access for this site</h2>
						</div>
						<EdgeStatusBadge
							:label="publicAccessLabel"
							:status="publicAccessLabel"
							:tone="publicAccessTone"
						/>
					</div>
					<p class="eduedge-cbt-access-summary">{{ publicAccessMessage }}</p>
					<div class="eduedge-cbt-capability-grid">
						<div v-for="capability in publicCapabilityRows" :key="capability.key" class="eduedge-cbt-capability">
							<div>
								<strong>{{ capability.label }}</strong>
								<span>{{ capability.description }}</span>
							</div>
							<EdgeStatusBadge
								:label="capability.allowed ? 'Available' : 'Not Activated'"
								:status="capability.allowed ? 'available' : 'not-activated'"
								:tone="capability.allowed ? 'success' : 'neutral'"
							/>
						</div>
					</div>
					<p class="eduedge-cbt-access-note">
						Standalone and white-label sites consume centrally governed exam versions through CoreEdge. Public question banks and answer keys are not copied into editable tenant records.
					</p>
				</section>

				<EdgeDashboardLayout min-column-width="12rem">
					<EdgeStatCard v-if="canReadCentres" label="Examination Centres" :value="context.counts.centres || 0" helper="Centres in the selected scope" />
					<EdgeStatCard v-if="canReadCentres" label="Active Centres" :value="context.counts.enabled_centres || 0" helper="Available for future schedules" />
					<EdgeStatCard v-if="canReadTemplates" label="Exam Templates" :value="context.counts.templates || 0" helper="Reusable examination definitions" />
					<EdgeStatCard v-if="canReadTemplates" label="Approved Templates" :value="context.counts.approved_templates || 0" helper="Ready for scheduling" />
					<EdgeStatCard
						v-if="canReadQuestions"
						label="Approved Questions"
						:value="context.counts.approved_questions || 0"
						helper="Eligible for exam templates"
					/>
				</EdgeDashboardLayout>

				<section v-if="canReadCentres || canReadTemplates" class="eduedge-cbt-grid">
					<article v-if="canReadCentres" class="eduedge-cbt-panel">
						<div class="eduedge-cbt-panel-heading">
							<div>
								<p class="edge-eyebrow">Centre readiness</p>
								<h2>Examination centres</h2>
							</div>
							<button type="button" class="edge-button" @click="openRoute('/app/eduedge-examination-centre')">
								Open all centres
							</button>
						</div>
						<EdgeEmptyState
							v-if="!context.centres.length"
							title="No examination centres found"
							description="No active centre matches the selected branch and your current record access."
							:action-label="canCreateCentres ? 'Create examination centre' : null"
							@action="openRoute('/app/eduedge-examination-centre/new-eduedge-examination-centre')"
						/>
						<div v-else class="eduedge-cbt-list">
							<button
								v-for="centre in context.centres"
								:key="centre.name"
								type="button"
								class="eduedge-cbt-row"
								@click="openRoute(`/app/eduedge-examination-centre/${centre.name}`)"
							>
								<div>
									<strong>{{ centre.centre_name || centre.name }}</strong>
									<span>
										{{ centre.centre_code }} · {{ centre.location || 'No location' }} · Capacity {{ centre.capacity || 0 }}
										<template v-if="centre.public_hosting_status === 'Approved'"> · Public host approved</template>
									</span>
								</div>
								<EdgeStatusBadge
									:label="centre.centre_status || (centre.enabled ? 'Active' : 'Draft')"
									:status="centre.centre_status || (centre.enabled ? 'Active' : 'Draft')"
									:tone="centreTone(centre.centre_status || (centre.enabled ? 'Active' : 'Draft'))"
								/>
							</button>
						</div>
					</article>

					<article v-if="canReadTemplates" class="eduedge-cbt-panel">
						<div class="eduedge-cbt-panel-heading">
							<div>
								<p class="edge-eyebrow">Reusable definitions</p>
								<h2>Exam templates</h2>
							</div>
							<button type="button" class="edge-button" @click="openRoute('/app/eduedge-cbt-exam-template')">
								Open all templates
							</button>
						</div>
						<EdgeEmptyState
							v-if="!context.templates.length"
							title="No exam templates found"
							description="No template matches the selected branch and your current record access."
							:action-label="canCreateTemplates ? 'Create exam template' : null"
							@action="openRoute('/app/eduedge-cbt-exam-template/new-eduedge-cbt-exam-template')"
						/>
						<div v-else class="eduedge-cbt-list">
							<button
								v-for="template in context.templates"
								:key="template.name"
								type="button"
								class="eduedge-cbt-row"
								@click="openRoute(`/app/eduedge-cbt-exam-template/${template.name}`)"
							>
								<div>
									<strong>{{ template.template_title || template.name }}</strong>
									<span>
										{{ template.course }} · {{ template.duration_minutes }} minutes ·
										{{ template.question_count || 0 }} questions · {{ template.total_marks || 0 }} marks
									</span>
								</div>
								<EdgeStatusBadge
									:label="template.status"
									:status="template.status"
									:tone="statusTone(template.status)"
								/>
							</button>
						</div>
					</article>
				</section>

				<section class="eduedge-cbt-grid">
					<article v-if="canReadQuestions" class="eduedge-cbt-panel">
						<div class="eduedge-cbt-panel-heading">
							<div>
								<p class="edge-eyebrow">Question governance</p>
								<h2>Question bank readiness</h2>
							</div>
							<button type="button" class="edge-button" @click="openRoute('/app/eduedge-cbt-question')">
								Open question bank
							</button>
						</div>
						<div class="eduedge-cbt-readiness">
							<div><span>Approved questions</span><strong>{{ context.counts.approved_questions || 0 }}</strong></div>
							<div><span>Draft or under review</span><strong>{{ context.counts.draft_questions || 0 }}</strong></div>
							<p>Only approved questions from the matching ownership scope, branch, and course can be selected in a template.</p>
						</div>
					</article>

					<article class="eduedge-cbt-panel">
						<div class="eduedge-cbt-panel-heading">
							<div>
								<p class="edge-eyebrow">Next implementation boundary</p>
								<h2>Candidate scheduling and attempts</h2>
							</div>
						</div>
						<div class="eduedge-cbt-roadmap">
							<p>Exam templates are definitions only. They do not yet create candidate attempts or publish results.</p>
							<ul>
								<li>Central public-exam catalogue references and signed launch sessions</li>
								<li>Exam schedule and candidate eligibility</li>
								<li>Server-authoritative timing and one active attempt</li>
								<li>Browser answer saving and pending-sync visibility</li>
								<li>Invigilator monitoring and signed result return</li>
							</ul>
						</div>
					</article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const PUBLIC_CAPABILITY_META = [
	["catalog", "Exam Catalogue", "Browse centrally published EduEdge Exams"],
	["assign", "Candidate Assignment", "Assign entitled candidates from this site"],
	["host", "Centre Hosting", "Host public exams at a verified school centre"],
	["launch", "Candidate Launch", "Create signed central examination sessions"],
	["results", "Results Access", "Receive signed public-exam result records"],
	["author", "Content Authoring", "Create ProcessEdge public questions and templates"],
];

export default {
	name: "EduEdgeCBTOperations",
	data() {
		return {
			loading: true,
			error: "",
			menuItems: EDUEDGE_MENU_ITEMS,
			filters: { exam_scope: "School Examination", branch: "" },
			context: {
				user: {},
				current_branch: null,
				allowed_branches: [],
				counts: {},
				centres: [],
				templates: [],
				questions: [],
				permissions: {
					examination_centre: {},
					cbt_question: {},
					cbt_template: {},
				},
				can_manage_public: false,
				public_exam_access: { authority_site: false, platform_mode: "standalone", capabilities: {} },
			},
		};
	},
	computed: {
		isSchoolScope() {
			return this.filters.exam_scope === "School Examination";
		},
		canReadCentres() {
			return Boolean(this.context.permissions?.examination_centre?.read);
		},
		canCreateCentres() {
			return Boolean(this.context.permissions?.examination_centre?.create);
		},
		canReadQuestions() {
			return Boolean(this.context.permissions?.cbt_question?.read);
		},
		canCreateQuestions() {
			return Boolean(this.context.permissions?.cbt_question?.create);
		},
		canReadTemplates() {
			return Boolean(this.context.permissions?.cbt_template?.read);
		},
		canCreateTemplates() {
			return Boolean(this.context.permissions?.cbt_template?.create);
		},
		hasAnyCreatePermission() {
			return this.canCreateCentres || this.canCreateQuestions || this.canCreateTemplates;
		},
		publicCapabilityRows() {
			const capabilities = this.context.public_exam_access?.capabilities || {};
			return PUBLIC_CAPABILITY_META.map(([key, label, description]) => ({
				key,
				label,
				description,
				allowed: Boolean(capabilities[key]?.allowed),
			}));
		},
		publicAccessLabel() {
			if (this.context.public_exam_access?.authority_site) return "Authority Site";
			const enabled = this.publicCapabilityRows.filter((row) => row.allowed).length;
			return enabled ? `${enabled} Capabilities Active` : "Not Activated";
		},
		publicAccessTone() {
			return this.publicCapabilityRows.some((row) => row.allowed) ? "success" : "neutral";
		},
		publicAccessMessage() {
			if (this.context.public_exam_access?.authority_site) {
				return "This site is the controlled ProcessEdge authoring authority for EduEdge public examinations.";
			}
			if (this.context.public_exam_access?.capabilities?.catalog?.allowed) {
				return "CoreEdge has activated selected EduEdge Exams capabilities for this tenant. Public content remains centrally governed.";
			}
			if (this.context.public_exam_access?.platform_mode === "remote") {
				return "This site is connected to CoreEdge, but EduEdge Exams access has not been activated for the current tenant or user.";
			}
			return "School CBT remains available locally. Connect this site to CoreEdge to activate EduEdge public-exam catalogue, hosting, launch, and result capabilities.";
		},
	},
	mounted() {
		this.loadContext();
	},
	methods: {
		openRoute: openEduEdgeRoute,
		openPreferredCreateRoute() {
			if (this.canCreateTemplates) {
				this.openRoute("/app/eduedge-cbt-exam-template/new-eduedge-cbt-exam-template");
				return;
			}
			if (this.canCreateQuestions) {
				this.openRoute("/app/eduedge-question-builder");
				return;
			}
			if (this.canCreateCentres) {
				this.openRoute("/app/eduedge-examination-centre/new-eduedge-examination-centre");
			}
		},
		statusTone(status) {
			if (status === "Approved") return "success";
			if (status === "Under Review") return "warning";
			return "neutral";
		},
		centreTone(status) {
			if (status === "Active") return "success";
			if (status === "Suspended") return "warning";
			if (status === "Retired") return "danger";
			return "neutral";
		},
		async loadContext() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.cbt.get_cbt_operations_context", {
					exam_scope: this.filters.exam_scope,
					branch: this.filters.branch || undefined,
				});
				this.context = response.message || this.context;
				this.filters = { ...this.filters, ...(this.context.filters || {}) };
			} catch (error) {
				this.error = error?.message || "CBT operations could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		async changeScope() {
			if (!this.isSchoolScope) this.filters.branch = "";
			await this.loadContext();
		},
		async changeBranch() {
			if (!this.filters.branch) {
				await this.loadContext();
				return;
			}
			await frappe.call("eduedge.api.branch_context.switch_school_branch", {
				branch: this.filters.branch,
			});
			await this.loadContext();
		},
	},
};
</script>

<style scoped>
.eduedge-cbt-filters {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
	gap: 1rem;
	width: min(100%, 38rem);
}

.eduedge-cbt-filters label {
	display: grid;
	gap: 0.35rem;
	font-size: 0.82rem;
	font-weight: 600;
	color: var(--edge-text-muted, #64748b);
}

.eduedge-cbt-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(min(100%, 28rem), 1fr));
	gap: 1rem;
	margin-top: 1rem;
}

.eduedge-cbt-panel {
	min-width: 0;
	padding: 1.25rem;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: var(--edge-radius-lg, 0.9rem);
	background: var(--edge-surface, #fff);
	box-shadow: var(--edge-shadow-sm, 0 1px 2px rgba(15, 23, 42, 0.06));
}

.eduedge-cbt-access-panel {
	margin: 1rem 0;
}

.eduedge-cbt-panel-heading {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 1rem;
	margin-bottom: 1rem;
}

.eduedge-cbt-panel-heading h2 {
	margin: 0.2rem 0 0;
	font-size: 1.05rem;
}

.eduedge-cbt-list,
.eduedge-cbt-capability-grid {
	display: grid;
	gap: 0.65rem;
}

.eduedge-cbt-capability-grid {
	grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
}

.eduedge-cbt-capability,
.eduedge-cbt-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 1rem;
	padding: 0.85rem;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: var(--edge-radius-md, 0.7rem);
}

.eduedge-cbt-row {
	width: 100%;
	background: transparent;
	text-align: left;
}

.eduedge-cbt-row:hover {
	border-color: var(--edge-primary, #1f6feb);
	background: var(--edge-primary-soft, #eff6ff);
}

.eduedge-cbt-capability > div,
.eduedge-cbt-row div {
	display: grid;
	gap: 0.25rem;
	min-width: 0;
}

.eduedge-cbt-capability span,
.eduedge-cbt-row span,
.eduedge-cbt-readiness p,
.eduedge-cbt-roadmap,
.eduedge-cbt-scope-note,
.eduedge-cbt-access-summary,
.eduedge-cbt-access-note {
	color: var(--edge-text-muted, #64748b);
}

.eduedge-cbt-capability span,
.eduedge-cbt-row span {
	font-size: 0.82rem;
}

.eduedge-cbt-row span {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.eduedge-cbt-access-note {
	margin: 0.85rem 0 0;
	font-size: 0.84rem;
}

.eduedge-cbt-readiness {
	display: grid;
	gap: 0.75rem;
}

.eduedge-cbt-readiness div {
	display: flex;
	justify-content: space-between;
	gap: 1rem;
	padding-bottom: 0.65rem;
	border-bottom: 1px solid var(--edge-border, #e2e8f0);
}

.eduedge-cbt-scope-note,
.eduedge-cbt-roadmap {
	padding: 1rem;
	border-radius: var(--edge-radius-md, 0.7rem);
	background: var(--edge-surface-subtle, #f8fafc);
}

.eduedge-cbt-scope-note {
	margin-top: 1rem;
}

.eduedge-cbt-roadmap ul {
	margin: 0.75rem 0 0;
	padding-left: 1.1rem;
}

@media (max-width: 640px) {
	.eduedge-cbt-panel-heading,
	.eduedge-cbt-capability,
	.eduedge-cbt-row {
		align-items: stretch;
		flex-direction: column;
	}

	.eduedge-cbt-row span {
		white-space: normal;
	}
}
</style>
