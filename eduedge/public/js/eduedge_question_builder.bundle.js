import EduEdgeQuestionBuilder from "./eduedge_question_builder/EduEdgeQuestionBuilder.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeQuestionBuilderApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeQuestionBuilder, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeQuestionBuilder = EduEdgeQuestionBuilder;
	window.createEduEdgeQuestionBuilderApp = createEduEdgeQuestionBuilderApp;
}

export default EduEdgeQuestionBuilder;
