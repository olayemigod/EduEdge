export const EDUEDGE_MENU_ITEMS = Object.freeze([
	{ section: __("Overview"), sectionIcon: "home", label: __("Home"), route: "/app/eduedge-home", icon: "home", description: __("School command centre") },
	{ section: __("School Operations"), sectionIcon: "graduation", label: __("Academic Operations"), route: "/app/eduedge-academic-operations", icon: "book", description: __("Classes, schedules, and attendance") },
	{ section: __("School Operations"), sectionIcon: "graduation", label: __("Admissions"), route: "/app/eduedge-admissions", icon: "clipboard", description: __("Admission windows and availability") },
	{ section: __("School Operations"), sectionIcon: "graduation", label: __("Applicants"), route: "/app/eduedge-applicants", icon: "user", description: __("Review prospective students") },
	{ section: __("School Operations"), sectionIcon: "graduation", label: __("Students"), route: "/app/eduedge-students", icon: "students", description: __("Student records and profiles") },
	{ section: __("Academics and Outcomes"), sectionIcon: "assessment", label: __("Programmes"), route: "/app/eduedge-programs", icon: "book", description: __("School programme catalogue") },
	{ section: __("Academics and Outcomes"), sectionIcon: "assessment", label: __("Programme Offerings"), route: "/app/eduedge-program-offerings", icon: "layers", description: __("Programmes by campus and session") },
	{ section: __("Academics and Outcomes"), sectionIcon: "assessment", label: __("Assessments & Results"), route: "/app/eduedge-assessment-operations", icon: "assessment", description: __("Plan, review, approve, and publish") },
	{ section: __("Academics and Outcomes"), sectionIcon: "assessment", label: __("Report Cards"), route: "/app/eduedge-report-cards", icon: "report", description: __("Comments, progression, and printing") },
	{ section: __("Administration"), sectionIcon: "settings", label: __("School Branches"), route: "/app/eduedge-school-branches", icon: "building", description: __("Campus identity and operational defaults") },
	{ section: __("Administration"), sectionIcon: "settings", label: __("Institution Structure"), route: "/app/eduedge-institution-structure", icon: "building", description: __("Institution types and academic terminology") },
	{ section: __("Administration"), sectionIcon: "settings", label: __("Branch Governance"), route: "/app/eduedge-branch-governance", icon: "shield", description: __("Campus access and accounting readiness") },
	{ section: __("Administration"), sectionIcon: "settings", label: __("Setup Center"), route: "/app/eduedge-setup-center", icon: "settings", description: __("Foundation readiness and configuration") },
	{ section: __("Administration"), sectionIcon: "settings", label: __("EduEdge Settings"), route: "/app/eduedge-settings-center", icon: "settings", description: __("Defaults, controls, and features") },
	{ section: __("Help & Training"), sectionIcon: "book", label: __("Training Centre"), route: "/app/eduedge-training-centre", icon: "book", description: __("Role-based guided learning") },
]);

export const EDUEDGE_UI_ROUTES = Object.freeze([
	"/app/eduedge-home",
	"/app/eduedge-academic-operations",
	"/app/eduedge-admissions",
	"/app/eduedge-applicants",
	"/app/eduedge-students",
	"/app/eduedge-programs",
	"/app/eduedge-program-offerings",
	"/app/eduedge-assessment-operations",
	"/app/eduedge-report-cards",
	"/app/eduedge-school-branches",
	"/app/eduedge-institution-structure",
	"/app/eduedge-branch-governance",
	"/app/eduedge-setup-center",
	"/app/eduedge-settings-center",
	"/app/eduedge-training-centre",
]);

function normalizedPath(route) {
	try {
		return new URL(route, window.location.origin).pathname.replace(/\/+$/, "") || "/";
	} catch (_error) {
		return String(route || "").split(/[?#]/, 1)[0].replace(/\/+$/, "");
	}
}

export function isEduEdgeUIRoute(route) {
	return EDUEDGE_UI_ROUTES.includes(normalizedPath(route));
}

export function openEduEdgeRoute(route) {
	if (!route) return;
	if (isEduEdgeUIRoute(route)) {
		window.location.href = route;
		return;
	}

	// Native Frappe forms and specialist workflows remain available only as
	// deliberate full-form fallbacks, preserving the current EduEdge workspace.
	const opened = window.open(route, "_blank", "noopener,noreferrer");
	if (opened) opened.opener = null;
}
