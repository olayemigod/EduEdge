(() => {
	"use strict";

	function installAnswerSaveQueue() {
		const runtime = window.EduEdgeCBTCandidateRuntime;
		if (!runtime) {
			window.setTimeout(installAnswerSaveQueue, 25);
			return;
		}
		if (runtime.__answerSaveQueueInstalled) return;
		runtime.__answerSaveQueueInstalled = true;

		const originalSaveAnswer = runtime.saveAnswer.bind(runtime);
		const questionQueues = new Map();
		runtime.saveAnswer = function serialisedSaveAnswer(questionKey, answer) {
			const previous = questionQueues.get(questionKey) || Promise.resolve();
			const next = previous
				.catch(() => undefined)
				.then(() => originalSaveAnswer(questionKey, answer));
			questionQueues.set(questionKey, next);
			next.finally(() => {
				if (questionQueues.get(questionKey) === next) questionQueues.delete(questionKey);
			});
			return next;
		};
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", () => window.setTimeout(installAnswerSaveQueue, 0), {
			once: true,
		});
	} else {
		window.setTimeout(installAnswerSaveQueue, 0);
	}
})();
