import EduEdgeAcademicOperations from "./eduedge_academic_operations/EduEdgeAcademicOperations.vue";
import { installAcademicOperationsScheduleAction } from "./eduedge_academic_operations/schedule_action";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

installAcademicOperationsScheduleAction(EduEdgeAcademicOperations);

export function createEduEdgeAcademicOperationsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeAcademicOperations, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeAcademicOperations = EduEdgeAcademicOperations;
	window.createEduEdgeAcademicOperationsApp = createEduEdgeAcademicOperationsApp;
}

export default EduEdgeAcademicOperations;
