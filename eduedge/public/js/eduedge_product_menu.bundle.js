const EDUEDGE_PRODUCT_KEY = "eduedge";

function term(key, { plural = false, fallback = "" } = {}) {
	return frappe.eduedge?.term?.(key, { plural, fallback }) || fallback;
}

function item(label, description, icon, route, extra = {}) {
	return { label, description, icon, route, ...extra };
}

function featureEnabled(feature) {
	if (!feature) return true;
	const features =
		frappe.boot?.eduedge_features ||
		frappe.boot?.eduedge_ui_identity?.features ||
		frappe.boot?.eduedge_access_manifest?.features;
	if (!features || !Object.prototype.hasOwnProperty.call(features, feature)) return true;
	return Boolean(features[feature]);
}

function buildEduEdgeProductMenu() {
	const programme = term("programme", { fallback: __("Programme") });
	const programmes = term("programme", { plural: true, fallback: __("Programmes") });
	const offerings = term("programme_offering", { plural: true, fallback: __("Programme Offerings") });
	const student = term("student", { fallback: __("Student") });
	const students = term("student", { plural: true, fallback: __("Students") });
	const applicants = term("student_applicant", { plural: true, fallback: __("Applicants") });
	const groups = term("student_group", { plural: true, fallback: __("Classes") });
	const assessments = term("assessment", { plural: true, fallback: __("Assessments") });

	return {
		product_key: EDUEDGE_PRODUCT_KEY,
		product: "EduEdge",
		label: "EduEdge",
		icon: "graduation",
		home_route: "/app/eduedge-home",
		route_patterns: ["/app/eduedge*", "/app/query-report/EduEdge*"],
		order: 30,
		subtitle: "School operations and intelligence",
		menu_source: "eduedge",
		accordion: true,
		sections: [
			{
				key: "overview",
				label: "Overview",
				description: "School command centre and your profile",
				icon: "home",
				items: [
					item("EduEdge Home", "Branch context, readiness, and daily priorities", "home", "/app/eduedge-home", { keywords: ["dashboard", "school", "home"], quick_action: true }),
					item("My Profile", "Your EduEdge identity and account profile", "user", "/app/eduedge-my-profile", { keywords: ["profile", "account", "identity"] }),
				],
			},
			{
				key: "students-admissions",
				label: "Students & Admissions",
				description: `Admissions, applicants, and ${students.toLowerCase()}`,
				icon: "students",
				items: [
					item("Admissions", "Configure and publish admission windows", "clipboard", "/app/eduedge-admissions", { keywords: ["admission", "session", "programme"], quick_action: true }),
					item(applicants, `Review prospective ${students.toLowerCase()}`, "user", "/app/eduedge-applicants", { keywords: ["applicant", "application", "enrolment"] }),
					item(students, `${student} records, profiles, and branch context`, "students", "/app/eduedge-students", { keywords: ["student", "pupil", "learner", "profile"], quick_action: true }),
				],
			},
			{
				key: "academic-setup",
				label: "Academic Setup",
				description: `${programmes}, offerings, ${groups.toLowerCase()}, schedules, and attendance`,
				icon: "graduation",
				items: [
					item("Academic Foundation", "Academic structure, levels, and calendars", "book", "/app/eduedge-academic-foundation", { keywords: ["academic", "foundation", "calendar", "level"] }),
					item(programmes, `Maintain the ${programme.toLowerCase()} catalogue`, "book", "/app/eduedge-programs", { keywords: ["programme", "class", "catalogue", "course"] }),
					item(offerings, `${programmes} available by campus and session`, "layers", "/app/eduedge-program-offerings", { keywords: ["programme", "class", "offering", "academic year"] }),
					item("Academic Operations", `Run ${groups.toLowerCase()}, schedules, and attendance`, "calendar", "/app/eduedge-academic-operations", { keywords: ["class", "schedule", "attendance"], quick_action: true }),
				],
			},
			{
				key: "assessment-results",
				label: "Assessments & Results",
				description: `Plan, approve, publish, and report ${assessments.toLowerCase()}`,
				icon: "assessment",
				items: [
					item(`${assessments} & Results`, `Plan, review, approve, and publish ${assessments.toLowerCase()}`, "assessment", "/app/eduedge-assessment-operations", { keywords: ["exam", "assessment", "result", "publication"], quick_action: true }),
					item("Report Cards", "Comments, progression, approval, and printing", "report", "/app/eduedge-report-cards", { keywords: ["report card", "progression", "promotion", "pdf"] }),
				],
			},
			{
				key: "cbt-delivery",
				label: "CBT Delivery",
				description: "Schedules, candidates, invigilation, review, scoring, and marking",
				icon: "monitor",
				feature: "cbt",
				items: [
					item("CBT Operations", "Centres, approved questions, templates, and readiness", "assessment", "/app/eduedge-cbt-operations", { keywords: ["cbt", "exam", "readiness"], quick_action: true }),
					item("CBT Schedules", "Schedules, candidates, check-in, release, and interventions", "calendar", "/app/eduedge-cbt-schedules", { keywords: ["cbt", "schedule", "candidate", "check in", "invigilator", "intervention"] }),
					item("CBT Invigilation", "Monitor candidates, sync health, and result readiness", "monitor", "/app/eduedge-cbt-invigilation", { resource: "cbt_attempt", permissions: ["read", "report"], keywords: ["cbt", "invigilation", "candidate", "pending sync", "monitor"] }),
					item("CBT Attempt Review", "Resolve integrity flags before scoring", "shield", "/app/eduedge-cbt-review-workbench", { resource: "cbt_attempt_review", permissions: ["create"], keywords: ["cbt", "attempt", "review", "integrity", "disqualify"] }),
					item("CBT Scoring & Marking", "Score objective responses, mark written answers, and approve results", "edit", "/app/eduedge-cbt-marking", { resource: "cbt_result", permissions: ["write"], keywords: ["cbt", "score", "marking", "result", "approval"] }),
				],
			},
			{
				key: "cbt-content",
				label: "CBT Content",
				description: "Question governance and reusable examination designs",
				icon: "book",
				feature: "cbt",
				items: [
					item("Question Bank", "Search and review governed CBT questions", "book", "/app/eduedge-question-bank", { keywords: ["cbt", "question", "bank", "review"] }),
					item("Question Builder", "Author and revise governed CBT questions", "edit", "/app/eduedge-question-builder", { keywords: ["cbt", "question", "author", "builder"], quick_action: true }),
					item("Question Batch", "Create governed CBT questions in batches", "layers", "/app/eduedge-question-batch", { keywords: ["cbt", "question", "batch", "import"] }),
					item("Question Responsibilities", "Manage scoped authors, reviewers, and approvers", "shield", "/app/eduedge-question-responsibilities", { keywords: ["cbt", "question", "author", "reviewer", "approver"] }),
					item("Exam Templates", "Review reusable approved examination designs", "layers", "/app/eduedge-exam-templates", { keywords: ["cbt", "exam", "template", "reuse"] }),
					item("Exam Template Builder", "Create and govern reusable examination designs", "edit", "/app/eduedge-exam-template-builder", { keywords: ["cbt", "exam", "template", "builder"] }),
				],
			},
			{
				key: "institution-access",
				label: "Institution & Access",
				description: "Institution identity, branches, access, accounting, and setup",
				icon: "building",
				items: [
					item("Institution Profile", "Institution identity, branding, address, and contacts", "building", "/app/eduedge-institution-profile", { keywords: ["institution", "profile", "branding", "identity"] }),
					item("Institution Structure", "Institution types and academic terminology", "layers", "/app/eduedge-institution-structure", { keywords: ["institution", "structure", "terminology"] }),
					item("Institution Operations", "Company defaults and institution workflow preferences", "settings", "/app/eduedge-institution-operations-settings", { keywords: ["institution", "operations", "settings", "defaults"] }),
					item("School Branches", "Campus identity and operational defaults", "building", "/app/eduedge-school-branches", { keywords: ["campus", "branch", "cost centre", "account"], quick_action: true }),
					item("Branch Governance", "Campus access coverage and accounting readiness", "shield", "/app/eduedge-branch-governance", { keywords: ["branch", "campus", "access", "accounting"] }),
					item("User Branch Access", "Maintain staff campus assignments inside Branch Governance", "students", "/app/eduedge-branch-governance", { resource: "user_branch_access", permissions: ["read", "write"], keywords: ["user", "role", "assignment", "hq"] }),
					item("Setup Center", "Review foundation readiness and configuration", "settings", "/app/eduedge-setup-center", { keywords: ["setup", "readiness", "configuration"] }),
					item("EduEdge Settings", "Defaults, controls, and optional features", "settings", "/app/eduedge-settings-center", { keywords: ["settings", "features", "defaults"] }),
				],
			},
			{
				key: "help-training",
				label: "Help & Training",
				description: "Role-based learning, practice, and readiness",
				icon: "book",
				items: [
					item("EduEdge Training Centre", "Step-by-step guides, flowcharts, videos, and progress", "book", "/app/eduedge-training-centre", { keywords: ["training", "guide", "help", "video", "onboarding"] }),
				],
			},
		],
	};
}

function normalizeRoute(route) {
	try {
		return new URL(route, window.location.origin).pathname.replace(/\/+$/, "") || "/";
	} catch (_error) {
		return String(route || "").split(/[?#]/, 1)[0].replace(/\/+$/, "");
	}
}

function itemAllowed(menuItem) {
	if (frappe.session.user === "Administrator") return true;
	const manifest = frappe.boot?.eduedge_access_manifest;
	if (!manifest) return true;
	if (menuItem.resource) {
		const resource = manifest.resources?.[menuItem.resource] || {};
		return (menuItem.permissions || ["read"]).some((permission) => Boolean(resource[permission]));
	}
	const route = normalizeRoute(menuItem.route);
	if (!Object.prototype.hasOwnProperty.call(manifest.routes || {}, route)) return true;
	return Boolean(manifest.routes[route]);
}

function permissionFilteredMenu() {
	const source = buildEduEdgeProductMenu();
	return {
		...source,
		sections: source.sections
			.filter((section) => featureEnabled(section.feature))
			.map((section) => ({
				...section,
				items: section.items.filter(itemAllowed).map(({ resource, permissions, ...menuItem }) => menuItem),
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
		branch: userDefaults.eduedge_school_branch || frappe.defaults?.get_user_default?.("eduedge_school_branch") || "",
	};
}

function registerEduEdgeProductMenu() {
	frappe.require("edgesuite_ui.bundle.js", () => {
		const runtime = window.EdgeSuiteUI || window.EdgeUI;
		if (!runtime?.registerProductMenu) return;
		runtime.registerProductMenu({ ...permissionFilteredMenu(), profile: getProfile() });
		runtime.refreshProductMenu?.();
		scheduleVisibleFriendlyNames();
	});
}

function friendlyPairs() {
	const student = term("student", { fallback: "Student" });
	const students = term("student", { plural: true, fallback: "Students" });
	const applicants = term("student_applicant", { plural: true, fallback: "Applicants" });
	const group = term("student_group", { fallback: "Student Group" });
	const groups = term("student_group", { plural: true, fallback: "Student Groups" });
	const programme = term("programme", { fallback: "Programme" });
	const programmes = term("programme", { plural: true, fallback: "Programmes" });
	const offerings = term("programme_offering", { plural: true, fallback: "Programme Offerings" });
	const assessment = term("assessment", { fallback: "Assessment" });
	const assessments = term("assessment", { plural: true, fallback: "Assessments" });
	return [
		["Add School Branches", "Add School Branch"],
		["Add School Branche", "Add School Branch"],
		["School Branche", "School Branch"],
		["Student Groups / Classes", groups],
		["Student Groups", groups],
		["Student Group", group],
		["Student Applicants", applicants],
		["Applicants", applicants],
		["Students", students],
		["Student", student],
		["Program Offerings", offerings],
		["Programme Offerings", offerings],
		["Programs", programmes],
		["Programmes", programmes],
		["Program", programme],
		["Programme", programme],
		["Assessment Operations", `${assessment} Operations`],
		["Assessment Plans", `${assessment} Plans`],
		["Assessment Results", `${assessment} Results`],
		["Assessments & Results", `${assessments} & Results`],
	].filter(([from, to]) => from && to && from !== to).sort((left, right) => right[0].length - left[0].length);
}

function isEduEdgeSurface() {
	const path = normalizeRoute(window.location.pathname);
	return path === "/app/eduedge" || path.startsWith("/app/eduedge-") || path.startsWith("/desk/eduedge-");
}

function replaceValue(value, pairs) {
	let next = String(value || "");
	for (const [from, to] of pairs) next = next.split(from).join(to);
	return next;
}

function applyVisibleFriendlyNames(root = document.body) {
	if (!root || !isEduEdgeSurface()) return;
	const pairs = friendlyPairs();
	const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
		acceptNode(node) {
			const parent = node.parentElement;
			if (!parent || !node.nodeValue?.trim()) return NodeFilter.FILTER_REJECT;
			if (parent.closest("script, style, textarea, code, pre, [contenteditable='true']")) return NodeFilter.FILTER_REJECT;
			return NodeFilter.FILTER_ACCEPT;
		},
	});
	const nodes = [];
	while (walker.nextNode()) nodes.push(walker.currentNode);
	for (const node of nodes) {
		const next = replaceValue(node.nodeValue, pairs);
		if (next !== node.nodeValue) node.nodeValue = next;
	}
	for (const element of root.querySelectorAll?.("[placeholder], [title], [aria-label]") || []) {
		for (const attribute of ["placeholder", "title", "aria-label"]) {
			if (!element.hasAttribute(attribute)) continue;
			const current = element.getAttribute(attribute) || "";
			const next = replaceValue(current, pairs);
			if (next !== current) element.setAttribute(attribute, next);
		}
	}
}

let terminologyScheduled = false;
function scheduleVisibleFriendlyNames() {
	if (terminologyScheduled) return;
	terminologyScheduled = true;
	requestAnimationFrame(() => {
		terminologyScheduled = false;
		applyVisibleFriendlyNames();
	});
}

function initialiseEduEdgeMenu() {
	registerEduEdgeProductMenu();
	scheduleVisibleFriendlyNames();
	if (!window.__eduedgeFriendlyNameObserver && document.body) {
		window.__eduedgeFriendlyNameObserver = new MutationObserver(scheduleVisibleFriendlyNames);
		window.__eduedgeFriendlyNameObserver.observe(document.body, { childList: true, subtree: true });
	}
}

if (document.readyState === "loading") {
	document.addEventListener("DOMContentLoaded", initialiseEduEdgeMenu, { once: true });
} else {
	initialiseEduEdgeMenu();
}

["desktop_screen", "sidebar_setup", "toolbar_setup", "page-change"].forEach((eventName) => {
	document.addEventListener(eventName, initialiseEduEdgeMenu);
});
window.addEventListener("eduedge:institution-context-changed", initialiseEduEdgeMenu);
