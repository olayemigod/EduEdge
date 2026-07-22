import EduEdgeQuestionBuilder from "./eduedge_question_builder/EduEdgeQuestionBuilder.vue";
import "./eduedge_question_builder/rich_text_editor.css";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const FORMAT_COMMANDS = [
	{ label: "B", title: "Bold", command: "bold", className: "is-bold" },
	{ label: "I", title: "Italic", command: "italic", className: "is-italic" },
	{ label: "U", title: "Underline", command: "underline", className: "is-underline" },
	{ label: "x²", title: "Superscript selected text", command: "superscript" },
	{ label: "x₂", title: "Subscript selected text", command: "subscript" },
	{ label: "• List", title: "Bulleted list", command: "insertUnorderedList" },
	{ label: "1. List", title: "Numbered list", command: "insertOrderedList" },
	{ label: "Clear", title: "Remove formatting", command: "removeFormat" },
];

const QUICK_SYMBOLS = ["²", "³", "₀", "₁", "₂", "₃", "√", "π", "θ", "Δ", "∑", "∞", "×", "÷", "±", "≤", "≥", "≠", "°"];

function resolveMountRoot(target) {
	if (target instanceof Element) return target;
	if (typeof target === "string") return document.querySelector(target);
	return null;
}

function makeToolbarButton(label, title, onClick, className = "") {
	const button = document.createElement("button");
	button.type = "button";
	button.className = `eduedge-rich-editor__button ${className}`.trim();
	button.textContent = label;
	button.title = title;
	button.setAttribute("aria-label", title);
	button.addEventListener("mousedown", (event) => event.preventDefault());
	button.addEventListener("click", (event) => {
		event.preventDefault();
		onClick();
	});
	return button;
}

function placeCaretAtEnd(editor) {
	const selection = window.getSelection();
	if (!selection) return;
	const range = document.createRange();
	range.selectNodeContents(editor);
	range.collapse(false);
	selection.removeAllRanges();
	selection.addRange(range);
}

function installNativeQuestionToolbar(root) {
	if (!root) return { destroy() {} };

	let scheduled = false;
	let destroyed = false;
	let activeTextTarget = null;
	let toolbar = null;
	let help = null;
	let editor = null;

	const syncEditor = () => {
		if (!editor) return;
		editor.dispatchEvent(new Event("input", { bubbles: true }));
	};

	const editorIsReadOnly = () => !editor || editor.getAttribute("contenteditable") === "false" || editor.classList.contains("is-read-only");

	const ensureEditorSelection = () => {
		if (!editor) return;
		editor.focus();
		const selection = window.getSelection();
		if (!editor.contains(selection?.anchorNode)) placeCaretAtEnd(editor);
	};

	const runCommand = (command) => {
		if (editorIsReadOnly()) return;
		activeTextTarget = editor;
		ensureEditorSelection();
		document.execCommand(command, false, null);
		syncEditor();
	};

	const insertSymbol = (value) => {
		if (editorIsReadOnly()) return;
		if (activeTextTarget instanceof HTMLInputElement || activeTextTarget instanceof HTMLTextAreaElement) {
			const start = Number.isInteger(activeTextTarget.selectionStart) ? activeTextTarget.selectionStart : activeTextTarget.value.length;
			const end = Number.isInteger(activeTextTarget.selectionEnd) ? activeTextTarget.selectionEnd : start;
			activeTextTarget.setRangeText(value, start, end, "end");
			activeTextTarget.dispatchEvent(new Event("input", { bubbles: true }));
			activeTextTarget.focus();
			return;
		}
		activeTextTarget = editor;
		ensureEditorSelection();
		document.execCommand("insertText", false, value);
		syncEditor();
	};

	const buildToolbar = () => {
		toolbar = document.createElement("div");
		toolbar.className = "eduedge-rich-editor__toolbar eduedge-native-question-toolbar";
		toolbar.setAttribute("role", "toolbar");
		toolbar.setAttribute("aria-label", "Question formatting");

		FORMAT_COMMANDS.forEach((item) => {
			toolbar.appendChild(makeToolbarButton(item.label, item.title, () => runCommand(item.command), item.className));
		});

		const symbolLabel = document.createElement("span");
		symbolLabel.className = "eduedge-rich-editor__symbols-label";
		symbolLabel.textContent = "Symbols";
		toolbar.appendChild(symbolLabel);

		const symbols = document.createElement("div");
		symbols.className = "eduedge-rich-editor__symbols";
		QUICK_SYMBOLS.forEach((symbol) => {
			symbols.appendChild(makeToolbarButton(symbol, `Insert ${symbol}`, () => insertSymbol(symbol), "is-symbol"));
		});
		toolbar.appendChild(symbols);

		help = document.createElement("p");
		help.className = "eduedge-rich-editor__help eduedge-native-question-help";
		help.textContent = "Select text before using superscript or subscript. Symbols can also be inserted into the last focused answer field.";
	};

	const applyReadOnlyState = () => {
		if (!toolbar) return;
		const disabled = editorIsReadOnly();
		toolbar.querySelectorAll("button").forEach((button) => {
			button.disabled = disabled;
		});
	};

	const ensureToolbar = () => {
		scheduled = false;
		if (destroyed || !root.isConnected) return;

		const nextEditor = root.querySelector(".eduedge-question-editor");
		if (!nextEditor) return;

		if (editor !== nextEditor || !toolbar?.isConnected) {
			toolbar?.remove();
			help?.remove();
			if (editor) editor.classList.remove("eduedge-rich-editor__surface", "eduedge-native-question-surface");

			editor = nextEditor;
			activeTextTarget = editor;
			editor.setAttribute("dir", "ltr");
			editor.classList.add("eduedge-rich-editor__surface", "eduedge-native-question-surface");
			buildToolbar();
			editor.parentNode.insertBefore(toolbar, editor);
			editor.parentNode.insertBefore(help, editor.nextSibling);
		}

		applyReadOnlyState();
	};

	const scheduleEnsure = () => {
		if (scheduled || destroyed) return;
		scheduled = true;
		window.requestAnimationFrame(ensureToolbar);
	};

	const rememberTarget = (event) => {
		const target = event.target;
		if (target === editor || target?.matches?.(".eduedge-answer-row textarea, .eduedge-question-panel--editor textarea")) {
			activeTextTarget = target;
		}
	};

	root.addEventListener("focusin", rememberTarget);
	const observer = new MutationObserver(scheduleEnsure);
	observer.observe(root, {
		childList: true,
		subtree: true,
		attributes: true,
		attributeFilter: ["class", "contenteditable"],
	});
	ensureToolbar();

	return {
		destroy() {
			destroyed = true;
			observer.disconnect();
			root.removeEventListener("focusin", rememberTarget);
			toolbar?.remove();
			help?.remove();
			editor?.classList.remove("eduedge-rich-editor__surface", "eduedge-native-question-surface");
			toolbar = null;
			help = null;
			editor = null;
		},
	};
}

export function createEduEdgeQuestionBuilderApp(rootProps = null) {
	const app = createEduEdgeApp(EduEdgeQuestionBuilder, rootProps);
	const originalMount = app.mount.bind(app);
	const originalUnmount = app.unmount.bind(app);
	let toolbarController = null;

	app.mount = (target, ...args) => {
		const mounted = originalMount(target, ...args);
		toolbarController?.destroy();
		toolbarController = installNativeQuestionToolbar(resolveMountRoot(target));
		return mounted;
	};

	app.unmount = (...args) => {
		toolbarController?.destroy();
		toolbarController = null;
		return originalUnmount(...args);
	};

	return app;
}

if (typeof window !== "undefined") {
	window.EduEdgeQuestionBuilder = EduEdgeQuestionBuilder;
	window.createEduEdgeQuestionBuilderApp = createEduEdgeQuestionBuilderApp;
}

export default EduEdgeQuestionBuilder;
