import EduEdgeAssessmentOperations from "./eduedge_assessment_operations/EduEdgeAssessmentOperations.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeAssessmentOperationsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeAssessmentOperations, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeAssessmentOperations = EduEdgeAssessmentOperations;
	window.createEduEdgeAssessmentOperationsApp = createEduEdgeAssessmentOperationsApp;
}

export default EduEdgeAssessmentOperations;
