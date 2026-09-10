import EduEdgeQuestionBatch from "./eduedge_question_batch/EduEdgeQuestionBatch.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const originalAddQuestion = EduEdgeQuestionBatch.methods?.addQuestion;
const originalLoadContext = EduEdgeQuestionBatch.methods?.loadContext;

if (typeof originalAddQuestion === "function") {
	EduEdgeQuestionBatch.methods.addQuestion = function addQuestionNewestFirst(...args) {
		const before = this.questions.length;
		const result = originalAddQuestion.apply(this, args);
		if (this.questions.length > before) {
			const newest = this.questions.pop();
			this.questions.unshift(newest);
			this.$nextTick(() => {
				this.$el
					?.querySelector(".eduedge-question-card input.form-control")
					?.focus();
			});
		}
		return result;
	};
}

if (typeof originalLoadContext === "function") {
	EduEdgeQuestionBatch.methods.loadContext = async function loadPermissionAwareContext(...args) {
		const root = this.$el?.closest(".eduedge-question-batch-root");
		root?.setAttribute("data-can-upload", "0");
		const result = await originalLoadContext.apply(this, args);
		const canUpload = Boolean(this.context?.can_upload);
		root?.setAttribute("data-can-upload", canUpload ? "1" : "0");
		if (!canUpload && this.mode === "upload") {
			this.setMode("entry");
		}
		return result;
	};
}

export function createEduEdgeQuestionBatchApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeQuestionBatch, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeQuestionBatch = EduEdgeQuestionBatch;
	window.createEduEdgeQuestionBatchApp = createEduEdgeQuestionBatchApp;
}

export default EduEdgeQuestionBatch;
