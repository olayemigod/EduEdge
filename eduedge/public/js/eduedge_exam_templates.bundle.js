import EduEdgeExamTemplates from "./eduedge_exam_templates/EduEdgeExamTemplates.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeExamTemplatesApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeExamTemplates, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeExamTemplates = EduEdgeExamTemplates;
	window.createEduEdgeExamTemplatesApp = createEduEdgeExamTemplatesApp;
}

export default EduEdgeExamTemplates;
