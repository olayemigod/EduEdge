(() => {
	"use strict";

	const ROOT_ID = "eduedge-cbt-candidate-root";
	const QUESTION_TEXT_ID = "eduedge-cbt-current-question-text";

	function enhanceCandidateRuntime() {
		const root = document.getElementById(ROOT_ID);
		if (!root) return;

		const questionText = root.querySelector(".cbt-question-text");
		if (questionText) {
			questionText.id = QUESTION_TEXT_ID;
			questionText.setAttribute("role", "heading");
			questionText.setAttribute("aria-level", "2");
		}

		const answerArea = root.querySelector(".cbt-answer-area");
		if (answerArea && questionText) {
			answerArea.setAttribute("role", "group");
			answerArea.setAttribute("aria-labelledby", QUESTION_TEXT_ID);
		}

		for (const input of root.querySelectorAll(".cbt-text-answer, .cbt-numeric-answer")) {
			if (!input.getAttribute("aria-label")) {
				input.setAttribute(
					"aria-label",
					input.classList.contains("cbt-numeric-answer") ? "Numeric answer" : "Written answer"
				);
			}
			if (questionText) input.setAttribute("aria-describedby", QUESTION_TEXT_ID);
		}

		for (const button of root.querySelectorAll(".cbt-question-number")) {
			if (button.classList.contains("current")) button.setAttribute("aria-current", "step");
			else button.removeAttribute("aria-current");
		}

		const connection = root.querySelector(".cbt-connection-badge");
		if (connection) {
			connection.setAttribute("role", "status");
			connection.setAttribute("aria-live", "polite");
		}
	}

	function install() {
		const root = document.getElementById(ROOT_ID);
		if (!root || root.dataset.eduedgeAccessibilityBound === "1") return;
		root.dataset.eduedgeAccessibilityBound = "1";
		enhanceCandidateRuntime();
		const observer = new MutationObserver(() => enhanceCandidateRuntime());
		observer.observe(root, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] });
	}

	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install, { once: true });
	else install();
})();
