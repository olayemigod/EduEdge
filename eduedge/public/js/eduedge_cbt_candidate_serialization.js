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
		const originalRequestSubmission = runtime.requestSubmission.bind(runtime);
		const originalHandleLocalTimeout = runtime.handleLocalTimeout.bind(runtime);
		const questionQueues = new Map();
		const capturedDrafts = new Map();
		const draftTimers = new Map();

		function enqueue(questionKey, operation) {
			const previous = questionQueues.get(questionKey) || Promise.resolve();
			const next = previous.catch(() => undefined).then(operation);
			questionQueues.set(questionKey, next);
			next.finally(() => {
				if (questionQueues.get(questionKey) === next) questionQueues.delete(questionKey);
			});
			return next;
		}

		runtime.saveAnswer = function serialisedSaveAnswer(questionKey, answer) {
			return enqueue(questionKey, () => originalSaveAnswer(questionKey, answer));
		};

		async function persistCapturedDraft(questionKey) {
			window.clearTimeout(draftTimers.get(questionKey));
			draftTimers.delete(questionKey);
			const draft = capturedDrafts.get(questionKey);
			if (!draft || !runtime.storage) return;
			capturedDrafts.delete(questionKey);
			await enqueue(questionKey, async () => {
				const current = runtime.answers.get(questionKey) || {};
				const revision = Math.max(
					Number(current.client_revision || 0),
					Number(current.synced_revision || 0)
				) + 1;
				const row = {
					question_snapshot_key: questionKey,
					answer: draft.answer,
					client_revision: revision,
					synced_revision: Number(current.synced_revision || 0),
					client_saved_at: draft.client_saved_at,
					server_saved_at: current.server_saved_at || null,
				};
				await runtime.storage.putAnswer(row);
				runtime.answers.set(questionKey, { ...current, ...row });
				await runtime.reloadLocalAnswers();
				runtime.updateFooterStatus("Saved in this browser");
				runtime.queueSync();
			});
		}

		async function awaitQuestionQueues() {
			while (questionQueues.size) {
				await Promise.all(
					Array.from(questionQueues.values(), (promise) => promise.catch(() => undefined))
				);
			}
		}

		async function flushCapturedDrafts() {
			const keys = Array.from(capturedDrafts.keys());
			for (const questionKey of keys) await persistCapturedDraft(questionKey);
			await awaitQuestionQueues();
		}

		function activeQuestion() {
			return runtime.questions?.[runtime.currentIndex] || null;
		}

		function captureControlValue(target) {
			const question = activeQuestion();
			if (!question) return false;
			let answer = null;
			if (target.matches(".cbt-text-answer")) {
				answer = { text: target.value };
			} else if (target.matches(".cbt-numeric-answer")) {
				answer = { value: target.value };
			}
			if (!answer) return false;
			capturedDrafts.set(question.snapshot_key, {
				answer,
				client_saved_at: runtime.serverNowString(),
			});
			window.clearTimeout(draftTimers.get(question.snapshot_key));
			draftTimers.set(
				question.snapshot_key,
				window.setTimeout(() => persistCapturedDraft(question.snapshot_key), 180)
			);
			return true;
		}

		runtime.root.addEventListener(
			"input",
			(event) => {
				if (!captureControlValue(event.target)) return;
				event.stopImmediatePropagation();
			},
			true
		);
		runtime.root.addEventListener(
			"change",
			(event) => {
				if (!captureControlValue(event.target)) return;
				event.stopImmediatePropagation();
				const question = activeQuestion();
				if (question) persistCapturedDraft(question.snapshot_key);
			},
			true
		);
		runtime.root.addEventListener(
			"blur",
			(event) => {
				if (!captureControlValue(event.target)) return;
				event.stopImmediatePropagation();
				const question = activeQuestion();
				if (question) persistCapturedDraft(question.snapshot_key);
			},
			true
		);
		runtime.root.addEventListener(
			"click",
			async (event) => {
				const submit = event.target.closest?.(".cbt-submit");
				if (!submit) return;
				event.preventDefault();
				event.stopImmediatePropagation();
				await flushCapturedDrafts();
				await originalRequestSubmission();
			},
			true
		);

		runtime.handleLocalTimeout = async function guardedLocalTimeout() {
			await flushCapturedDrafts();
			return originalHandleLocalTimeout();
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
