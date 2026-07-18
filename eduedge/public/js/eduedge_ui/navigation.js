export const EDUEDGE_MENU_ITEMS = Object.freeze([
	{ label: __("Home"), route: "/app/eduedge-home", icon: "⌂" },
	{ label: __("Academic Operations"), route: "/app/eduedge-academic-operations", icon: "C" },
	{ label: __("Assessments & Results"), route: "/app/eduedge-assessment-operations", icon: "R" },
	{ label: __("Report Cards"), route: "/app/eduedge-report-cards", icon: "P" },
	{ label: __("Branch Governance"), route: "/app/eduedge-branch-governance", icon: "B" },
	{ label: __("Admissions"), route: "/app/student-admission", icon: "A" },
	{ label: __("Applicants"), route: "/app/student-applicant", icon: "P" },
	{ label: __("Students"), route: "/app/student", icon: "S" },
	{ label: __("Program Offerings"), route: "/app/eduedge-program-offering", icon: "O" },
	{ label: __("Setup Center"), route: "/app/eduedge-setup-center", icon: "⚙" },
]);

export function openEduEdgeRoute(route) {
	if (route) {
		window.location.href = route;
	}
}
