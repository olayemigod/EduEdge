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

export function hasEduEdgeRouteAccess(route) {
	if (frappe.session.user === "Administrator") return true;
	const path = normalizedPath(route);
	const routes = frappe.boot?.eduedge_access_manifest?.routes;
	if (!routes || !Object.prototype.hasOwnProperty.call(routes, path)) return true;
	return Boolean(routes[path]);
}

export function buildEduEdgeMenuItems() {
	const programmePlural = term("programme", { plural: true, fallback: __("Programmes") });
	const offeringPlural = term("programme_offering", { plural: true, fallback: __("Programme Offerings") });
	const groupPlural = term("student_group", { plural: true, fallback: __("Classes") });
	const sessionPlural = term("class_session", { plural: true, fallback: __("Schedules") });
	const academicYear = term("academic_year", { fallback: __("Academic Year") });
	const sectionPlural = term("academic_section", { plural: true, fallback: __("Academic Sections") });
	const levelPlural = term("academic_level", { plural: true, fallback: __("Academic Levels") });
	const assessmentPlural = term("assessment", { plural: true, fallback: __("Assessments") });

	const items = [
		{ section: __("Overview"), sectionIcon: "home", label: __("Home"), route: "/app/eduedge-home", icon: "home", description: __("Education command centre") },
		{ section: __("Academic Operations"), sectionIcon: "graduation", label: __("Academic Operations"), route: "/app/eduedge-academic-operations", icon: "book", description: __(`${groupPlural}, ${sessionPlural}, and attendance`) },
		{ section: __("Academic Operations"), sectionIcon: "graduation", label: __("Admissions"), route: "/app/eduedge-admissions", icon: "clipboard", description: __("Admission windows and availability") },
		{ section: __("Academic Operations"), sectionIcon: "graduation", label: __("Applicants"), route: "/app/eduedge-applicants", icon: "user", description: __("Review prospective students") },
		{ section: __("Academic Operations"), sectionIcon: "graduation", label: __("Students"), route: "/app/eduedge-students", icon: "students", description: __("Student records and profiles") },
		{ section: __("Academics and Outcomes"), sectionIcon: "assessment", label: programmePlural, route: "/app/eduedge-programs", icon: "book", description: __(`${programmePlural} catalogue`) },
		{ section: __("Academics and Outcomes"), sectionIcon: "assessment", label: offeringPlural, route: "/app/eduedge-program-offerings", icon: "layers", description: __(`${programmePlural} by campus and ${academicYear}`) },
		{ section: __("Academics and Outcomes"), sectionIcon: "assessment", label: __("Academic Foundation"), route: "/app/eduedge-academic-foundation", icon: "book", description: __(`${sectionPlural}, ${levelPlural}, and calendars`) },
		{ section: __("Academics and Outcomes"), sectionIcon: "assessment", label: __("CBT Operations"), route: "/app/eduedge-cbt-operations", icon: "assessment", description: __("Centres, question governance, templates, and readiness") },
		{ section: __("Academics and Outcomes"), sectionIcon: "assessment", label: __("CBT Schedules"), route: "/app/eduedge-cbt-schedules", icon: "calendar", description: __("Schedules, candidates, check-in, release, and interventions") },
		{ section: __("Academics and Outcomes"), sectionIcon: "assessment", label: __("Exam Templates"), route: "/app/eduedge-exam-templates", icon: "layers", description: __("Reusable Universal, Institution, Branch, and Subject exam designs") },
		{ section: __("Academics and Outcomes"), sectionIcon: "assessment", label: __("Question Bank"), route: "/app/eduedge-question-bank", icon: "book", description: __("Search and review governed CBT questions") },
		{ section: __("Academics and Outcomes"), sectionIcon: "assessment", label: __("Question Responsibilities"), route: "/app/eduedge-question-responsibilities", icon: "shield", description: __("Scoped question authors, subject reviewers, and final approvers") },
		{ section: __("Academics and Outcomes"), sectionIcon: "assessment", label: __(`${assessmentPlural} & Results`), route: "/app/eduedge-assessment-operations", icon: "assessment", description: __(`Plan, review, approve, and publish ${assessmentPlural.toLowerCase()}`) },
		{ section: __("Academics and Outcomes"), sectionIcon: "assessment", label: __("Report Cards"), route: "/app/eduedge-report-cards", icon: "report", description: __("Comments, progression, and printing") },
		{ section: __("Administration"), sectionIcon: "settings", label: __("Institution Profile"), route: "/app/eduedge-institution-profile", icon: "building", description: __("Logo, address, contact, and report identity") },
		{ section: __("Administration"), sectionIcon: "settings", label: __("School Branches"), route: "/app/eduedge-school-branches", icon: "building", description: __("Campus identity and operational defaults") },
		{ section: __("Administration"), sectionIcon: "settings", label: __("Institution Structure"), route: "/app/eduedge-institution-structure", icon: "building", description: __("Institution types and academic terminology") },
		{ section: __("Administration"), sectionIcon: "settings", label: __("Institution Operations"), route: "/app/eduedge-institution-operations-settings", icon: "settings", description: __("Company defaults and Institution workflow preferences") },
		{ section: __("Administration"), sectionIcon: "settings", label: __("Branch Governance"), route: "/app/eduedge-branch-governance", icon: "shield", description: __("Campus access and accounting readiness") },
		{ section: __("Administration"), sectionIcon: "settings", label: __("Setup Center"), route: "/app/eduedge-setup-center", icon: "settings", description: __("Foundation readiness and configuration") },
		{ section: __("Administration"), sectionIcon: "settings", label: __("EduEdge Settings"), route: "/app/eduedge-settings-center", icon: "settings", description: __("Defaults, controls, and features") },
		{ section: __("Help & Training"), sectionIcon: "book", label: __("Training Centre"), route: "/app/eduedge-training-centre", icon: "book", description: __("Role-based guided learning") },
	];

	return Object.freeze(items.filter((item) => hasEduEdgeRouteAccess(item.route)));
}

export const EDUEDGE_MENU_ITEMS = buildEduEdgeMenuItems();

export const EDUEDGE_UI_ROUTES = Object.freeze([
	"/app/eduedge-home",
	"/app/eduedge-my-profile",
	"/app/eduedge-academic-operations",
	"/app/eduedge-admissions",
	"/app/eduedge-applicants",
	"/app/eduedge-students",
	"/app/eduedge-programs",
	"/app/eduedge-program-offerings",
	"/app/eduedge-academic-foundation",
	"/app/eduedge-cbt-operations",
	"/app/eduedge-cbt-schedules",
	"/app/eduedge-exam-templates",
	"/app/eduedge-exam-template-builder",
	"/app/eduedge-question-bank",
	"/app/eduedge-question-responsibilities",
	"/app/eduedge-question-builder",
	"/app/eduedge-question-batch",
	"/app/eduedge-assessment-operations",
	"/app/eduedge-report-cards",
	"/app/eduedge-institution-profile",
	"/app/eduedge-school-branches",
	"/app/eduedge-institution-structure",
	"/app/eduedge-institution-operations-settings",
	"/app/eduedge-branch-governance",
	"/app/eduedge-setup-center",
	"/app/eduedge-settings-center",
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
