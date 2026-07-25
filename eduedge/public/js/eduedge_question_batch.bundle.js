import EduEdgeQuestionBatch from "./eduedge_question_batch/EduEdgeQuestionBatch.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const baseMethods = EduEdgeQuestionBatch.methods || {};
const NewestFirstQuestionBatch = {
	name: "EduEdgeQuestionBatch",
	extends: EduEdgeQuestionBatch,
	methods: {
		addQuestion(...args) {
			if (this.questions.length >= this.context.limits.manual_questions) return;
			const before = this.questions.length;
			const result = baseMethods.addQuestion.apply(this, args);
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
		},
	},
};

export function createEduEdgeQuestionBatchApp(rootProps = null) {
	return createEduEdgeApp(NewestFirstQuestionBatch, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeQuestionBatch = NewestFirstQuestionBatch;
	window.createEduEdgeQuestionBatchApp = createEduEdgeQuestionBatchApp;
}

export default NewestFirstQuestionBatch;
