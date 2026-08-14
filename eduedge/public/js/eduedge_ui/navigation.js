import { reactive } from "vue";

const NAVIGATION_STATE_VERSION = "v1";
const FAVORITES_STATE_VERSION = "v1";
const COMPACT_STYLESHEET = "/assets/eduedge/css/eduedge_compact_navigation.css";
const EDUEDGE_ROUTE_ALIASES = Object.freeze({
	"/app/eduedge-instructor-branch-assignment": "/app/eduedge-instructor-assignments",
	"/app/eduedge-scheme-of-work": "/app/eduedge-schemes-of-work",
});

export const EDUEDGE_CRITICAL_CBT_ROUTES = Object.freeze([
	{ route: "/app/eduedge-cbt-schedules" },
	{ route: "/app/eduedge-cbt-invigilation" },
	{ route: "/app/eduedge-cbt-review-workbench" },
	{ route: "/app/eduedge-cbt-marking" },
]);

function term(key, { plural = false, fallback = "" } = {}) {
	return frappe.eduedge?.term?.(key, { plural, fallback }) || fallback;
}

function normalizedPath(route) {
	let value = String(route || "");
	if (value.startsWith("route:")) value = value.slice(6);
	try {
		return new URL(value, window.location.origin).pathname.replace(/\/+$/, "") || "/";
	} catch (_error) {
		return value.split(/[?#]/, 1)[0].replace(/\/+$/, "");
	}
}

function resolvedRoute(route) {
	const value = String(route || "");
	const alias = EDUEDGE_ROUTE_ALIASES[normalizedPath(value)];
	if (!alias) return value;
	const queryIndex = value.indexOf("?");
	return `${alias}${queryIndex >= 0 ? value.slice(queryIndex) : ""}`;
}

function preferenceKey(kind, version) {
	const user = frappe.session?.user || "Guest";
	return `edgeui:eduedge:${kind}:${version}:${user}`;
}

function readFavoriteRoutes() {
	try {
		const value = JSON.parse(localStorage.getItem(preferenceKey("favorites", FAVORITES_STATE_VERSION)) || "[]");
		return Array.isArray(value) ? value.map(normalizedPath).filter(Boolean) : [];
	} catch (_error) {
		return [];
	}
}

function ensureCompactNavigationStyles() {
	if (typeof document === "undefined" || document.querySelector(`link[href="${COMPACT_STYLESHEET}"]`)) return;
	const link = document.createElement("link");
	link.rel = "stylesheet";
	link.href = COMPACT_STYLESHEET;
	link.dataset.eduedgeCompactNavigation = "1";
	document.head.appendChild(link);
}

export function featureEnabled(feature) {
	if (!feature) return true;
	const features =
		frappe.boot?.eduedge_features ||
		frappe.boot?.eduedge_ui_identity?.features ||
		frappe.boot?.eduedge_access_manifest?.features;
	if (!features || !Object.prototype.hasOwnProperty.call(features, feature)) return true;
	return Boolean(features[feature]);
}

export function hasEduEdgeRouteAccess(route) {
	if (frappe.session.user === "Administrator") return true;
	const path = normalizedPath(resolvedRoute(route));
	const routes = frappe.boot?.eduedge_access_manifest?.routes;
	if (!routes || !Object.prototype.hasOwnProperty.call(routes, path)) return false;
	return Boolean(routes[path]);
}

function menuItem(label, route, icon, description) {
	return { label, route, icon, description };
}

function menuGroup(key, label, icon, items, { feature = "" } = {}) {
	if (!featureEnabled(feature)) return null;
	const allowedItems = items.filter((item) => hasEduEdgeRouteAccess(item.route));
	const activePath = typeof window === "undefined" ? "" : normalizedPath(window.location.pathname);
	return {
		key,
		label,
		icon,
		feature,
		defaultCollapsed: !allowedItems.some((item) => normalizedPath(item.route) === activePath),
		items: allowedItems,
	};
}

function withFavorites(groups) {
	const populated = groups.filter((group) => group?.items.length);
	const favoriteRoutes = new Set(readFavoriteRoutes());
	if (!favoriteRoutes.size) return populated;
	const favoriteItems = [];
	const seen = new Set();
	for (const group of populated) {
		for (const item of group.items) {
			const route = normalizedPath(item.route);
			if (!favoriteRoutes.has(route) || seen.has(route)) continue;
			favoriteItems.push(item);
			seen.add(route);
		}
	}
	if (!favoriteItems.length) return populated;
	const favoriteGroup = {
		key: "favorites",
		label: __("Favorites"),
		icon: "star",
		defaultCollapsed: false,
		items: favoriteItems,
	};
	const overviewIndex = populated.findIndex((group) => group.key === "overview");
	const insertAt = overviewIndex >= 0 ? overviewIndex + 1 : 0;
	return [...populated.slice(0, insertAt), favoriteGroup, ...populated.slice(insertAt)];
}

export function buildEduEdgeMenuItems() {
	const programmes = term("programme", { plural: true, fallback: __("Programmes") });
	const offerings = term("programme_offering", { plural: true, fallback: __("Programme Offerings") });
	const groups = term("student_group", { plural: true, fallback: __("Classes") });
	const sessions = term("class_session", { plural: true, fallback: __("Schedules") });
	const courses = term("course", { plural: true, fallback: __("Courses / Subjects") });
	const topics = term("topic", { plural: true, fallback: __("Topics") });
	const academicYear = term("academic_year", { fallback: __("Academic Year") });
	const academicYears = term("academic_year", { plural: true, fallback: __("Academic Years") });
	const academicTerms = term("academic_term", { plural: true, fallback: __("Academic Terms") });
	const sections = term("academic_section", { plural: true, fallback: __("Academic Sections") });
	const levels = term("academic_level", { plural: true, fallback: __("Academic Levels") });
	const assessments = term("assessment", { plural: true, fallback: __("Assessments") });
	const student = term("student", { fallback: __("Student") });
	const students = term("student", { plural: true, fallback: __("Students") });
	const applicants = term("student_applicant", { plural: true, fallback: __("Applicants") });

	return withFavorites([
		menuGroup("overview", __("Overview"), "home", [
			menuItem(__("Home"), "/app/eduedge-home", "home", __("Education command centre")),
			menuItem(__("My Profile"), "/app/eduedge-my-profile", "user", __("Your EduEdge identity and profile")),
		]),
		menuGroup("students-admissions", __("Students & Admissions"), "user", [
			menuItem(__("Admissions"), "/app/eduedge-admissions", "clipboard", __("Admission windows and availability")),
			menuItem(applicants, "/app/eduedge-applicants", "user", __(`Review prospective ${students.toLowerCase()}`)),
			menuItem(students, "/app/eduedge-students", "students", __(`${student} profiles, guardians, photographs, and academic context`)),
			menuItem(__("Student Enrollments"), "/app/eduedge-student-enrollments", "assignment", __("Enroll Students into active Programme Offerings")),
			menuItem(__("Instructors"), "/app/eduedge-instructors", "users", __("Instructor identity, qualification, specialisation, and eligibility")),
			menuItem(__("Instructor Assignments"), "/app/eduedge-instructor-assignments", "assignment", __("Assign Instructors to multiple Branches, Classes, Class Arms, and Subjects")),
		]),
		menuGroup("academic-setup", __("Academic Setup"), "book", [
			menuItem(__("Academic Operations"), "/app/eduedge-academic-operations", "calendar", __("Daily academic command centre, alerts, and shortcuts")),
			menuItem(__("Teaching Schedule"), "/app/eduedge-teaching-schedule", "calendar", __(`Day, week, upcoming ${sessions.toLowerCase()}, and room usage`)),
			menuItem(__("Attendance"), "/app/eduedge-attendance", "clipboard", __("Take attendance, review registers, and resolve missing registers")),
			menuItem(__("Academic Readiness"), "/app/eduedge-academic-readiness", "report", __("Management view of assignment coverage, Instructor identity, Scheme approval, curriculum delivery, and assessment planning activity")),
			menuItem(__("Academic Foundation"), "/app/eduedge-academic-foundation", "book", __(`${sections}, ${levels}, and Institution calendars`)),
			menuItem(`${academicYears} & ${academicTerms}`, "/app/eduedge-academic-sessions", "calendar", __(`Configure ${academicYears.toLowerCase()} and their ${academicTerms.toLowerCase()}`)),
			menuItem(programmes, "/app/eduedge-programs", "book", __(`${programmes} catalogue`)),
			menuItem(`${courses} & ${topics}`, "/app/eduedge-curriculum", "book", __(`Manage Institution curriculum, grading, and class-aware ${topics.toLowerCase()}`)),
			menuItem(__("Scheme of Work"), "/app/eduedge-schemes-of-work", "book", __("Plan, approve, version, and snapshot term curriculum delivery")),
			menuItem(__("Lesson Plans"), "/app/eduedge-lesson-plans", "book", __("Prepare, submit, review, and approve lessons from the approved Scheme of Work")),
			menuItem(offerings, "/app/eduedge-program-offerings", "layers", __(`${programmes} by campus and ${academicYear}`)),
		]),
		menuGroup("assessment-results", __("Assessments & Results"), "clipboard", [
			menuItem(__(`${assessments} & Results`), "/app/eduedge-assessment-operations", "assessment", __(`Plan, approve, and publish ${assessments.toLowerCase()}`)),
			menuItem(__("Report Cards"), "/app/eduedge-report-cards", "report", __("Comments, progression, and printing")),
		]),
		menuGroup("cbt-delivery", __("CBT Delivery"), "monitor", [
			menuItem(__("CBT Operations"), "/app/eduedge-cbt-operations", "assessment", __("Centres, templates, and readiness")),
			menuItem(__("CBT Schedules"), "/app/eduedge-cbt-schedules", "calendar", __("Schedules, candidates, and release")),
			menuItem(__("CBT Invigilation"), "/app/eduedge-cbt-invigilation", "monitor", __("Live candidates and sync health")),
			menuItem(__("CBT Attempt Review"), "/app/eduedge-cbt-review-workbench", "shield", __("Resolve integrity flags before scoring")),
			menuItem(__("CBT Scoring & Marking"), "/app/eduedge-cbt-marking", "edit", __("Scoring, marking, and approval")),
		], { feature: "cbt" }),
		menuGroup("cbt-content", __("CBT Content"), "book", [
			menuItem(__("Question Bank"), "/app/eduedge-question-bank", "book", __("Search and review governed questions")),
			menuItem(__("Question Builder"), "/app/eduedge-question-builder", "edit", __("Author and revise questions")),
			menuItem(__("Question Batch"), "/app/eduedge-question-batch", "layers", __("Create questions in batches")),
			menuItem(__("Question Responsibilities"), "/app/eduedge-question-responsibilities", "shield", __("Authors, reviewers, and approvers")),
			menuItem(__("Exam Templates"), "/app/eduedge-exam-templates", "layers", __("Review reusable exam designs")),
			menuItem(__("Exam Template Builder"), "/app/eduedge-exam-template-builder", "edit", __("Create reusable exam designs")),
		], { feature: "cbt" }),
		menuGroup("institution-access", __("Institution & Access"), "building", [
			menuItem(__("Institution Profile"), "/app/eduedge-institution-profile", "building", __("Identity, branding, and contacts")),
			menuItem(__("Institution Structure"), "/app/eduedge-institution-structure", "layers", __("Institution types and terminology")),
			menuItem(__("Institution Operations"), "/app/eduedge-institution-operations-settings", "settings", __("Workflow preferences and defaults")),
			menuItem(__("School Branches"), "/app/eduedge-school-branches", "building", __("Campus identity and defaults")),
			menuItem(__("Branch Governance"), "/app/eduedge-branch-governance", "shield", __("Campus access and accounting readiness")),
			menuItem(__("Setup Center"), "/app/eduedge-setup-center", "settings", __("Foundation readiness and configuration")),
			menuItem(__("EduEdge Settings"), "/app/eduedge-settings-center", "settings", __("Defaults, controls, and features")),
		]),
		menuGroup("help-training", __("Help & Training"), "book", [
			menuItem(__("Training Centre"), "/app/eduedge-training-centre", "book", __("Role-based guided learning")),
		]),
	]);
}

export const EDUEDGE_MENU_ITEMS = reactive([]);
export const EDUEDGE_SECTION_STATE_KEY = `edgeui:eduedge:sidebar-sections:${NAVIGATION_STATE_VERSION}`;

export function refreshEduEdgeMenuItems() {
	ensureCompactNavigationStyles();
	EDUEDGE_MENU_ITEMS.splice(0, EDUEDGE_MENU_ITEMS.length, ...buildEduEdgeMenuItems());
	return EDUEDGE_MENU_ITEMS;
}

refreshEduEdgeMenuItems();
window.addEventListener("eduedge:institution-context-changed", refreshEduEdgeMenuItems);
window.addEventListener("edgesuite:favorites-changed", refreshEduEdgeMenuItems);
window.addEventListener("popstate", refreshEduEdgeMenuItems);
document.addEventListener("page-change", refreshEduEdgeMenuItems);

export const EDUEDGE_UI_ROUTES = Object.freeze([
	"/app/eduedge-home", "/app/eduedge-my-profile", "/app/eduedge-academic-operations",
	"/app/eduedge-teaching-schedule", "/app/eduedge-attendance",
	"/app/eduedge-class-arms", "/app/eduedge-admissions", "/app/eduedge-applicants",
	"/app/eduedge-students", "/app/eduedge-student-enrollments", "/app/eduedge-instructors",
	"/app/eduedge-instructor-assignments", "/app/eduedge-programs", "/app/eduedge-curriculum",
	"/app/eduedge-schemes-of-work", "/app/eduedge-lesson-plans", "/app/eduedge-program-offerings", "/app/eduedge-academic-foundation", "/app/eduedge-academic-sessions", "/app/eduedge-academic-readiness",
	"/app/eduedge-cbt-operations", "/app/eduedge-cbt-schedules", "/app/eduedge-cbt-invigilation",
	"/app/eduedge-cbt-marking", "/app/eduedge-cbt-review-workbench", "/app/eduedge-exam-templates",
	"/app/eduedge-exam-template-builder", "/app/eduedge-question-bank", "/app/eduedge-question-responsibilities",
	"/app/eduedge-question-builder", "/app/eduedge-question-batch", "/app/eduedge-assessment-operations",
	"/app/eduedge-report-cards", "/app/eduedge-institution-profile", "/app/eduedge-school-branches",
	"/app/eduedge-institution-structure", "/app/eduedge-institution-operations-settings",
	"/app/eduedge-branch-governance", "/app/eduedge-setup-center", "/app/eduedge-settings-center",
	"/app/eduedge-training-centre",
]);

export function isEduEdgeUIRoute(route) {
	return EDUEDGE_UI_ROUTES.includes(normalizedPath(resolvedRoute(route)));
}

export function openEduEdgeRoute(route) {
	route = resolvedRoute(route);
	if (!route) return;
	if (isEduEdgeUIRoute(route)) {
		if (!hasEduEdgeRouteAccess(route)) {
			frappe.msgprint({
				title: __("Access not available"),
				message: __("Your current role permissions do not provide access to this EduEdge area."),
				indicator: "orange",
			});
			return;
		}
		window.location.href = route;
		return;
	}
	const opened = window.open(route, "_blank", "noopener,noreferrer");
	if (opened) opened.opener = null;
}
