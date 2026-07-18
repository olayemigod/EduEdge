export const EDUEDGE_MENU_ITEMS = Object.freeze([
	{
		section: __("Overview"),
		sectionIcon: "home",
		label: __("Home"),
		route: "/app/eduedge-home",
		icon: "home",
		description: __("School command centre"),
	},
	{
		section: __("School Operations"),
		sectionIcon: "graduation",
		label: __("Academic Operations"),
		route: "/app/eduedge-academic-operations",
		icon: "book",
		description: __("Classes, schedules, and attendance"),
	},
	{
		section: __("School Operations"),
		sectionIcon: "graduation",
		label: __("Admissions"),
		route: "/app/student-admission",
		icon: "clipboard",
		description: __("Admission windows and applications"),
	},
	{
		section: __("School Operations"),
		sectionIcon: "graduation",
		label: __("Applicants"),
		route: "/app/student-applicant",
		icon: "user",
		description: __("Review prospective students"),
	},
	{
		section: __("School Operations"),
		sectionIcon: "graduation",
		label: __("Students"),
		route: "/app/student",
		icon: "students",
		description: __("Student records and profiles"),
	},
	{
		section: __("Academics and Outcomes"),
		sectionIcon: "assessment",
		label: __("Program Offerings"),
		route: "/app/eduedge-program-offering",
		icon: "layers",
		description: __("Programmes by campus and session"),
	},
	{
		section: __("Academics and Outcomes"),
		sectionIcon: "assessment",
		label: __("Assessments & Results"),
		route: "/app/eduedge-assessment-operations",
		icon: "assessment",
		description: __("Plan, review, approve, and publish"),
	},
	{
		section: __("Academics and Outcomes"),
		sectionIcon: "assessment",
		label: __("Report Cards"),
		route: "/app/eduedge-report-cards",
		icon: "report",
		description: __("Comments, progression, and printing"),
	},
	{
		section: __("Administration"),
		sectionIcon: "settings",
		label: __("Branch Governance"),
		route: "/app/eduedge-branch-governance",
		icon: "shield",
		description: __("Campus access and accounting readiness"),
	},
	{
		section: __("Administration"),
		sectionIcon: "settings",
		label: __("Setup Center"),
		route: "/app/eduedge-setup-center",
		icon: "settings",
		description: __("Foundation readiness and configuration"),
	},
]);

export function openEduEdgeRoute(route) {
	if (route) {
		window.location.href = route;
	}
}
