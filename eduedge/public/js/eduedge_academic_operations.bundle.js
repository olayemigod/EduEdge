import EduEdgeAcademicOperations from "./eduedge_academic_operations/EduEdgeAcademicOperations.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeAcademicOperationsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeAcademicOperations, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeAcademicOperations = EduEdgeAcademicOperations;
	window.createEduEdgeAcademicOperationsApp = createEduEdgeAcademicOperationsApp;
}

export default EduEdgeAcademicOperations;
