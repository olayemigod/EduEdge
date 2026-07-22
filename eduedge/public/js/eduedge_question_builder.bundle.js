import EduEdgeQuestionBuilder from "./eduedge_question_builder/EduEdgeQuestionBuilder.vue";
import { installQuestionRichTextEditor } from "./eduedge_question_builder/rich_text_editor";
import "./eduedge_question_builder/rich_text_editor.css";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

function resolveMountRoot(target) {
	if (target instanceof Element) return target;
	if (typeof target === "string") return document.querySelector(target);
	return null;
}

function installEditorObserver(root) {
	if (!root) return { destroy() {} };

	let editorController = null;
	let scheduled = false;
	let destroyed = false;

	const ensureEditor = () => {
		scheduled = false;
		if (destroyed || !root.isConnected) return;

		if (editorController) {
			const active = editorController.refresh();
			if (active) return;
			editorController.destroy();
			editorController = null;
		}

		editorController = installQuestionRichTextEditor(root);
	};

	const scheduleEnsure = () => {
		if (scheduled || destroyed) return;
		scheduled = true;
		window.requestAnimationFrame(ensureEditor);
	};

	const observer = new MutationObserver(scheduleEnsure);
	observer.observe(root, {
		childList: true,
		subtree: true,
		attributes: true,
		attributeFilter: ["class", "contenteditable"],
	});

	scheduleEnsure();

	return {
		destroy() {
			destroyed = true;
			observer.disconnect();
			editorController?.destroy();
			editorController = null;
		},
	};
}

export function createEduEdgeQuestionBuilderApp(rootProps = null) {
	const app = createEduEdgeApp(EduEdgeQuestionBuilder, rootProps);
	const originalMount = app.mount.bind(app);
	const originalUnmount = app.unmount.bind(app);
	let editorObserver = null;

	app.mount = (target, ...args) => {
		const mounted = originalMount(target, ...args);
		editorObserver?.destroy();
		editorObserver = installEditorObserver(resolveMountRoot(target));
		return mounted;
	};

	app.unmount = (...args) => {
		editorObserver?.destroy();
		editorObserver = null;
		return originalUnmount(...args);
	};

	return app;
}

if (typeof window !== "undefined") {
	window.EduEdgeQuestionBuilder = EduEdgeQuestionBuilder;
	window.createEduEdgeQuestionBuilderApp = createEduEdgeQuestionBuilderApp;
}

export default EduEdgeQuestionBuilder;
