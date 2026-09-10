<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="context.institution_context?.institution_name || context.tenant_name || ''"
		:branch-name="context.institution_context?.branch_name || context.active_label || ''"
		:user-name="context.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-home"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Education Management"
					title="Academic Operations"
					subtitle="Admissions, students, teaching groups, assessments, results, and active institution context in one place."
					action-label="Open Academic Operations"
					@action="openRoute('/app/eduedge-academic-operations')"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading EduEdge..." :skeleton="true" />
			<EdgeErrorState v-else-if="error" title="EduEdge could not load" :message="error" action-label="Try again" @retry="loadContext" />
			<template v-else>
				<EdgeActionBar label="Working institution and branch">
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

				<section class="eduedge-active-pair" aria-label="Current EduEdge context">
					<div>
						<span>Institution</span>
						<strong>{{ context.institution_context?.institution_name || "Not selected" }}</strong>
						<small>{{ context.institution_context?.institution_type_name || "Institution type not resolved" }}</small>
					</div>
					<div>
						<span>Branch / Campus</span>
						<strong>{{ context.institution_context?.branch_name || (context.active_scope === 'all' ? 'All authorised branches' : 'Not selected') }}</strong>
						<small>{{ context.active_company || "Company not resolved" }}</small>
					</div>
				</section>

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
						<button v-if="context.can_manage_branch_access" type="button" class="edge-button" @click="openRoute('/app/eduedge-branch-governance')">
							Open branch governance
						</button>
					</div>
				</section>

				<EdgeDashboardLayout min-column-width="12rem">
					<EdgeStatCard label="Students" :value="context.counts.students" :helper="scopeHelper" />
					<EdgeStatCard label="Active Applicants" :value="context.counts.applicants" helper="Applied or approved" />
					<EdgeStatCard :label="term('student_group', true, 'Classes')" :value="context.counts.student_groups" :helper="`Active ${term('student_group', true, 'student groups')}`" />
					<EdgeStatCard :label="`Today's ${term('class_session', true, 'Schedules')}`" :value="context.counts.today_schedules" :helper="`${term('class_session', true, 'Sessions')} scheduled today`" />
					<EdgeStatCard label="Assessment Plans" :value="context.counts.assessment_plans" helper="Active assessment plans" />
					<EdgeStatCard label="Pending Result Approvals" :value="context.counts.pending_result_approvals" helper="Awaiting authorized review" />
					<EdgeStatCard label="Progression Reviews" :value="context.counts.pending_progression_reviews" helper="Recommended and awaiting approval" />
					<EdgeStatCard label="Published Admissions" :value="context.counts.admissions" helper="Current admission windows" />
					<EdgeStatCard :label="term('programme_offering', true, 'Programme Offerings')" :value="context.counts.program_offerings" helper="Enabled branch offerings" />
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
				user: {}, current_institution: {}, current_branch: null, institution_context: {}, allowed_branches: [], all_branch_options: [], requires_branch_selection: false,
				active_scope: "branch", active_label: "", can_switch_branch: true, can_manage_branch_access: false,
				branch_access_enforced: false,
				readiness: { ready: false, blocker_count: 0, warning_count: 0 },
				counts: { students: 0, applicants: 0, admissions: 0, program_offerings: 0, student_groups: 0, today_schedules: 0, assessment_plans: 0, pending_result_approvals: 0, pending_progression_reviews: 0 },
			},
			menuItems: EDUEDGE_MENU_ITEMS,
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
		modules() {
			const offeringPlural = this.term("programme_offering", true, "Programme Offerings");
			return [
				{ eyebrow: "Guided learning", title: "Train every EduEdge role", description: "Follow role-based steps, flowcharts, practice exercises, and future embedded videos for students, teachers, administrators, owners, and ProcessEdge support staff.", action: "Open Training Centre", route: "/app/eduedge-training-centre" },
				{ eyebrow: "Daily operations", title: `Run ${this.term("class_session", true, "classes")} and attendance`, description: "View schedules and mark a branch-safe class register without leaving the EduEdge shell.", action: "Open academic operations", route: "/app/eduedge-academic-operations" },
				{ eyebrow: "Assessments and results", title: "Control assessment publication", description: "Review plans, confirm result completeness, approve results, and unlock report cards safely.", action: "Open assessments", route: "/app/eduedge-assessment-operations" },
				{ eyebrow: "Report cards", title: "Review comments and progression", description: "Prepare published report cards, record teacher and principal comments, and review promotion recommendations.", action: "Open report cards", route: "/app/eduedge-report-cards" },
				{ eyebrow: "Branch foundation", title: "Govern access and accounting", description: "Assign campus access, verify coverage, complete branch accounting defaults, and activate enforcement safely.", action: "Open branch governance", route: "/app/eduedge-branch-governance" },
				{ eyebrow: "Admission", title: "Manage admissions", description: `Publish branch admission windows and control valid ${this.term("programme", true, "programme")} choices.`, action: "Open admissions", route: "/app/eduedge-admissions" },
				{ eyebrow: "Applicants", title: "Review applications", description: "Approve, reject, or enroll applicants within the selected campus.", action: "Open applicants", route: "/app/eduedge-applicants" },
				{ eyebrow: "Academic setup", title: `Configure ${offeringPlural}`, description: `Define which ${this.term("programme", true, "programmes")} each branch offers by ${this.term("academic_year", false, "academic year")} and ${this.term("academic_term", false, "term")}.`, action: `Open ${offeringPlural}`, route: "/app/eduedge-program-offerings" },
			];
		},
	},
	mounted() { this.loadContext(); },
	methods: {
		openRoute: openEduEdgeRoute,
		term(key, plural = false, fallback = "") {
			return frappe.eduedge?.term?.(key, { plural, context: this.context.institution_context, fallback }) || fallback;
		},
		async loadContext() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.home.get_home_context");
				this.context = response.message || this.context;
				if (this.context.institution_context && frappe.eduedge?.applyInstitutionContext) {
					frappe.eduedge.applyInstitutionContext(this.context.institution_context);
				}
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
.eduedge-active-pair { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:var(--edge-space-4,1rem); margin:var(--edge-space-4,1rem) 0; }
.eduedge-active-pair > div { display:grid; gap:.2rem; padding:var(--edge-space-4,1rem); border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.eduedge-active-pair span { color:var(--text-muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.04em; }
.eduedge-active-pair small { color:var(--text-muted); }
.eduedge-attention, .eduedge-context-status, .eduedge-readiness-panel { display: flex; align-items: center; justify-content: space-between; gap: var(--edge-space-4, 1rem); padding: var(--edge-space-4, 1rem); margin: var(--edge-space-4, 1rem) 0; border: 1px solid var(--border-color); border-radius: var(--edge-radius-lg, 12px); background: var(--card-bg); }
.eduedge-attention { align-items: flex-start; flex-direction: column; }
.eduedge-context-status > div:first-child { display: grid; gap: 0.25rem; }
.eduedge-context-status span, .eduedge-module-card p { color: var(--text-muted); }
.eduedge-home-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); gap: var(--edge-space-4, 1rem); margin-top: var(--edge-space-5, 1.25rem); }
.eduedge-module-card { display: flex; flex-direction: column; justify-content: space-between; gap: var(--edge-space-4, 1rem); min-height: 13rem; padding: var(--edge-space-5, 1.25rem); border: 1px solid var(--border-color); border-radius: var(--edge-radius-lg, 12px); background: var(--card-bg); }
.eduedge-module-card h2, .eduedge-readiness-panel h2 { margin: 0.25rem 0 0.5rem; }
.eduedge-readiness-badges { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; }
@media (max-width: 640px) { .eduedge-active-pair { grid-template-columns:1fr; } .eduedge-context-status, .eduedge-readiness-panel { align-items: flex-start; flex-direction: column; } }
</style>
