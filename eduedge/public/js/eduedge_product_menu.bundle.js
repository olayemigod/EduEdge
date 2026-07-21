const EDUEDGE_PRODUCT_MENU = Object.freeze({
	product: "EduEdge",
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
			],
		},
		{
			label: "School Operations",
			description: "Admissions, students, classes, and attendance",
			icon: "graduation",
			items: [
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
					description: "Centres, approved questions, and exam templates",
					icon: "assessment",
					route: "/app/eduedge-cbt-operations",
					keywords: ["cbt", "exam", "question bank", "invigilation", "template"],
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
	frappe.require("edgeui.bundle.js", () => {
		const runtime = window.EdgeSuiteUI || window.EdgeUI;
		if (!runtime?.registerProductMenu) return;
		runtime.registerProductMenu({
			...permissionFilteredMenu(),
			profile: getProfile(),
		});
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
