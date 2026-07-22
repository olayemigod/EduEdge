const QUESTION_FORMAT_COMMANDS = [
	{ label: "B", title: "Bold", command: "bold", className: "is-bold" },
	{ label: "I", title: "Italic", command: "italic", className: "is-italic" },
	{ label: "U", title: "Underline", command: "underline", className: "is-underline" },
	{ label: "x²", title: "Superscript selected text", command: "superscript" },
	{ label: "x₂", title: "Subscript selected text", command: "subscript" },
	{ label: "• List", title: "Bulleted list", command: "insertUnorderedList" },
	{ label: "1. List", title: "Numbered list", command: "insertOrderedList" },
	{ label: "Clear", title: "Remove formatting", command: "removeFormat" },
];

const QUESTION_QUICK_SYMBOLS = ["²", "³", "₀", "₁", "₂", "₃", "√", "π", "θ", "Δ", "∑", "∞", "×", "÷", "±", "≤", "≥", "≠", "°"];

function resolveQuestionName() {
	const route = frappe.get_route ? frappe.get_route() : [];
	if (route[0] === "eduedge-question-builder" && route[1]) return route[1];
	try {
		return new URL(window.location.href).searchParams.get("question") || null;
	} catch (_error) {
		return null;
	}
}

function placeQuestionCaretAtEnd(editor) {
	const selection = window.getSelection();
	if (!selection) return;
	const range = document.createRange();
	range.selectNodeContents(editor);
	range.collapse(false);
	selection.removeAllRanges();
	selection.addRange(range);
}

function makeQuestionToolbarButton(label, title, onClick, className = "") {
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

function installQuestionToolbar(root) {
	if (!root) return { destroy() {} };

	let destroyed = false;
	let scheduled = false;
	let editor = null;
	let toolbar = null;
	let help = null;
	let activeTextTarget = null;

	const editorIsReadOnly = () =>
		!editor || editor.getAttribute("contenteditable") === "false" || editor.classList.contains("is-read-only");

	const syncEditor = () => {
		editor?.dispatchEvent(new Event("input", { bubbles: true }));
	};

	const focusEditor = () => {
		if (!editor) return;
		editor.focus();
		const selection = window.getSelection();
		if (!editor.contains(selection?.anchorNode)) placeQuestionCaretAtEnd(editor);
	};

	const runCommand = (command) => {
		if (editorIsReadOnly()) return;
		activeTextTarget = editor;
		focusEditor();
		document.execCommand(command, false, null);
		syncEditor();
	};

	const insertSymbol = (value) => {
		if (
			(activeTextTarget instanceof HTMLInputElement || activeTextTarget instanceof HTMLTextAreaElement)
			&& !activeTextTarget.disabled
			&& !activeTextTarget.readOnly
		) {
			const start = Number.isInteger(activeTextTarget.selectionStart)
				? activeTextTarget.selectionStart
				: activeTextTarget.value.length;
			const end = Number.isInteger(activeTextTarget.selectionEnd) ? activeTextTarget.selectionEnd : start;
			activeTextTarget.setRangeText(value, start, end, "end");
			activeTextTarget.dispatchEvent(new Event("input", { bubbles: true }));
			activeTextTarget.focus();
			return;
		}

		if (editorIsReadOnly()) return;
		activeTextTarget = editor;
		focusEditor();
		document.execCommand("insertText", false, value);
		syncEditor();
	};

	const buildToolbar = () => {
		toolbar = document.createElement("div");
		toolbar.className = "eduedge-rich-editor__toolbar eduedge-page-question-toolbar";
		toolbar.setAttribute("role", "toolbar");
		toolbar.setAttribute("aria-label", "Question formatting");

		QUESTION_FORMAT_COMMANDS.forEach((item) => {
			toolbar.appendChild(
				makeQuestionToolbarButton(item.label, item.title, () => runCommand(item.command), item.className)
			);
		});

		const symbolLabel = document.createElement("span");
		symbolLabel.className = "eduedge-rich-editor__symbols-label";
		symbolLabel.textContent = "Symbols";
		toolbar.appendChild(symbolLabel);

		const symbols = document.createElement("div");
		symbols.className = "eduedge-rich-editor__symbols";
		QUESTION_QUICK_SYMBOLS.forEach((symbol) => {
			symbols.appendChild(
				makeQuestionToolbarButton(symbol, `Insert ${symbol}`, () => insertSymbol(symbol), "is-symbol")
			);
		});
		toolbar.appendChild(symbols);

		help = document.createElement("p");
		help.className = "eduedge-rich-editor__help eduedge-page-question-help";
		help.textContent = "Select text before using superscript or subscript. Symbols also insert into the last focused answer, answer-key or marking-guide field.";
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
			if (editor) editor.classList.remove("eduedge-rich-editor__surface");

			editor = nextEditor;
			activeTextTarget = editor;
			editor.setAttribute("dir", "ltr");
			editor.classList.add("eduedge-rich-editor__surface");
			buildToolbar();
			editor.parentNode.insertBefore(toolbar, editor);
			editor.parentNode.insertBefore(help, editor.nextSibling);
		}

		applyReadOnlyState();
	};

	const scheduleToolbar = () => {
		if (scheduled || destroyed) return;
		scheduled = true;
		window.requestAnimationFrame(ensureToolbar);
	};

	const rememberTarget = (event) => {
		const target = event.target;
		if (
			target === editor
			|| target?.matches?.(
				".eduedge-answer-row textarea, .eduedge-question-panel--editor textarea, .eduedge-question-panel--editor input[type='text']"
			)
		) {
			activeTextTarget = target;
		}
	};

	root.addEventListener("focusin", rememberTarget);
	const observer = new MutationObserver(scheduleToolbar);
	observer.observe(root, {
		childList: true,
		subtree: true,
		attributes: true,
		attributeFilter: ["class", "contenteditable"],
	});
	const interval = window.setInterval(ensureToolbar, 500);
	ensureToolbar();

	return {
		destroy() {
			destroyed = true;
		observer.disconnect();
		window.clearInterval(interval);
		root.removeEventListener("focusin", rememberTarget);
		toolbar?.remove();
		help?.remove();
		editor?.classList.remove("eduedge-rich-editor__surface");
		toolbar = null;
		help = null;
		editor = null;
		},
	};
}

frappe.pages["eduedge-question-builder"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Question Builder"),
		single_column: true,
	});
};

frappe.pages["eduedge-question-builder"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	page.clear_inner_toolbar();
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	wrapper.question_toolbar?.destroy();
	wrapper.question_toolbar = null;

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge Question Builder", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(
		`<div class="p-6 text-center text-muted">${__("Loading Question Builder...")}</div>`
	).appendTo(page.body);

	const fail = (message) => {
		$loading.remove();
		$(
			`<div class="alert alert-danger p-6 text-center">
				<strong>${__("Question Builder failed to load")}</strong>
				<div>${frappe.utils.escape_html(message || "")}</div>
			</div>`
		).appendTo(page.body);
	};

	frappe.require("edgeui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		const runtime = window.EdgeSuiteUI || window.EdgeUI;
		if (!runtime?.install || !runtime?.components?.EdgeAppShell) {
			fail(__("The standalone EdgeSuite UI runtime is unavailable or incomplete."));
			return;
		}

		frappe.require("eduedge_question_builder.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (
				!window.EduEdgeQuestionBuilder
				|| typeof window.createEduEdgeQuestionBuilderApp !== "function"
			) {
				fail(__("The EduEdge Question Builder bundle is unavailable or incomplete."));
				return;
			}
			$loading.remove();
			const root = $(
				'<div class="eduedge-question-builder-root" data-edge-product="eduedge"></div>'
			).appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeQuestionBuilderApp({
					pageName: "eduedge-question-builder",
					questionName: resolveQuestionName(),
				});
				wrapper.vue_app.mount(root[0]);
				wrapper.question_toolbar = installQuestionToolbar(root[0]);
			} catch (error) {
				console.error("Failed to mount EduEdge Question Builder", error);
				wrapper.question_toolbar?.destroy();
				wrapper.question_toolbar = null;
				fail(error.message || String(error));
			}
		});
	});
};
