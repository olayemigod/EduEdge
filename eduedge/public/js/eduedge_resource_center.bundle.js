import EduEdgeResourceCenter from "./eduedge_resource_center/EduEdgeResourceCenter.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const FULL_FORM_ROUTES = Object.freeze({
	school_branches: "/app/eduedge-school-branch",
	admissions: "/app/student-admission",
	applicants: "/app/student-applicant",
	students: "/app/student",
	programs: "/app/program",
	program_offerings: "/app/eduedge-program-offering",
});

EduEdgeResourceCenter.methods.openFullForm = function openFullForm(row) {
	const base = FULL_FORM_ROUTES[this.resourceKey] || "";
	if (!base || !row?.name) return;
	window.open(`${base}/${encodeURIComponent(row.name)}`, "_blank", "noopener,noreferrer");
};

window.EduEdgeResourceCenter = EduEdgeResourceCenter;
window.createEduEdgeResourceCenterApp = function createEduEdgeResourceCenterApp(props = {}) {
	return createEduEdgeApp(EduEdgeResourceCenter, props);
};
