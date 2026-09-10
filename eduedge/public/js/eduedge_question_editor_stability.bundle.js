function captureSelectionOffsets(root) {
	const selection = window.getSelection?.();
	if (!selection?.rangeCount || !root.contains(selection.anchorNode)) return null;
	const range = selection.getRangeAt(0);
	const startRange = document.createRange();
	startRange.selectNodeContents(root);
	startRange.setEnd(range.startContainer, range.startOffset);
	const endRange = document.createRange();
	endRange.selectNodeContents(root);
	endRange.setEnd(range.endContainer, range.endOffset);
	return {
		start: startRange.toString().length,
		end: endRange.toString().length,
	};
}

function pointAtTextOffset(root, offset) {
	const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
	let remaining = Math.max(0, Number(offset || 0));
	let node = walker.nextNode();
	let last = null;
	while (node) {
		last = node;
		const length = node.nodeValue?.length || 0;
		if (remaining <= length) return { node, offset: remaining };
		remaining -= length;
		node = walker.nextNode();
	}
	if (last) return { node: last, offset: last.nodeValue?.length || 0 };
	return { node: root, offset: root.childNodes.length };
}

function restoreSelectionOffsets(root, snapshot) {
	if (!snapshot || document.activeElement !== root || !root.isConnected) return;
	const selection = window.getSelection?.();
	if (!selection) return;
	const start = pointAtTextOffset(root, snapshot.start);
	const end = pointAtTextOffset(root, snapshot.end);
	try {
		const range = document.createRange();
		range.setStart(start.node, start.offset);
		range.setEnd(end.node, end.offset);
		selection.removeAllRanges();
		selection.addRange(range);
	} catch (_error) {
		// If a framework patch replaced the exact text node shape, the next input
		// event will capture a fresh valid selection. Do not mutate editor content.
	}
}

function protectQuestionEditor(editor, registry) {
	if (!editor || editor.dataset.eduedgeCaretStable === "1") return;
	editor.dataset.eduedgeCaretStable = "1";
	let scheduledFrame = 0;

	const onInput = () => {
		const snapshot = captureSelectionOffsets(editor);
		if (!snapshot) return;
		queueMicrotask(() => {
			restoreSelectionOffsets(editor, snapshot);
			if (scheduledFrame) cancelAnimationFrame(scheduledFrame);
			scheduledFrame = requestAnimationFrame(() => restoreSelectionOffsets(editor, snapshot));
		});
	};

	editor.addEventListener("input", onInput);
	registry.add({
		editor,
		destroy() {
			editor.removeEventListener("input", onInput);
			if (scheduledFrame) cancelAnimationFrame(scheduledFrame);
			delete editor.dataset.eduedgeCaretStable;
		},
	});
}

function markDraftSaveAction(root) {
	const buttons = [...root.querySelectorAll("button:not([disabled])")].filter(
		(button) => String(button.textContent || "").trim().toLowerCase() === "save draft",
	);
	if (buttons.length !== 1) return;
	buttons[0].setAttribute("data-edgesuite-save", "draft");
	buttons[0].setAttribute("aria-label", "Save Draft");
}

export function installEduEdgeQuestionEditorStability(root) {
	if (!root) return null;
	const registry = new Set();

	function scan() {
		root.querySelectorAll(".question-editor[contenteditable]").forEach((editor) => {
			protectQuestionEditor(editor, registry);
		});
		markDraftSaveAction(root);
	}

	const observer = new MutationObserver(scan);
	observer.observe(root, { childList: true, subtree: true });
	scan();

	return {
		refresh: scan,
		destroy() {
			observer.disconnect();
			for (const instance of registry) instance.destroy();
			registry.clear();
		},
	};
}

if (typeof window !== "undefined") {
	window.installEduEdgeQuestionEditorStability = installEduEdgeQuestionEditorStability;
}
