import EduEdgeAcademicReadiness from "./eduedge_academic_readiness/EduEdgeAcademicReadiness.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeAcademicReadinessApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeAcademicReadiness, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeAcademicReadiness = EduEdgeAcademicReadiness;
	window.createEduEdgeAcademicReadinessApp = createEduEdgeAcademicReadinessApp;
}

export default EduEdgeAcademicReadiness;
