<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="context.tenant_name || ''"
		:branch-name="context.active_label || ''"
		:user-name="context.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-home"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Education Management"
					title="School Operations"
					subtitle="Admissions, students, classes, assessments, report cards, and branch context in one place."
					action-label="Open Academic Operations"
					@action="openRoute('/app/eduedge-academic-operations')"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading EduEdge..." :skeleton="true" />
			<EdgeErrorState v-else-if="error" title="EduEdge could not load" :message="error" action-label="Try again" @retry="loadContext" />
			<template v-else>
				<EdgeActionBar label="Working branch">
					<template #actions>
						<select
							v-model="selectedBranch"
							class="form-control input-sm eduedge-branch-select"
							:disabled="switchingBranch || !context.allowed_branches.length || (!context.can_switch_branch && context.allowed_branches.length > 1)"
							@change="switchBranch"
						>
							<option value="">Select branch or campus</option>
							<option v-for="option in context.all_branch_options" :key="option.value" :value="option.value">{{ option.label }}</option>
							<option v-for="branch in context.allowed_branches" :key="branch.name" :value="branch.name">
								{{ branch.branch_name }}{{ branch.branch_code ? ` · ${branch.branch_code}` : "" }}
							</option>
						</select>
					</template>
				</EdgeActionBar>

				<section v-if="context.requires_branch_selection" class="eduedge-attention">
					<strong>Select a branch or campus to load operational figures.</strong>
					<span>EduEdge keeps student, admission, schedule, assessment, and report-card activity inside the permitted branch context.</span>
				</section>

				<section class="eduedge-context-status">
					<div>
						<p class="edge-eyebrow">Branch governance</p>
						<strong>{{ context.active_scope === "all" ? "Authorised HQ view" : "Active campus view" }}</strong>
						<span>{{ scopeDescription }}</span>
					</div>
					<div class="eduedge-readiness-badges">
						<EdgeStatusBadge
							:label="context.branch_access_enforced ? 'Branch enforcement active' : 'Legacy branch access'"
							:status="context.branch_access_enforced ? 'enforced' : 'legacy'"
							:tone="context.branch_access_enforced ? 'success' : 'warning'"
						/>
						<button v-if="context.can_manage_branch_access" type="button" class="edge-button" @click="openRoute('/app/eduedge-user-branch-access')">
							Manage branch access
						</button>
					</div>
				</section>

				<EdgeDashboardLayout min-column-width="12rem">
					<EdgeStatCard label="Students" :value="context.counts.students" :helper="scopeHelper" />
					<EdgeStatCard label="Active Applicants" :value="context.counts.applicants" helper="Applied or approved" />
					<EdgeStatCard label="Classes" :value="context.counts.student_groups" helper="Active Student Groups" />
					<EdgeStatCard label="Today's Schedules" :value="context.counts.today_schedules" helper="Classes scheduled today" />
					<EdgeStatCard label="Assessment Plans" :value="context.counts.assessment_plans" helper="Active assessment plans" />
					<EdgeStatCard label="Pending Result Approvals" :value="context.counts.pending_result_approvals" helper="Awaiting authorized review" />
					<EdgeStatCard label="Progression Reviews" :value="context.counts.pending_progression_reviews" helper="Recommended and awaiting approval" />
					<EdgeStatCard label="Published Admissions" :value="context.counts.admissions" helper="Current admission windows" />
					<EdgeStatCard label="Programme Offerings" :value="context.counts.program_offerings" helper="Enabled branch offerings" />
				</EdgeDashboardLayout>

				<section class="eduedge-home-grid">
					<article v-for="module in modules" :key="module.route" class="eduedge-module-card">
						<div><p class="edge-eyebrow">{{ module.eyebrow }}</p><h2>{{ module.title }}</h2><p>{{ module.description }}</p></div>
						<button type="button" class="edge-button edge-button--primary" @click="openRoute(module.route)">{{ module.action }}</button>
					</article>
				</section>

				<section class="eduedge-readiness-panel">
					<div><p class="edge-eyebrow">Foundation readiness</p><h2>{{ context.readiness.ready ? "Ready for operations" : "Setup attention required" }}</h2></div>
					<div class="eduedge-readiness-badges">
						<EdgeStatusBadge :label="`${context.readiness.blocker_count} blockers`" :status="context.readiness.blocker_count ? 'blocked' : 'ready'" :tone="context.readiness.blocker_count ? 'danger' : 'success'" />
						<EdgeStatusBadge :label="`${context.readiness.warning_count} warnings`" :status="context.readiness.warning_count ? 'warning' : 'clear'" :tone="context.readiness.warning_count ? 'warning' : 'neutral'" />
					</div>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

export default {
	name: "EduEdgeHome",
	data() {
		return {
			loading: true,
			error: "",
			switchingBranch: false,
			selectedBranch: "",
			context: {
				user: {}, current_branch: null, allowed_branches: [], all_branch_options: [], requires_branch_selection: false,
				active_scope: "branch", active_label: "", can_switch_branch: true, can_manage_branch_access: false,
				branch_access_enforced: false,
				readiness: { ready: false, blocker_count: 0, warning_count: 0 },
				counts: { students: 0, applicants: 0, admissions: 0, program_offerings: 0, student_groups: 0, today_schedules: 0, assessment_plans: 0, pending_result_approvals: 0, pending_progression_reviews: 0 },
			},
			menuItems: EDUEDGE_MENU_ITEMS,
			modules: [
				{ eyebrow: "Daily operations", title: "Run classes and attendance", description: "View schedules and mark a branch-safe class register without leaving the EduEdge shell.", action: "Open academic operations", route: "/app/eduedge-academic-operations" },
				{ eyebrow: "Assessments and results", title: "Control assessment publication", description: "Review plans, confirm result completeness, approve results, and unlock report cards safely.", action: "Open assessments", route: "/app/eduedge-assessment-operations" },
				{ eyebrow: "Report cards", title: "Review comments and progression", description: "Prepare published report cards, record teacher and principal comments, and review promotion recommendations.", action: "Open report cards", route: "/app/eduedge-report-cards" },
				{ eyebrow: "Admission", title: "Manage admissions", description: "Publish branch admission windows and control valid programme choices.", action: "Open admissions", route: "/app/student-admission" },
				{ eyebrow: "Applicants", title: "Review applications", description: "Approve, reject, or enroll applicants within the selected campus.", action: "Open applicants", route: "/app/student-applicant" },
				{ eyebrow: "Academic setup", title: "Configure programme offerings", description: "Define which programmes each branch offers by academic year and term.", action: "Open offerings", route: "/app/eduedge-program-offering" },
			],
		};
	},
	computed: {
		scopeHelper() {
			return this.context.active_scope === "all" ? "Enabled students across authorised branches" : "Enabled students in this branch";
		},
		scopeDescription() {
			if (this.context.active_scope === "all") return `Aggregating authorised branches for ${this.context.active_company || "the selected company"}.`;
			return this.context.branch_access_enforced
				? "Branch access is enforced from active user assignments."
				: "Branch access enforcement is not enabled yet; review assignments before activation.";
		},
	},
	mounted() { this.loadContext(); },
	methods: {
		openRoute: openEduEdgeRoute,
		async loadContext() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.home.get_home_context");
				this.context = response.message || this.context;
				if (this.context.active_scope === "all") {
					this.selectedBranch = this.context.all_branch_options.find((option) => option.company === this.context.active_company)?.value || "";
				} else {
					this.selectedBranch = this.context.current_branch?.name || "";
				}
			} catch (error) {
				this.error = error?.message || "EduEdge home context could not be loaded.";
			} finally { this.loading = false; }
		},
		async switchBranch() {
			if (!this.selectedBranch) return;
			this.switchingBranch = true;
			try {
				let branch = this.selectedBranch;
				let company;
				if (branch.startsWith(`${this.context.all_branches_key}::`)) {
					company = branch.slice(`${this.context.all_branches_key}::`.length);
					branch = this.context.all_branches_key;
				}
				await frappe.call("eduedge.api.branch_context.switch_school_branch", { branch, company });
				await this.loadContext();
			} catch (error) {
				frappe.msgprint({ title: __("Unable to switch branch"), message: error?.message || __("The selected branch context could not be activated."), indicator: "red" });
			} finally { this.switchingBranch = false; }
		},
	},
};
</script>

<style scoped>
.eduedge-branch-select { min-width: min(25rem, 75vw); }
.eduedge-attention, .eduedge-context-status, .eduedge-readiness-panel { display: flex; align-items: center; justify-content: space-between; gap: var(--edge-space-4, 1rem); padding: var(--edge-space-4, 1rem); margin: var(--edge-space-4, 1rem) 0; border: 1px solid var(--border-color); border-radius: var(--edge-radius-lg, 12px); background: var(--card-bg); }
.eduedge-attention { align-items: flex-start; flex-direction: column; }
.eduedge-context-status > div:first-child { display: grid; gap: 0.25rem; }
.eduedge-context-status span, .eduedge-module-card p { color: var(--text-muted); }
.eduedge-home-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); gap: var(--edge-space-4, 1rem); margin-top: var(--edge-space-5, 1.25rem); }
.eduedge-module-card { display: flex; flex-direction: column; justify-content: space-between; gap: var(--edge-space-4, 1rem); min-height: 13rem; padding: var(--edge-space-5, 1.25rem); border: 1px solid var(--border-color); border-radius: var(--edge-radius-lg, 12px); background: var(--card-bg); }
.eduedge-module-card h2, .eduedge-readiness-panel h2 { margin: 0.25rem 0 0.5rem; }
.eduedge-readiness-badges { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; }
@media (max-width: 640px) { .eduedge-context-status, .eduedge-readiness-panel { align-items: flex-start; flex-direction: column; } }
</style>
