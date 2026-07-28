import EduEdgeExamTemplateBuilder from "./eduedge_exam_template_builder/EduEdgeExamTemplateBuilder.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeExamTemplateBuilderApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeExamTemplateBuilder, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeExamTemplateBuilder = EduEdgeExamTemplateBuilder;
	window.createEduEdgeExamTemplateBuilderApp = createEduEdgeExamTemplateBuilderApp;
}

export default EduEdgeExamTemplateBuilder;
