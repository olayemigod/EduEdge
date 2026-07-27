import EduEdgeQuestionBank from "./eduedge_question_bank/EduEdgeQuestionBank.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeQuestionBankApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeQuestionBank, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeQuestionBank = EduEdgeQuestionBank;
	window.createEduEdgeQuestionBankApp = createEduEdgeQuestionBankApp;
}

export default EduEdgeQuestionBank;
