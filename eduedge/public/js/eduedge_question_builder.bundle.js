import EduEdgeQuestionBuilder from "./eduedge_question_builder/EduEdgeQuestionBuilder.vue";
import { installQuestionRichTextEditor } from "./eduedge_question_builder/rich_text_editor";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const originalMounted = EduEdgeQuestionBuilder.mounted;
const originalUpdated = EduEdgeQuestionBuilder.updated;
const originalBeforeUnmount = EduEdgeQuestionBuilder.beforeUnmount;

function ensureRichTextEditor(vm) {
	vm.$nextTick(() => {
		if (vm._eduedgeRichTextEditor?.refresh?.()) return;
		vm._eduedgeRichTextEditor?.destroy?.();
		vm._eduedgeRichTextEditor = installQuestionRichTextEditor(vm.$el);
	});
}

EduEdgeQuestionBuilder.mounted = function mountedWithRichTextEditor(...args) {
	const result = originalMounted?.apply(this, args);
	ensureRichTextEditor(this);
	return result;
};

EduEdgeQuestionBuilder.updated = function updatedWithRichTextEditor(...args) {
	const result = originalUpdated?.apply(this, args);
	ensureRichTextEditor(this);
	return result;
};

EduEdgeQuestionBuilder.beforeUnmount = function beforeUnmountWithRichTextEditor(...args) {
	this._eduedgeRichTextEditor?.destroy?.();
	this._eduedgeRichTextEditor = null;
	return originalBeforeUnmount?.apply(this, args);
};

export function createEduEdgeQuestionBuilderApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeQuestionBuilder, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeQuestionBuilder = EduEdgeQuestionBuilder;
	window.createEduEdgeQuestionBuilderApp = createEduEdgeQuestionBuilderApp;
}

export default EduEdgeQuestionBuilder;
