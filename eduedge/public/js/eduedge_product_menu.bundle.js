const ADMIN_ROLES = ["System Manager", "EduEdge Administrator"];
const SETUP_ROLES = [...ADMIN_ROLES, "School Administrator"];
const GOVERNANCE_VIEW_ROLES = [...SETUP_ROLES, "Bursar"];

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
					link_type: "DocType",
					link_to: "Student Admission",
					keywords: ["admission", "session", "programme"],
				},
				{
					label: "Applicants",
					description: "Review prospective student applications",
					icon: "user",
					link_type: "DocType",
					link_to: "Student Applicant",
					keywords: ["applicant", "application", "enrolment"],
				},
				{
					label: "Students",
					description: "Student records, profiles, and branch context",
					icon: "students",
					link_type: "DocType",
					link_to: "Student",
					keywords: ["student", "learner", "profile"],
				},
			],
		},
		{
			label: "Academics and Outcomes",
			description: "Programmes, assessments, results, and progression",
			icon: "assessment",
			items: [
				{
					label: "Program Offerings",
					description: "Programmes available by campus and session",
					icon: "layers",
					link_type: "DocType",
					link_to: "EduEdge Program Offering",
					keywords: ["programme", "offering", "academic year"],
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
					label: "Branch Governance",
					description: "Campus access coverage and accounting readiness",
					icon: "shield",
					route: "/app/eduedge-branch-governance",
					roles: GOVERNANCE_VIEW_ROLES,
					keywords: ["branch", "campus", "access", "accounting"],
				},
				{
					label: "School Branches",
					description: "Campus identity and accounting defaults",
					icon: "building",
					link_type: "DocType",
					link_to: "EduEdge School Branch",
					roles: GOVERNANCE_VIEW_ROLES,
					keywords: ["campus", "branch", "cost centre", "account"],
				},
				{
					label: "User Branch Access",
					description: "Maintain staff campus assignments",
					icon: "students",
					link_type: "DocType",
					link_to: "EduEdge User Branch Access",
					roles: ADMIN_ROLES,
					keywords: ["user", "role", "assignment", "hq"],
				},
				{
					label: "Setup Center",
					description: "Review foundation readiness and configuration",
					icon: "settings",
					route: "/app/eduedge-setup-center",
					roles: SETUP_ROLES,
					keywords: ["setup", "readiness", "configuration"],
				},
			],
		},
	],
});

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
			...EDUEDGE_PRODUCT_MENU,
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
