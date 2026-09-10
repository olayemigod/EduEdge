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
	["²", "Squared"],
	["³", "Cubed"],
	["₀", "Subscript zero"],
	["₁", "Subscript one"],
	["₂", "Subscript two"],
	["₃", "Subscript three"],
	["√", "Square root"],
	["π", "Pi"],
	["θ", "Theta"],
	["Δ", "Delta"],
	["∑", "Summation"],
	["∞", "Infinity"],
	["×", "Multiplication"],
	["÷", "Division"],
	["±", "Plus or minus"],
	["≤", "Less than or equal to"],
	["≥", "Greater than or equal to"],
	["≠", "Not equal to"],
	["°", "Degree"],
].map(([value, title]) => ({ value, title }));

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

function sourceValue(source) {
	if (source instanceof HTMLTextAreaElement || source instanceof HTMLInputElement) {
		return source.value || "";
	}
	return source.innerHTML || "";
}

function updateSource(source, value) {
	if (source instanceof HTMLTextAreaElement || source instanceof HTMLInputElement) {
		source.value = value;
	} else {
		source.innerHTML = value;
	}
	source.dispatchEvent(new Event("input", { bubbles: true }));
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

function insertText(editor, value) {
	const selection = window.getSelection();
	if (!selection || !editor.contains(selection.anchorNode)) {
		placeCaretAtEnd(editor);
	}
	if (document.execCommand("insertText", false, value)) return;
	const activeSelection = window.getSelection();
	if (!activeSelection?.rangeCount) return;
	const range = activeSelection.getRangeAt(0);
	range.deleteContents();
	const node = document.createTextNode(value);
	range.insertNode(node);
	range.setStartAfter(node);
	range.collapse(true);
	activeSelection.removeAllRanges();
	activeSelection.addRange(range);
}

function isSourceReadOnly(source) {
	return Boolean(
		source.disabled
		|| source.readOnly
		|| source.classList.contains("is-read-only")
		|| source.getAttribute("contenteditable") === "false"
	);
}

function findQuestionSources(root) {
	const sources = new Set(root.querySelectorAll(".eduedge-question-editor"));
	root.querySelectorAll(".eduedge-question-card").forEach((card) => {
		const source = card.querySelector(":scope > .eduedge-batch-field--wide > textarea");
		if (source) sources.add(source);
	});
	return [...sources];
}

function enhanceQuestionSource(source, registry) {
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
	editor.dataset.placeholder = source.getAttribute("placeholder") || "Enter the question shown to candidates";
	editor.innerHTML = sourceValue(source);

	function readOnly() {
		return isSourceReadOnly(source);
	}

	function updateReadOnlyState() {
		const disabled = readOnly();
		editor.contentEditable = disabled ? "false" : "true";
		wrapper.classList.toggle("is-read-only", disabled);
		toolbar.querySelectorAll("button").forEach((button) => {
			button.disabled = disabled;
		});
	}

	function syncToSource() {
		if (readOnly()) return;
		updateSource(source, editor.innerHTML);
	}

	function runCommand(command) {
		if (readOnly()) return;
		editor.focus();
		if (!editor.contains(window.getSelection()?.anchorNode)) placeCaretAtEnd(editor);
		document.execCommand(command, false, null);
		syncToSource();
	}

	function insertSymbol(value) {
		if (readOnly()) return;
		editor.focus();
		insertText(editor, value);
		syncToSource();
	}

	FORMAT_COMMANDS.forEach((item) => {
		toolbar.appendChild(makeButton(item.label, item.title, () => runCommand(item.command), item.className));
	});

	const symbolLabel = document.createElement("span");
	symbolLabel.className = "eduedge-rich-editor__symbols-label";
	symbolLabel.textContent = "Symbols";
	toolbar.appendChild(symbolLabel);

	const symbolPanel = document.createElement("div");
	symbolPanel.className = "eduedge-rich-editor__symbols";
	symbolPanel.setAttribute("aria-label", "Maths and science symbols");
	QUICK_SYMBOLS.forEach((item) => {
		symbolPanel.appendChild(makeButton(item.value, item.title, () => insertSymbol(item.value), "is-symbol"));
	});
	toolbar.appendChild(symbolPanel);

	const help = document.createElement("p");
	help.className = "eduedge-rich-editor__help";
	help.textContent = "Use formatting for the question text. Select text before applying superscript or subscript.";

	wrapper.appendChild(toolbar);
	wrapper.appendChild(editor);
	wrapper.appendChild(help);
	source.parentNode.insertBefore(wrapper, source);

	editor.addEventListener("input", syncToSource);

	const sourceObserver = new MutationObserver(() => {
		updateReadOnlyState();
		if (document.activeElement !== editor) {
			const nextValue = sourceValue(source);
			if (nextValue !== editor.innerHTML) editor.innerHTML = nextValue;
		}
	});
	sourceObserver.observe(source, {
		attributes: true,
		attributeFilter: ["class", "contenteditable", "disabled", "readonly"],
		childList: true,
		characterData: true,
		subtree: true,
	});
	updateReadOnlyState();

	const instance = {
		source,
		wrapper,
		refresh() {
			if (!source.isConnected || !wrapper.isConnected) return false;
			updateReadOnlyState();
			if (document.activeElement !== editor) {
				const nextValue = sourceValue(source);
				if (nextValue !== editor.innerHTML) editor.innerHTML = nextValue;
			}
			return true;
		},
		destroy() {
			sourceObserver.disconnect();
			wrapper.remove();
			source.style.removeProperty("display");
			source.removeAttribute("aria-hidden");
			delete source.dataset.eduedgeRichTextEnhanced;
			registry.delete(instance);
		},
	};
	registry.add(instance);
	return instance;
}

export function installEduEdgeQuestionRichTextEditors(root) {
	if (!root) return null;
	const instances = new Set();

	function scan() {
		for (const instance of [...instances]) {
			if (!instance.refresh()) instance.destroy();
		}
		findQuestionSources(root).forEach((source) => enhanceQuestionSource(source, instances));
	}

	const observer = new MutationObserver(() => scan());
	observer.observe(root, { childList: true, subtree: true });
	scan();

	return {
		refresh: scan,
		destroy() {
			observer.disconnect();
			for (const instance of [...instances]) instance.destroy();
		},
	};
}

if (typeof window !== "undefined") {
	window.installEduEdgeQuestionRichTextEditors = installEduEdgeQuestionRichTextEditors;
}
