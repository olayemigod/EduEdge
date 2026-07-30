const EDUEDGE_PRODUCT_KEY = "eduedge";
const EDUEDGE_PRODUCT_MENU = Object.freeze({
	product_key: EDUEDGE_PRODUCT_KEY,
	product: "EduEdge",
	label: "EduEdge",
	icon: "graduation",
	home_route: "/app/eduedge-home",
	route_patterns: ["/app/eduedge*", "/app/query-report/EduEdge*"],
	order: 30,
	subtitle: "School operations and intelligence",
	menu_source: "eduedge",
	sections: [
		{
			label: "Overview",
			description: "Start from the school command centre",
			icon: "home",
			items: [
				{
					label: "EduEdge Home",
					description: "Branch context, readiness, and daily priorities",
					icon: "home",
					route: "/app/eduedge-home",
					keywords: ["dashboard", "school", "home"],
				},
				{
					label: "My Profile",
					description: "Your EduEdge identity and account profile",
					icon: "user",
					route: "/app/eduedge-my-profile",
					keywords: ["profile", "account", "identity"],
				},
			],
		},
		{
			label: "School Operations",
			description: "Admissions, students, classes, and attendance",
			icon: "graduation",
			items: [
				{
					label: "Academic Foundation",
					description: "Academic structure, levels, and calendars",
					icon: "book",
					route: "/app/eduedge-academic-foundation",
					keywords: ["academic", "foundation", "calendar", "level"],
				},
				{
					label: "Academic Operations",
					description: "Run classes, schedules, and attendance",
					icon: "book",
					route: "/app/eduedge-academic-operations",
					keywords: ["class", "schedule", "attendance"],
				},
				{
					label: "Admissions",
					description: "Configure and publish admission windows",
					icon: "clipboard",
					route: "/app/eduedge-admissions",
					keywords: ["admission", "session", "programme"],
				},
				{
					label: "Applicants",
					description: "Review prospective student applications",
					icon: "user",
					route: "/app/eduedge-applicants",
					keywords: ["applicant", "application", "enrolment"],
				},
				{
					label: "Students",
					description: "Student records, profiles, and branch context",
					icon: "students",
					route: "/app/eduedge-students",
					keywords: ["student", "learner", "profile"],
				},
			],
		},
		{
			label: "Academics and Outcomes",
			description: "Programmes, CBT, assessments, results, and progression",
			icon: "assessment",
			items: [
				{
					label: "Programmes",
					description: "Maintain the school programme catalogue",
					icon: "book",
					route: "/app/eduedge-programs",
					keywords: ["programme", "catalogue", "course"],
				},
				{
					label: "Programme Offerings",
					description: "Programmes available by campus and session",
					icon: "layers",
					route: "/app/eduedge-program-offerings",
					keywords: ["programme", "offering", "academic year"],
				},
				{
					label: "CBT Operations",
					description: "Centres, approved questions, templates, and readiness",
					icon: "assessment",
					route: "/app/eduedge-cbt-operations",
					keywords: ["cbt", "exam", "question bank", "template"],
				},
				{
					label: "CBT Schedules",
					description: "Schedules, candidates, check-in, release, and interventions",
					icon: "calendar",
					route: "/app/eduedge-cbt-schedules",
					keywords: ["cbt", "schedule", "candidate", "check in", "invigilator", "intervention"],
				},
				{
					label: "CBT Invigilation",
					description: "Monitor candidates, sync health, and result readiness",
					icon: "monitor",
					route: "/app/eduedge-cbt-invigilation",
					resource: "cbt_attempt",
					permissions: ["read", "report"],
					keywords: ["cbt", "invigilation", "candidate", "pending sync", "monitor"],
				},
				{
					label: "CBT Scoring & Marking",
					description: "Score objective responses, mark written answers, and approve results",
					icon: "edit",
					route: "/app/eduedge-cbt-marking",
					resource: "cbt_result",
					permissions: ["write"],
					keywords: ["cbt", "score", "marking", "result", "approval"],
				},
				{
					label: "CBT Attempt Review",
					description: "Resolve integrity flags before scoring",
					icon: "shield",
					route: "/app/eduedge-cbt-attempt-review",
					resource: "cbt_attempt_review",
					permissions: ["create"],
					keywords: ["cbt", "attempt", "review", "integrity", "disqualify"],
				},
				{
					label: "Exam Templates",
					description: "Review reusable approved examination designs",
					icon: "layers",
					route: "/app/eduedge-exam-templates",
					keywords: ["cbt", "exam", "template", "reuse"],
				},
				{
					label: "Exam Template Builder",
					description: "Create and govern reusable examination designs",
					icon: "edit",
					route: "/app/eduedge-exam-template-builder",
					keywords: ["cbt", "exam", "template", "builder"],
				},
				{
					label: "Question Bank",
					description: "Search and review governed CBT questions",
					icon: "book",
					route: "/app/eduedge-question-bank",
					keywords: ["cbt", "question", "bank", "review"],
				},
				{
					label: "Question Responsibilities",
					description: "Manage scoped authors, reviewers, and approvers",
					icon: "shield",
					route: "/app/eduedge-question-responsibilities",
					keywords: ["cbt", "question", "author", "reviewer", "approver"],
				},
				{
					label: "Question Builder",
					description: "Author and revise governed CBT questions",
					icon: "edit",
					route: "/app/eduedge-question-builder",
					keywords: ["cbt", "question", "author", "builder"],
				},
				{
					label: "Question Batch",
					description: "Create governed CBT questions in batches",
					icon: "layers",
					route: "/app/eduedge-question-batch",
					keywords: ["cbt", "question", "batch", "import"],
				},
				{
					label: "Assessments & Results",
					description: "Plan, review, approve, and publish results",
					icon: "assessment",
					route: "/app/eduedge-assessment-operations",
					keywords: ["exam", "assessment", "result", "publication"],
				},
				{
					label: "Report Cards",
					description: "Comments, progression, approval, and printing",
					icon: "report",
					route: "/app/eduedge-report-cards",
					keywords: ["report card", "progression", "promotion", "pdf"],
				},
			],
		},
		{
			label: "Administration",
			description: "Branch governance, access, accounting, and setup",
			icon: "settings",
			items: [
				{
					label: "Institution Profile",
					description: "Institution identity, branding, address, and contacts",
					icon: "building",
					route: "/app/eduedge-institution-profile",
					keywords: ["institution", "profile", "branding", "identity"],
				},
				{
					label: "Institution Structure",
					description: "Institution types and academic terminology",
					icon: "building",
					route: "/app/eduedge-institution-structure",
					keywords: ["institution", "structure", "terminology"],
				},
				{
					label: "Institution Operations Settings",
					description: "Company defaults and institution workflow preferences",
					icon: "settings",
					route: "/app/eduedge-institution-operations-settings",
					keywords: ["institution", "operations", "settings", "defaults"],
				},
				{
					label: "School Branches",
					description: "Campus identity and operational defaults",
					icon: "building",
					route: "/app/eduedge-school-branches",
					keywords: ["campus", "branch", "cost centre", "account"],
				},
				{
					label: "Branch Governance",
					description: "Campus access coverage and accounting readiness",
					icon: "shield",
					route: "/app/eduedge-branch-governance",
					keywords: ["branch", "campus", "access", "accounting"],
				},
				{
					label: "User Branch Access",
					description: "Maintain staff campus assignments inside Branch Governance",
					icon: "students",
					route: "/app/eduedge-branch-governance",
					resource: "user_branch_access",
					permissions: ["read", "write"],
					keywords: ["user", "role", "assignment", "hq"],
				},
				{
					label: "Setup Center",
					description: "Review foundation readiness and configuration",
					icon: "settings",
					route: "/app/eduedge-setup-center",
					keywords: ["setup", "readiness", "configuration"],
				},
				{
					label: "EduEdge Settings",
					description: "Defaults, controls, and optional features",
					icon: "settings",
					route: "/app/eduedge-settings-center",
					keywords: ["settings", "features", "defaults"],
				},
			],
		},
		{
			label: "Help & Training",
			description: "Role-based learning, practice, and readiness",
			icon: "book",
			items: [
				{
					label: "EduEdge Training Centre",
					description: "Step-by-step guides, flowcharts, videos, and progress",
					icon: "book",
					route: "/app/eduedge-training-centre",
					keywords: ["training", "guide", "help", "video", "onboarding"],
				},
			],
		},
	],
});

function normalizeRoute(route) {
	try {
		return new URL(route, window.location.origin).pathname.replace(/\/+$/, "") || "/";
	} catch (_error) {
		return String(route || "").split(/[?#]/, 1)[0].replace(/\/+$/, "");
	}
}

function itemAllowed(item) {
	if (frappe.session.user === "Administrator") return true;
	const manifest = frappe.boot?.eduedge_access_manifest;
	if (!manifest) return true;

	if (item.resource) {
		const resource = manifest.resources?.[item.resource] || {};
		return (item.permissions || ["read"]).some((permission) => Boolean(resource[permission]));
	}
	const route = normalizeRoute(item.route);
	if (!Object.prototype.hasOwnProperty.call(manifest.routes || {}, route)) return true;
	return Boolean(manifest.routes[route]);
}

function permissionFilteredMenu() {
	return {
		...EDUEDGE_PRODUCT_MENU,
		sections: EDUEDGE_PRODUCT_MENU.sections
			.map((section) => ({
				...section,
				items: section.items.filter(itemAllowed).map(({ resource, permissions, ...item }) => item),
			}))
			.filter((section) => section.items.length),
	};
}

function getProfile() {
	const bootUser = frappe.boot?.user || {};
	const userDefaults = bootUser.defaults || {};
	return {
		name: bootUser.full_name || frappe.session?.user || "EduEdge User",
		email: frappe.session?.user || "",
		company: userDefaults.company || frappe.defaults?.get_default?.("company") || "",
		branch:
			userDefaults.eduedge_school_branch ||
			frappe.defaults?.get_user_default?.("eduedge_school_branch") ||
			"",
	};
}

function registerEduEdgeProductMenu() {
	frappe.require("edgesuite_ui.bundle.js", () => {
		const runtime = window.EdgeSuiteUI || window.EdgeUI;
		if (!runtime?.registerProductMenu) return;
		runtime.registerProductMenu({
			...permissionFilteredMenu(),
			profile: getProfile(),
		});
		runtime.refreshProductMenu?.();
	});
}

if (document.readyState === "loading") {
	document.addEventListener("DOMContentLoaded", registerEduEdgeProductMenu, { once: true });
} else {
	registerEduEdgeProductMenu();
}

["desktop_screen", "sidebar_setup", "toolbar_setup", "page-change"].forEach((eventName) => {
	document.addEventListener(eventName, registerEduEdgeProductMenu);
});
