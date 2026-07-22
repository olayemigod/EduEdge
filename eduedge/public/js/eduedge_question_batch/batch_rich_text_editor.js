import { installQuestionRichTextEditor } from "../eduedge_question_builder/rich_text_editor";


function findQuestionTextarea(card) {
	return [...card.querySelectorAll("label.eduedge-batch-field--wide textarea")].find((textarea) => {
		const label = textarea.closest("label");
		const fieldLabel = label?.querySelector(":scope > span")?.textContent || "";
		return fieldLabel.trim().startsWith("Question");
	});
}


function prepareCardTargets(card) {
	card.classList.add("eduedge-question-panel--editor");
	card.querySelectorAll(".eduedge-card-answer-row").forEach((row) => {
		row.classList.add("eduedge-answer-row");
	});
}


function installCardEditor(card) {
	if (!card || card.dataset.eduedgeBatchRichText === "1") return null;
	const textarea = findQuestionTextarea(card);
	if (!textarea) return null;

	card.dataset.eduedgeBatchRichText = "1";
	prepareCardTargets(card);

	const originalDisplay = textarea.style.display;
	const source = document.createElement("div");
	source.className = "eduedge-question-editor eduedge-batch-question-editor-source";
	source.innerHTML = textarea.value || "";
	source.setAttribute("contenteditable", textarea.disabled ? "false" : "true");
	if (textarea.disabled) source.classList.add("is-read-only");
	textarea.parentNode.insertBefore(source, textarea);
	textarea.style.display = "none";
	textarea.setAttribute("aria-hidden", "true");

	let syncingToTextarea = false;
	const syncToTextarea = () => {
		syncingToTextarea = true;
		textarea.value = source.innerHTML;
		textarea.dispatchEvent(new Event("input", { bubbles: true }));
		queueMicrotask(() => {
			syncingToTextarea = false;
		});
	};
	source.addEventListener("input", syncToTextarea);

	const editorController = installQuestionRichTextEditor(card);
	if (!editorController) {
		source.removeEventListener("input", syncToTextarea);
		source.remove();
		textarea.style.display = originalDisplay;
		textarea.removeAttribute("aria-hidden");
		delete card.dataset.eduedgeBatchRichText;
		return null;
	}

	const refresh = () => {
		if (!card.isConnected || !textarea.isConnected || !source.isConnected) return false;
		prepareCardTargets(card);
		const readOnly = Boolean(textarea.disabled || textarea.readOnly);
		source.classList.toggle("is-read-only", readOnly);
		source.setAttribute("contenteditable", readOnly ? "false" : "true");

		const visibleEditor = card.querySelector(".eduedge-rich-editor__surface");
		if (
			!syncingToTextarea
			&& document.activeElement !== visibleEditor
			&& source.innerHTML !== (textarea.value || "")
		) {
			source.innerHTML = textarea.value || "";
		}
		return editorController.refresh();
	};

	const observer = new MutationObserver(refresh);
	observer.observe(card, {
		childList: true,
		subtree: true,
		attributes: true,
		attributeFilter: ["disabled", "readonly", "class"],
	});
	refresh();

	return {
		refresh,
		destroy() {
			observer.disconnect();
			editorController.destroy();
			source.removeEventListener("input", syncToTextarea);
			source.remove();
			textarea.style.display = originalDisplay;
			textarea.removeAttribute("aria-hidden");
			delete card.dataset.eduedgeBatchRichText;
		},
	};
}


export function installBatchQuestionRichTextEditors(root) {
	if (!root) return { destroy() {} };
	const controllers = new Map();
	let scheduled = false;
	let destroyed = false;

	const scan = () => {
		scheduled = false;
		if (destroyed || !root.isConnected) return;

		for (const [card, controller] of controllers.entries()) {
			if (!card.isConnected || !controller.refresh()) {
				controller.destroy();
				controllers.delete(card);
			}
		}

		root.querySelectorAll(".eduedge-question-card").forEach((card) => {
			if (controllers.has(card)) return;
			const controller = installCardEditor(card);
			if (controller) controllers.set(card, controller);
		});
	};

	const scheduleScan = () => {
		if (scheduled || destroyed) return;
		scheduled = true;
		window.requestAnimationFrame(scan);
	};

	const observer = new MutationObserver(scheduleScan);
	observer.observe(root, { childList: true, subtree: true });
	scheduleScan();

	return {
		destroy() {
			destroyed = true;
			observer.disconnect();
			controllers.forEach((controller) => controller.destroy());
			controllers.clear();
		},
	};
}
