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

const QUICK_SYMBOLS = [
	{ value: "²", title: "Squared" },
	{ value: "³", title: "Cubed" },
	{ value: "₀", title: "Subscript zero" },
	{ value: "₁", title: "Subscript one" },
	{ value: "₂", title: "Subscript two" },
	{ value: "₃", title: "Subscript three" },
	{ value: "√", title: "Square root" },
	{ value: "π", title: "Pi" },
	{ value: "θ", title: "Theta" },
	{ value: "Δ", title: "Delta" },
	{ value: "∑", title: "Summation" },
	{ value: "∞", title: "Infinity" },
	{ value: "×", title: "Multiplication" },
	{ value: "÷", title: "Division" },
	{ value: "±", title: "Plus or minus" },
	{ value: "≤", title: "Less than or equal to" },
	{ value: "≥", title: "Greater than or equal to" },
	{ value: "≠", title: "Not equal to" },
	{ value: "°", title: "Degree" },
];

function makeButton(label, title, onClick, className = "") {
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

function placeCaretAtEnd(element) {
	const selection = window.getSelection();
	if (!selection) return;
	const range = document.createRange();
	range.selectNodeContents(element);
	range.collapse(false);
	selection.removeAllRanges();
	selection.addRange(range);
}

function insertTextAtTarget(target, value) {
	if (!target || !value) return false;
	if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) {
		const start = Number.isInteger(target.selectionStart) ? target.selectionStart : target.value.length;
		const end = Number.isInteger(target.selectionEnd) ? target.selectionEnd : start;
		target.setRangeText(value, start, end, "end");
		target.dispatchEvent(new Event("input", { bubbles: true }));
		target.focus();
		return true;
	}
	return false;
}

export function installQuestionRichTextEditor(root) {
	if (!root) return null;
	const source = root.querySelector(".eduedge-question-editor");
	if (!source || source.dataset.eduedgeRichTextEnhanced === "1") return null;

	source.dataset.eduedgeRichTextEnhanced = "1";
	source.style.display = "none";
	source.setAttribute("aria-hidden", "true");

	const wrapper = document.createElement("div");
	wrapper.className = "eduedge-rich-editor";

	const toolbar = document.createElement("div");
	toolbar.className = "eduedge-rich-editor__toolbar";
	toolbar.setAttribute("role", "toolbar");
	toolbar.setAttribute("aria-label", "Question formatting");

	const editor = document.createElement("div");
	editor.className = "eduedge-rich-editor__surface";
	editor.setAttribute("role", "textbox");
	editor.setAttribute("aria-label", "Question");
	editor.setAttribute("aria-multiline", "true");
	editor.setAttribute("dir", "ltr");
	editor.setAttribute("spellcheck", "true");
	editor.dataset.placeholder = "Enter the question shown to candidates";
	editor.innerHTML = source.innerHTML || "";

	const symbolPanel = document.createElement("div");
	symbolPanel.className = "eduedge-rich-editor__symbols";
	symbolPanel.setAttribute("aria-label", "Maths and science symbols");

	let syncingFromEditor = false;
	let activeTextTarget = editor;

	function isReadOnly() {
		return source.classList.contains("is-read-only") || source.getAttribute("contenteditable") === "false";
	}

	function updateReadOnlyState() {
		const readOnly = isReadOnly();
		editor.contentEditable = readOnly ? "false" : "true";
		wrapper.classList.toggle("is-read-only", readOnly);
		toolbar.querySelectorAll("button").forEach((button) => {
			button.disabled = readOnly;
		});
	}

	function syncToSource() {
		if (isReadOnly()) return;
		syncingFromEditor = true;
		source.innerHTML = editor.innerHTML;
		source.dispatchEvent(new Event("input", { bubbles: true }));
		queueMicrotask(() => {
			syncingFromEditor = false;
		});
	}

	function runCommand(command) {
		if (isReadOnly()) return;
		activeTextTarget = editor;
		editor.focus();
		if (!editor.contains(window.getSelection()?.anchorNode)) placeCaretAtEnd(editor);
		document.execCommand(command, false, null);
		syncToSource();
	}

	function insertSymbol(value) {
		if (isReadOnly()) return;
		if (insertTextAtTarget(activeTextTarget, value)) return;
		activeTextTarget = editor;
		editor.focus();
		if (!editor.contains(window.getSelection()?.anchorNode)) placeCaretAtEnd(editor);
		document.execCommand("insertText", false, value);
		syncToSource();
	}

	FORMAT_COMMANDS.forEach((item) => {
		toolbar.appendChild(makeButton(item.label, item.title, () => runCommand(item.command), item.className));
	});

	QUICK_SYMBOLS.forEach((item) => {
		symbolPanel.appendChild(makeButton(item.value, item.title, () => insertSymbol(item.value), "is-symbol"));
	});

	const symbolLabel = document.createElement("span");
	symbolLabel.className = "eduedge-rich-editor__symbols-label";
	symbolLabel.textContent = "Symbols";
	toolbar.appendChild(symbolLabel);
	toolbar.appendChild(symbolPanel);

	const help = document.createElement("p");
	help.className = "eduedge-rich-editor__help";
	help.textContent = "Select text before using superscript or subscript. Symbol buttons also insert into the last focused answer or answer-key field.";

	wrapper.appendChild(toolbar);
	wrapper.appendChild(editor);
	wrapper.appendChild(help);
	source.parentNode.insertBefore(wrapper, source);

	const focusTargetsSelector = [
		".eduedge-rich-editor__surface",
		".eduedge-answer-row textarea",
		".eduedge-question-panel--editor textarea",
	].join(",");

	function rememberTarget(event) {
		const target = event.target;
		if (target?.matches?.(focusTargetsSelector)) activeTextTarget = target;
	}

	editor.addEventListener("input", () => {
		activeTextTarget = editor;
		syncToSource();
	});
	root.addEventListener("focusin", rememberTarget);

	const observer = new MutationObserver(() => {
		updateReadOnlyState();
		if (!syncingFromEditor && document.activeElement !== editor && source.innerHTML !== editor.innerHTML) {
			editor.innerHTML = source.innerHTML || "";
		}
	});
	observer.observe(source, {
		attributes: true,
		attributeFilter: ["class", "contenteditable"],
		childList: true,
		characterData: true,
		subtree: true,
	});
	updateReadOnlyState();

	return {
		refresh() {
			if (!source.isConnected || !wrapper.isConnected) return false;
			updateReadOnlyState();
			if (document.activeElement !== editor && source.innerHTML !== editor.innerHTML) {
				editor.innerHTML = source.innerHTML || "";
			}
			return true;
		},
		destroy() {
			observer.disconnect();
			root.removeEventListener("focusin", rememberTarget);
			wrapper.remove();
			source.style.removeProperty("display");
			source.removeAttribute("aria-hidden");
			delete source.dataset.eduedgeRichTextEnhanced;
		},
	};
}
