import EduEdgeQuestionBuilder from "./eduedge_question_builder/EduEdgeQuestionBuilder.vue";
import { installQuestionRichTextEditor } from "./eduedge_question_builder/rich_text_editor";
import "./eduedge_question_builder/rich_text_editor.css";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

function attachQuestionRichTextEditor(viewModel) {
	if (viewModel.$options?.name !== "EduEdgeQuestionBuilder") return;
	viewModel.$nextTick(() => {
		if (viewModel.__eduedgeQuestionRichTextEditor) {
			const active = viewModel.__eduedgeQuestionRichTextEditor.refresh();
			if (active) return;
			viewModel.__eduedgeQuestionRichTextEditor.destroy();
			viewModel.__eduedgeQuestionRichTextEditor = null;
		}
		viewModel.__eduedgeQuestionRichTextEditor = installQuestionRichTextEditor(viewModel.$el);
	});
}

export function createEduEdgeQuestionBuilderApp(rootProps = null) {
	const app = createEduEdgeApp(EduEdgeQuestionBuilder, rootProps);
	app.mixin({
		mounted() {
			attachQuestionRichTextEditor(this);
		},
		updated() {
			attachQuestionRichTextEditor(this);
		},
		beforeUnmount() {
			if (this.$options?.name !== "EduEdgeQuestionBuilder") return;
			this.__eduedgeQuestionRichTextEditor?.destroy();
			this.__eduedgeQuestionRichTextEditor = null;
		},
	});
	return app;
}

if (typeof window !== "undefined") {
	window.EduEdgeQuestionBuilder = EduEdgeQuestionBuilder;
	window.createEduEdgeQuestionBuilderApp = createEduEdgeQuestionBuilderApp;
}

export default EduEdgeQuestionBuilder;
