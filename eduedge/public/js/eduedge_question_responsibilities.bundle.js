import EduEdgeQuestionResponsibilities from "./eduedge_question_responsibilities/EduEdgeQuestionResponsibilities.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeQuestionResponsibilitiesApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeQuestionResponsibilities, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeQuestionResponsibilities = EduEdgeQuestionResponsibilities;
	window.createEduEdgeQuestionResponsibilitiesApp = createEduEdgeQuestionResponsibilitiesApp;
}

export default EduEdgeQuestionResponsibilities;
