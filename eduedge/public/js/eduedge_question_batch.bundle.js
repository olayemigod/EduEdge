import EduEdgeQuestionBatch from "./eduedge_question_batch/EduEdgeQuestionBatch.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeQuestionBatchApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeQuestionBatch, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeQuestionBatch = EduEdgeQuestionBatch;
	window.createEduEdgeQuestionBatchApp = createEduEdgeQuestionBatchApp;
}

export default EduEdgeQuestionBatch;
