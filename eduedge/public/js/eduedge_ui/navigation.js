import { reactive } from "vue";

const NAVIGATION_STATE_VERSION = "v1";
const COMPACT_STYLESHEET = "/assets/eduedge/css/eduedge_compact_navigation.css";

function term(key, { plural = false, fallback = "" } = {}) {
	return frappe.eduedge?.term?.(key, { plural, fallback }) || fallback;
}

function normalizedPath(route) {
	try {
		return new URL(route, window.location.origin).pathname.replace(/\/+$/, "") || "/";
	} catch (_error) {
		return String(route || "").split(/[?#]/, 1)[0].replace(/\/+$/, "");
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

export function hasEduEdgeRouteAccess(route) {
	if (frappe.session.user === "Administrator") return true;
	const path = normalizedPath(route);
	const routes = frappe.boot?.eduedge_access_manifest?.routes;
	if (!routes || !Object.prototype.hasOwnProperty.call(routes, path)) return true;
	return Boolean(routes[path]);
}

function menuItem(label, route, icon, description) {
	return { label, route, icon, description };
}

function menuGroup(key, label, icon, items) {
	return {
		key,
		label,
		icon,
		defaultCollapsed: true,
		items: items.filter((item) => hasEduEdgeRouteAccess(item.route)),
	};
}

export function buildEduEdgeMenuItems() {
	const programmes = term("programme", { plural: true, fallback: __("Programmes") });
	const offerings = term("programme_offering", { plural: true, fallback: __("Programme Offerings") });
	const groups = term("student_group", { plural: true, fallback: __("Classes") });
	const sessions = term("class_session", { plural: true, fallback: __("Schedules") });
	const academicYear = term("academic_year", { fallback: __("Academic Year") });
	const sections = term("academic_section", { plural: true, fallback: __("Academic Sections") });
	const levels = term("academic_level", { plural: true, fallback: __("Academic Levels") });
	const assessments = term("assessment", { plural: true, fallback: __("Assessments") });
	const student = term("student", { fallback: __("Student") });
	const students = term("student", { plural: true, fallback: __("Students") });
	const applicants = term("student_applicant", { plural: true, fallback: __("Applicants") });

	return [
		menuGroup("overview", __("Overview"), "home", [
			menuItem(__("Home"), "/app/eduedge-home", "home", __("Education command centre")),
			menuItem(__("My Profile"), "/app/eduedge-my-profile", "user", __("Your EduEdge identity and profile")),
		]),
		menuGroup("students-admissions", __("Students & Admissions"), "students", [
			menuItem(__("Admissions"), "/app/eduedge-admissions", "clipboard", __("Admission windows and availability")),
			menuItem(applicants, "/app/eduedge-applicants", "user", __(`Review prospective ${students.toLowerCase()}`)),
			menuItem(students, "/app/eduedge-students", "students", __(`${student} records and profiles`)),
		]),
		menuGroup("academic-setup", __("Academic Setup"), "graduation", [
			menuItem(__("Academic Foundation"), "/app/eduedge-academic-foundation", "book", __(`${sections}, ${levels}, and calendars`)),
			menuItem(programmes, "/app/eduedge-programs", "book", __(`${programmes} catalogue`)),
			menuItem(offerings, "/app/eduedge-program-offerings", "layers", __(`${programmes} by campus and ${academicYear}`)),
			menuItem(__("Academic Operations"), "/app/eduedge-academic-operations", "calendar", __(`${groups}, ${sessions}, and attendance`)),
		]),
		menuGroup("assessment-results", __("Assessments & Results"), "assessment", [
			menuItem(__(`${assessments} & Results`), "/app/eduedge-assessment-operations", "assessment", __(`Plan, approve, and publish ${assessments.toLowerCase()}`)),
			menuItem(__("Report Cards"), "/app/eduedge-report-cards", "report", __("Comments, progression, and printing")),
		]),
		menuGroup("cbt-delivery", __("CBT Delivery"), "monitor", [
			menuItem(__("CBT Operations"), "/app/eduedge-cbt-operations", "assessment", __("Centres, templates, and readiness")),
			menuItem(__("CBT Schedules"), "/app/eduedge-cbt-schedules", "calendar", __("Schedules, candidates, and release")),
			menuItem(__("CBT Invigilation"), "/app/eduedge-cbt-invigilation", "monitor", __("Live candidates and sync health")),
			menuItem(__("CBT Attempt Review"), "/app/eduedge-cbt-review-workbench", "shield", __("Resolve integrity flags before scoring")),
			menuItem(__("CBT Scoring & Marking"), "/app/eduedge-cbt-marking", "edit", __("Scoring, marking, and approval")),
		]),
		menuGroup("cbt-content", __("CBT Content"), "book", [
			menuItem(__("Question Bank"), "/app/eduedge-question-bank", "book", __("Search and review governed questions")),
			menuItem(__("Question Builder"), "/app/eduedge-question-builder", "edit", __("Author and revise questions")),
			menuItem(__("Question Batch"), "/app/eduedge-question-batch", "layers", __("Create questions in batches")),
			menuItem(__("Question Responsibilities"), "/app/eduedge-question-responsibilities", "shield", __("Authors, reviewers, and approvers")),
			menuItem(__("Exam Templates"), "/app/eduedge-exam-templates", "layers", __("Review reusable exam designs")),
			menuItem(__("Exam Template Builder"), "/app/eduedge-exam-template-builder", "edit", __("Create reusable exam designs")),
		]),
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
	].filter((group) => group.items.length);
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

export const EDUEDGE_UI_ROUTES = Object.freeze([
	"/app/eduedge-home", "/app/eduedge-my-profile", "/app/eduedge-academic-operations",
	"/app/eduedge-admissions", "/app/eduedge-applicants", "/app/eduedge-students",
	"/app/eduedge-programs", "/app/eduedge-program-offerings", "/app/eduedge-academic-foundation",
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
	return EDUEDGE_UI_ROUTES.includes(normalizedPath(route));
}

export function openEduEdgeRoute(route) {
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
