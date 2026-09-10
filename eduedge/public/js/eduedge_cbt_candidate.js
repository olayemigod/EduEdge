(() => {
	"use strict";

	const API = Object.freeze({
		state: "eduedge.cbt.attempt_runtime_guard.get_attempt_state",
		start: "eduedge.cbt.attempts.start_attempt",
		sync: "eduedge.cbt.attempt_runtime_guard.sync_answers",
		heartbeat: "eduedge.cbt.attempts.record_heartbeat",
		submit: "eduedge.cbt.attempt_runtime_guard.submit_attempt",
	});
	const TERMINAL_STATUSES = new Set([
		"Submitted",
		"Auto Submitted",
		"Timed Out",
		"Cancelled",
		"Marked",
		"Reviewed",
	]);
	const SYNC_DEBOUNCE_MS = 900;
	const PERIODIC_SYNC_MS = 12000;
	const HEARTBEAT_MS = 30000;
	const BASIC_RICH_TEXT_TAGS = new Set([
		"P",
		"BR",
		"B",
		"STRONG",
		"I",
		"EM",
		"U",
		"OL",
		"UL",
		"LI",
		"SUP",
		"SUB",
		"CODE",
		"PRE",
		"BLOCKQUOTE",
		"TABLE",
		"THEAD",
		"TBODY",
		"TR",
		"TH",
		"TD",
		"SPAN",
		"DIV",
	]);

	function randomId() {
		if (window.crypto?.randomUUID) return window.crypto.randomUUID();
		const bytes = new Uint8Array(16);
		window.crypto?.getRandomValues?.(bytes);
		return Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("") || `${Date.now()}-${Math.random()}`;
	}

	function parseServerMessages(payload) {
		const messages = [];
		if (payload?._server_messages) {
			try {
				for (const encoded of JSON.parse(payload._server_messages)) {
					const row = JSON.parse(encoded);
					if (row?.message) messages.push(row.message);
				}
			} catch (error) {
				// Fall back to the normal API error fields below.
			}
		}
		if (payload?.message && typeof payload.message === "string") messages.push(payload.message);
		if (!messages.length && payload?.exception) messages.push(payload.exception);
		return messages.filter(Boolean).join("\n");
	}

	async function apiCall(method, args) {
		const headers = { "Content-Type": "application/json", Accept: "application/json" };
		const csrfToken = window.frappe?.csrf_token || window.csrf_token;
		if (csrfToken && csrfToken !== "None") headers["X-Frappe-CSRF-Token"] = csrfToken;
		const response = await window.fetch(`/api/method/${method}`, {
			method: "POST",
			headers,
			credentials: "same-origin",
			body: JSON.stringify(args || {}),
		});
		let payload = {};
		try {
			payload = await response.json();
		} catch (error) {
			throw new Error(`EduEdge CBT returned an unreadable response (${response.status}).`);
		}
		if (!response.ok || payload.exc || payload.exception) {
			throw new Error(parseServerMessages(payload) || `EduEdge CBT request failed (${response.status}).`);
		}
		return payload.message ?? payload;
	}

	function readLaunchContext() {
		const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
		const query = new URLSearchParams(window.location.search);
		const attempt = hash.get("attempt") || query.get("attempt") || "";
		let token = hash.get("token") || query.get("token") || "";
		const tokenKey = attempt ? `eduedge:cbt:launch-token:${attempt}` : "";
		if (attempt && token) window.sessionStorage.setItem(tokenKey, token);
		if (attempt && !token) token = window.sessionStorage.getItem(tokenKey) || "";
		if (attempt && (hash.has("token") || query.has("token") || window.location.hash)) {
			const clean = new URL(window.location.href);
			clean.hash = "";
			clean.searchParams.delete("token");
			clean.searchParams.set("attempt", attempt);
			window.history.replaceState({}, document.title, `${clean.pathname}${clean.search}`);
		}
		return { attempt, token };
	}

	function clientSessionId(attempt) {
		const key = `eduedge:cbt:client-session:${attempt}`;
		let value = window.localStorage.getItem(key);
		if (!value) {
			value = randomId();
			window.localStorage.setItem(key, value);
		}
		return value;
	}

	function sanitizeRichText(raw) {
		const template = document.createElement("template");
		template.innerHTML = String(raw || "");
		const walk = (node) => {
			for (const child of Array.from(node.childNodes)) {
				if (child.nodeType === Node.COMMENT_NODE) {
					child.remove();
					continue;
				}
				if (child.nodeType !== Node.ELEMENT_NODE) continue;
				if (!BASIC_RICH_TEXT_TAGS.has(child.tagName)) {
					child.replaceWith(document.createTextNode(child.textContent || ""));
					continue;
				}
				for (const attribute of Array.from(child.attributes)) {
					const allowedTableAttribute = ["colspan", "rowspan"].includes(attribute.name.toLowerCase());
					if (!allowedTableAttribute) child.removeAttribute(attribute.name);
				}
				walk(child);
			}
		};
		walk(template.content);
		return template.innerHTML;
	}

	function formatServerDateTime(date) {
		const pad = (value, size = 2) => String(value).padStart(size, "0");
		return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}.${pad(date.getMilliseconds(), 3)}`;
	}

	function formatDuration(totalSeconds) {
		const seconds = Math.max(0, Math.floor(Number(totalSeconds) || 0));
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		const remaining = seconds % 60;
		return hours > 0
			? `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`
			: `${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
	}

	function answerIsFilled(answer) {
		const payload = answer || {};
		return Boolean(
			(payload.selected_option_ids || []).length ||
			String(payload.text || "").trim() ||
			(payload.value !== "" && payload.value !== null && payload.value !== undefined)
		);
	}

	class CandidateRuntime {
		constructor(root) {
			this.root = root;
			this.launch = readLaunchContext();
			this.clientSession = this.launch.attempt ? clientSessionId(this.launch.attempt) : "";
			this.storage = null;
			this.serverState = null;
			this.questions = [];
			this.answers = new Map();
			this.currentIndex = 0;
			this.pendingCount = 0;
			this.syncing = false;
			this.syncPromise = null;
			this.syncTimer = null;
			this.timerInterval = null;
			this.periodicSyncInterval = null;
			this.heartbeatInterval = null;
			this.timerBaseSeconds = 0;
			this.timerBasePerformance = window.performance.now();
			this.serverClockOffsetMs = 0;
			this.connectionState = navigator.onLine ? "checking" : "offline";
			this.submissionRequested = false;
			this.locallyLocked = false;
			this.localTimeoutHandled = false;
			this.destroyed = false;
		}

		async init() {
			this.renderLoading("Opening secure examination session…");
			if (!this.launch.attempt || !this.launch.token) {
				this.renderFatal(
					"The examination link is incomplete. Open the original EduEdge launch link in this browser tab."
				);
				return;
			}
			if (!window.EduEdgeCBTRuntimeStorage?.open) {
				this.renderFatal("The EduEdge browser answer-storage module did not load.");
				return;
			}
			try {
				this.storage = await window.EduEdgeCBTRuntimeStorage.open(this.launch.attempt);
				this.currentIndex = Number(await this.storage.getMeta("current_question", 0)) || 0;
				this.submissionRequested = Boolean(await this.storage.getMeta("submission_requested", false));
				await this.loadStateWithOfflineFallback();
				this.installLifecycleHandlers();
				this.startBackgroundWork();
			} catch (error) {
				this.renderFatal(error.message || String(error));
			}
		}

		async loadStateWithOfflineFallback() {
			try {
				const state = await apiCall(API.state, {
					attempt_name: this.launch.attempt,
					launch_token: this.launch.token,
					client_session_id: this.clientSession,
				});
				this.setConnection("online");
				await this.applyServerState(state, false);
			} catch (error) {
				this.setConnection(navigator.onLine ? "degraded" : "offline");
				const cached = await this.storage.getMeta("cached_attempt_state", null);
				if (!cached || !["In Progress", "Pending Sync"].includes(cached.status)) throw error;
				await this.applyServerState(cached, true);
				this.showNotice(
					"You are offline. Existing questions and browser-saved answers are available. EduEdge will synchronise automatically when the connection returns.",
					"warning"
				);
			}
		}

		updateServerClock(serverTime) {
			if (!serverTime) return;
			const parsed = Date.parse(String(serverTime).replace(" ", "T"));
			if (Number.isFinite(parsed)) this.serverClockOffsetMs = parsed - Date.now();
		}

		serverNowString() {
			return formatServerDateTime(new Date(Date.now() + this.serverClockOffsetMs));
		}

		async applyServerState(state, fromCache) {
			this.serverState = { ...(state || {}) };
			this.updateServerClock(state.server_time);
			if (Array.isArray(state.questions) && state.questions.length) this.questions = state.questions;
			if (!fromCache) {
				await this.storage.seedServerAnswers(state.answers || {});
				const deadlineEpoch = Date.now() + Math.max(0, Number(state.seconds_remaining || 0)) * 1000;
				await this.storage.setMeta("timer_deadline_epoch", deadlineEpoch);
				await this.storage.setMeta("cached_attempt_state", {
					attempt: state.attempt,
					candidate_name: state.candidate_name,
					status: state.status,
					server_time: state.server_time,
					started_at: state.started_at,
					expires_at: state.expires_at,
					seconds_remaining: state.seconds_remaining,
					navigation_policy: state.navigation_policy,
					questions: state.questions || this.questions,
					answers: {},
					reported_pending_sync_count: state.reported_pending_sync_count || 0,
					last_sync_at: state.last_sync_at || null,
				});
			} else {
				const deadlineEpoch = Number(await this.storage.getMeta("timer_deadline_epoch", Date.now()));
				this.serverState.seconds_remaining = Math.max(0, Math.floor((deadlineEpoch - Date.now()) / 1000));
			}
			await this.reloadLocalAnswers();
			this.currentIndex = Math.max(0, Math.min(this.currentIndex, Math.max(0, this.questions.length - 1)));
			this.setTimer(Number(this.serverState.seconds_remaining || 0));
			this.renderForStatus();
			if (this.submissionRequested && navigator.onLine) this.queueSync(0);
		}

		async reloadLocalAnswers() {
			const rows = await this.storage.listAnswers();
			this.answers = new Map(rows.map((row) => [row.question_snapshot_key, row]));
			this.pendingCount = rows.filter(
				(row) => Number(row.client_revision || 0) > Number(row.synced_revision || 0)
			).length;
			this.updatePendingUI();
		}

		setTimer(seconds) {
			this.timerBaseSeconds = Math.max(0, Number(seconds || 0));
			this.timerBasePerformance = window.performance.now();
			this.localTimeoutHandled = false;
			this.updateTimerUI();
		}

		secondsRemaining() {
			const elapsed = (window.performance.now() - this.timerBasePerformance) / 1000;
			return Math.max(0, Math.floor(this.timerBaseSeconds - elapsed));
		}

		setConnection(value) {
			this.connectionState = value;
			this.updateConnectionUI();
		}

		renderLoading(message) {
			this.root.innerHTML = `<main class="cbt-loading"><div class="cbt-spinner" aria-hidden="true"></div><h1>EduEdge CBT</h1><p>${message}</p></main>`;
		}

		renderFatal(message) {
			this.root.innerHTML = `
				<main class="cbt-fatal" role="alert">
					<div class="cbt-fatal-card">
						<div class="cbt-mark">E</div>
						<h1>Unable to open examination</h1>
						<p></p>
						<button type="button" class="cbt-button cbt-button-primary">Try again</button>
					</div>
				</main>`;
			this.root.querySelector("p").textContent = message || "An unexpected error occurred.";
			this.root.querySelector("button").addEventListener("click", () => window.location.reload());
		}

		renderForStatus() {
			const status = this.serverState?.status;
			if (status === "Prepared") {
				this.renderPrepared();
				return;
			}
			if (status === "In Progress") {
				this.locallyLocked = false;
				this.renderExam();
				return;
			}
			if (status === "Pending Sync") {
				this.locallyLocked = true;
				this.renderTerminal(true);
				return;
			}
			this.locallyLocked = true;
			this.renderTerminal(false);
		}

		renderPrepared() {
			this.root.innerHTML = `
				<main class="cbt-entry">
					<section class="cbt-entry-card">
						<div class="cbt-mark">E</div>
						<p class="cbt-eyebrow">EduEdge Offline-Resilient CBT</p>
						<h1>Ready to begin</h1>
						<p class="cbt-candidate-name"></p>
						<div class="cbt-entry-checks">
							<div><strong>Browser storage</strong><span>Available</span></div>
							<div><strong>Connection</strong><span class="cbt-entry-connection"></span></div>
							<div><strong>Session protection</strong><span>Active</span></div>
						</div>
						<p class="cbt-entry-note">Your timer starts only after you press Start Examination. Answers are saved in this browser first and synchronised automatically.</p>
						<button type="button" class="cbt-button cbt-button-primary cbt-start-button">Start Examination</button>
						<p class="cbt-inline-status" aria-live="polite"></p>
					</section>
				</main>`;
			this.root.querySelector(".cbt-candidate-name").textContent = this.serverState.candidate_name || "Candidate";
			this.updatePreparedConnection();
			this.root.querySelector(".cbt-start-button").addEventListener("click", () => this.startAttempt());
		}

		async startAttempt() {
			const button = this.root.querySelector(".cbt-start-button");
			const status = this.root.querySelector(".cbt-inline-status");
			button.disabled = true;
			status.textContent = "Starting examination…";
			try {
				const state = await apiCall(API.start, {
					attempt_name: this.launch.attempt,
					launch_token: this.launch.token,
					client_session_id: this.clientSession,
				});
				this.setConnection("online");
				await this.applyServerState(state, false);
			} catch (error) {
				button.disabled = false;
				status.textContent = error.message || String(error);
			}
		}

		renderExam() {
			this.root.innerHTML = `
				<div class="cbt-shell">
					<header class="cbt-header">
						<div class="cbt-brand"><span class="cbt-mark cbt-mark-small">E</span><div><strong>EduEdge CBT</strong><span class="cbt-candidate"></span></div></div>
						<div class="cbt-runtime-status">
							<span class="cbt-connection-badge"></span>
							<span class="cbt-sync-badge" aria-live="polite"></span>
							<strong class="cbt-timer" aria-label="Time remaining">00:00</strong>
						</div>
					</header>
					<div class="cbt-notice" hidden role="status"></div>
					<div class="cbt-workspace">
						<aside class="cbt-palette" aria-label="Question navigation">
							<div class="cbt-palette-heading"><strong>Questions</strong><span class="cbt-progress-text"></span></div>
							<div class="cbt-question-grid"></div>
							<div class="cbt-palette-legend"><span><i class="answered"></i>Answered</span><span><i class="pending"></i>Pending sync</span></div>
						</aside>
						<main class="cbt-question-panel">
							<div class="cbt-question-meta"></div>
							<article class="cbt-question-text"></article>
							<div class="cbt-answer-area"></div>
						</main>
					</div>
					<footer class="cbt-footer">
						<button type="button" class="cbt-button cbt-button-secondary cbt-previous">Previous</button>
						<div class="cbt-footer-status" aria-live="polite"></div>
						<div class="cbt-footer-actions"><button type="button" class="cbt-button cbt-button-secondary cbt-next">Next</button><button type="button" class="cbt-button cbt-button-danger cbt-submit">Submit Examination</button></div>
					</footer>
				</div>`;
			this.root.querySelector(".cbt-candidate").textContent = this.serverState.candidate_name || "Candidate";
			this.root.querySelector(".cbt-previous").addEventListener("click", () => this.navigate(-1));
			this.root.querySelector(".cbt-next").addEventListener("click", () => this.navigate(1));
			this.root.querySelector(".cbt-submit").addEventListener("click", () => this.requestSubmission());
			this.renderPalette();
			this.renderCurrentQuestion();
			this.updateConnectionUI();
			this.updatePendingUI();
			this.updateTimerUI();
			if (this.submissionRequested) {
				this.locallyLocked = true;
				this.showNotice("Submission is saved in this browser and will complete after pending answers synchronise.", "warning");
			}
		}

		renderPalette() {
			const grid = this.root.querySelector(".cbt-question-grid");
			if (!grid) return;
			grid.innerHTML = "";
			this.questions.forEach((question, index) => {
				const row = this.answers.get(question.snapshot_key);
				const pending = row && Number(row.client_revision || 0) > Number(row.synced_revision || 0);
				const button = document.createElement("button");
				button.type = "button";
				button.textContent = String(index + 1);
				button.className = "cbt-question-number";
				if (index === this.currentIndex) button.classList.add("current");
				if (answerIsFilled(row?.answer)) button.classList.add("answered");
				if (pending) button.classList.add("pending");
				const forwardOnly = this.serverState.navigation_policy === "Forward Only";
				button.disabled = forwardOnly && index !== this.currentIndex && index !== this.currentIndex + 1;
				button.setAttribute("aria-label", `Question ${index + 1}`);
				button.addEventListener("click", () => this.goToQuestion(index));
				grid.appendChild(button);
			});
			const answered = this.questions.filter((question) => answerIsFilled(this.answers.get(question.snapshot_key)?.answer)).length;
			const progress = this.root.querySelector(".cbt-progress-text");
			if (progress) progress.textContent = `${answered}/${this.questions.length} answered`;
		}

		renderCurrentQuestion() {
			const question = this.questions[this.currentIndex];
			if (!question) {
				this.renderFatal("This attempt does not contain any candidate questions.");
				return;
			}
			const row = this.answers.get(question.snapshot_key);
			const meta = this.root.querySelector(".cbt-question-meta");
			meta.innerHTML = "";
			const heading = document.createElement("div");
			heading.innerHTML = `<span>Question ${this.currentIndex + 1} of ${this.questions.length}</span><strong>${Number(question.mark || 0)} mark${Number(question.mark || 0) === 1 ? "" : "s"}</strong>`;
			meta.appendChild(heading);
			if (question.section_label || question.topic) {
				const context = document.createElement("p");
				context.textContent = [question.section_label, question.topic].filter(Boolean).join(" · ");
				meta.appendChild(context);
			}
			this.root.querySelector(".cbt-question-text").innerHTML = sanitizeRichText(question.question_text);
			const answerArea = this.root.querySelector(".cbt-answer-area");
			answerArea.innerHTML = "";
			this.renderAnswerControl(question, row?.answer || {}, answerArea);
			const previous = this.root.querySelector(".cbt-previous");
			const next = this.root.querySelector(".cbt-next");
			previous.disabled = this.currentIndex === 0 || this.serverState.navigation_policy === "Forward Only";
			next.disabled = this.currentIndex >= this.questions.length - 1;
			this.updateFooterStatus();
		}

		renderAnswerControl(question, answer, container) {
			const disabled = this.locallyLocked || this.submissionRequested;
			if (["Single Choice", "True/False", "Yes/No", "Multiple Choice"].includes(question.question_type)) {
				const multiple = question.question_type === "Multiple Choice";
				const selected = new Set(answer.selected_option_ids || []);
				for (const option of question.options || []) {
					const label = document.createElement("label");
					label.className = "cbt-option";
					if (selected.has(option.id)) label.classList.add("selected");
					const input = document.createElement("input");
					input.type = multiple ? "checkbox" : "radio";
					input.name = `answer-${question.snapshot_key}`;
					input.value = option.id;
					input.checked = selected.has(option.id);
					input.disabled = disabled;
					input.addEventListener("change", async () => {
						let values;
						if (multiple) {
							values = Array.from(container.querySelectorAll("input:checked")).map((item) => item.value);
						} else {
							values = [input.value];
						}
						await this.saveAnswer(question.snapshot_key, { selected_option_ids: values });
						this.renderCurrentQuestion();
						this.renderPalette();
					});
					const marker = document.createElement("span");
					marker.className = "cbt-option-marker";
					marker.textContent = option.label || "";
					const text = document.createElement("span");
					text.className = "cbt-option-text";
					text.textContent = option.text || "";
					label.append(input, marker, text);
					container.appendChild(label);
				}
				return;
			}
			if (["Short Answer", "Essay"].includes(question.question_type)) {
				const textarea = document.createElement("textarea");
				textarea.className = "cbt-text-answer";
				textarea.rows = question.question_type === "Essay" ? 12 : 5;
				textarea.placeholder = question.question_type === "Essay" ? "Type your essay response…" : "Type your answer…";
				textarea.value = answer.text || "";
				textarea.disabled = disabled;
				let timer = null;
				textarea.addEventListener("input", () => {
					window.clearTimeout(timer);
					timer = window.setTimeout(() => this.saveAnswer(question.snapshot_key, { text: textarea.value }), 350);
				});
				textarea.addEventListener("blur", () => this.saveAnswer(question.snapshot_key, { text: textarea.value }));
				container.appendChild(textarea);
				return;
			}
			if (question.question_type === "Numeric") {
				const input = document.createElement("input");
				input.type = "number";
				input.inputMode = "decimal";
				input.className = "cbt-numeric-answer";
				input.placeholder = "Enter a number";
				input.value = answer.value ?? "";
				input.disabled = disabled;
				input.addEventListener("change", () => this.saveAnswer(question.snapshot_key, { value: input.value }));
				input.addEventListener("blur", () => this.saveAnswer(question.snapshot_key, { value: input.value }));
				container.appendChild(input);
			}
		}

		async saveAnswer(questionKey, answer) {
			if (this.locallyLocked || this.submissionRequested || this.secondsRemaining() <= 0) return;
			const current = this.answers.get(questionKey) || {};
			const revision = Math.max(Number(current.client_revision || 0), Number(current.synced_revision || 0)) + 1;
			const row = {
				question_snapshot_key: questionKey,
				answer,
				client_revision: revision,
				synced_revision: Number(current.synced_revision || 0),
				client_saved_at: this.serverNowString(),
				server_saved_at: current.server_saved_at || null,
			};
			await this.storage.putAnswer(row);
			this.answers.set(questionKey, { ...current, ...row });
			await this.reloadLocalAnswers();
			this.updateFooterStatus("Saved in this browser");
			this.queueSync();
		}

		navigate(direction) {
			this.goToQuestion(this.currentIndex + direction);
		}

		async goToQuestion(index) {
			if (index < 0 || index >= this.questions.length) return;
			if (this.serverState.navigation_policy === "Forward Only" && index < this.currentIndex) return;
			if (this.serverState.navigation_policy === "Forward Only" && index > this.currentIndex + 1) return;
			this.currentIndex = index;
			await this.storage.setMeta("current_question", index);
			this.renderPalette();
			this.renderCurrentQuestion();
			window.scrollTo({ top: 0, behavior: "smooth" });
		}

		queueSync(delay = SYNC_DEBOUNCE_MS) {
			window.clearTimeout(this.syncTimer);
			this.syncTimer = window.setTimeout(() => this.flushSync(), delay);
		}

		async createBatchIfNeeded() {
			let batch = await this.storage.getActiveBatch();
			if (batch) return batch;
			const pending = await this.storage.pendingAnswers();
			if (!pending.length) return null;
			batch = {
				idempotency_key: `${this.clientSession}:${Date.now()}:${randomId()}`,
				created_at: this.serverNowString(),
				answers: pending.map((row) => ({
					question_snapshot_key: row.question_snapshot_key,
					client_revision: Number(row.client_revision || 0),
					client_saved_at: row.client_saved_at,
					answer: row.answer || {},
				})),
			};
			await this.storage.putActiveBatch(batch);
			return batch;
		}

		async pendingAfterBatch(batch) {
			const current = await this.storage.pendingAnswers();
			const sent = new Map((batch.answers || []).map((row) => [row.question_snapshot_key, Number(row.client_revision || 0)]));
			return current.filter((row) => Number(row.client_revision || 0) > Number(sent.get(row.question_snapshot_key) || 0)).length;
		}

		async flushSync() {
			if (this.syncing) return this.syncPromise;
			if (!navigator.onLine) {
				this.setConnection("offline");
				return false;
			}
			this.syncing = true;
			this.syncPromise = (async () => {
				this.updatePendingUI();
				try {
					let loops = 0;
					while (loops < 10) {
						loops += 1;
						const batch = await this.createBatchIfNeeded();
						if (!batch) break;
						const remaining = await this.pendingAfterBatch(batch);
						const result = await apiCall(API.sync, {
							attempt_name: this.launch.attempt,
							launch_token: this.launch.token,
							client_session_id: this.clientSession,
							idempotency_key: batch.idempotency_key,
							answers: batch.answers,
							client_saved_at: batch.created_at,
							reported_pending_count: remaining,
						});
						if (result.status === "Conflict") {
							this.showNotice("EduEdge detected an answer revision conflict. Stop and contact the invigilator.", "danger");
							return false;
						}
						await this.storage.markBatchSynced(batch);
						this.updateServerClock(result.server_time);
						await this.reloadLocalAnswers();
						this.setConnection("online");
					}
					if (this.submissionRequested && this.pendingCount === 0) await this.completeQueuedSubmission();
					return true;
				} catch (error) {
					this.setConnection(navigator.onLine ? "degraded" : "offline");
					this.updateFooterStatus("Saved in browser; waiting to synchronise");
					return false;
				} finally {
					this.syncing = false;
					this.syncPromise = null;
					this.updatePendingUI();
				}
			})();
			return this.syncPromise;
		}

		async requestSubmission() {
			if (this.submissionRequested) return;
			const unanswered = this.questions.filter((question) => !answerIsFilled(this.answers.get(question.snapshot_key)?.answer)).length;
			const warning = unanswered
				? `You still have ${unanswered} unanswered question${unanswered === 1 ? "" : "s"}. Submit now?`
				: "Submit your examination now? You will not be able to change answers afterwards.";
			if (!window.confirm(warning)) return;
			this.submissionRequested = true;
			this.locallyLocked = true;
			await this.storage.setMeta("submission_requested", true);
			this.renderCurrentQuestion();
			this.showNotice("Submission saved in this browser. EduEdge is synchronising your remaining answers.", "warning");
			if (navigator.onLine) {
				await this.flushSync();
				if (this.pendingCount === 0) await this.completeQueuedSubmission();
			} else {
				this.updateFooterStatus("Submission waiting for connection");
			}
		}

		async completeQueuedSubmission() {
			if (!this.submissionRequested) return;
			try {
				const result = await apiCall(API.submit, {
					attempt_name: this.launch.attempt,
					launch_token: this.launch.token,
					client_session_id: this.clientSession,
					reported_pending_count: this.pendingCount,
				});
				this.updateServerClock(result.server_time);
				this.serverState.status = result.status;
				await this.storage.setMeta("submission_requested", false);
				this.submissionRequested = false;
				await this.refreshState();
			} catch (error) {
				this.setConnection(navigator.onLine ? "degraded" : "offline");
				this.updateFooterStatus("Submission saved locally; retrying automatically");
			}
		}

		async refreshState() {
			try {
				const state = await apiCall(API.state, {
					attempt_name: this.launch.attempt,
					launch_token: this.launch.token,
					client_session_id: this.clientSession,
				});
				this.setConnection("online");
				await this.applyServerState(state, false);
			} catch (error) {
				this.setConnection(navigator.onLine ? "degraded" : "offline");
			}
		}

		async heartbeat() {
			if (!navigator.onLine || !this.serverState || this.serverState.status === "Prepared") return;
			try {
				const result = await apiCall(API.heartbeat, {
					attempt_name: this.launch.attempt,
					launch_token: this.launch.token,
					client_session_id: this.clientSession,
					reported_pending_count: this.pendingCount,
				});
				this.updateServerClock(result.server_time);
				this.setConnection("online");
				if (Number.isFinite(Number(result.seconds_remaining))) this.setTimer(Number(result.seconds_remaining));
				if (result.status !== this.serverState.status) await this.refreshState();
			} catch (error) {
				this.setConnection(navigator.onLine ? "degraded" : "offline");
			}
		}

		async handleLocalTimeout() {
			if (this.localTimeoutHandled || this.serverState?.status !== "In Progress") return;
			this.localTimeoutHandled = true;
			this.submissionRequested = true;
			this.locallyLocked = true;
			await this.storage.setMeta("submission_requested", true);
			this.renderCurrentQuestion();
			this.showNotice("Time has ended. Answers saved before the deadline are locked and will synchronise automatically.", "warning");
			if (navigator.onLine) {
				await this.heartbeat();
				await this.flushSync();
				await this.refreshState();
			}
		}

		renderTerminal(syncPending) {
			const status = this.serverState?.status || "Closed";
			this.root.innerHTML = `
				<main class="cbt-entry">
					<section class="cbt-entry-card cbt-terminal-card">
						<div class="cbt-mark">E</div>
						<p class="cbt-eyebrow">EduEdge CBT</p>
						<h1></h1>
						<p class="cbt-terminal-message"></p>
						<div class="cbt-entry-checks">
							<div><strong>Status</strong><span class="cbt-terminal-status"></span></div>
							<div><strong>Browser pending</strong><span class="cbt-terminal-pending"></span></div>
							<div><strong>Connection</strong><span class="cbt-entry-connection"></span></div>
						</div>
						<button type="button" class="cbt-button cbt-button-secondary cbt-retry-sync" ${syncPending ? "" : "hidden"}>Retry Synchronisation</button>
					</section>
				</main>`;
			this.root.querySelector("h1").textContent = syncPending ? "Submission awaiting synchronisation" : "Examination received";
			this.root.querySelector(".cbt-terminal-message").textContent = syncPending
				? "Your submission is recorded, but some browser-saved answers still need to reach the server. Keep this page open or reconnect this browser."
				: "Your answers are locked. You may close this page when instructed by the invigilator.";
			this.root.querySelector(".cbt-terminal-status").textContent = status;
			this.root.querySelector(".cbt-terminal-pending").textContent = String(this.pendingCount);
			this.updatePreparedConnection();
			const retry = this.root.querySelector(".cbt-retry-sync");
			if (retry) retry.addEventListener("click", async () => {
				retry.disabled = true;
				await this.flushSync();
				await this.refreshState();
				retry.disabled = false;
			});
		}

		showNotice(message, tone = "info") {
			const notice = this.root.querySelector(".cbt-notice");
			if (!notice) return;
			notice.hidden = !message;
			notice.className = `cbt-notice ${tone ? `cbt-notice-${tone}` : ""}`;
			notice.textContent = message || "";
		}

		updatePreparedConnection() {
			const element = this.root.querySelector(".cbt-entry-connection");
			if (element) element.textContent = this.connectionLabel();
		}

		connectionLabel() {
			if (this.connectionState === "online") return "Online";
			if (this.connectionState === "checking") return "Checking";
			if (this.connectionState === "degraded") return "Unstable";
			return "Offline";
		}

		updateConnectionUI() {
			this.updatePreparedConnection();
			const badge = this.root.querySelector(".cbt-connection-badge");
			if (!badge) return;
			badge.className = `cbt-connection-badge ${this.connectionState}`;
			badge.textContent = this.connectionLabel();
		}

		updatePendingUI() {
			const badge = this.root.querySelector(".cbt-sync-badge");
			if (badge) {
				badge.className = `cbt-sync-badge ${this.pendingCount ? "pending" : "synced"}`;
				badge.textContent = this.syncing
					? "Synchronising…"
					: this.pendingCount
						? `${this.pendingCount} pending`
						: "All answers synced";
			}
			const terminal = this.root.querySelector(".cbt-terminal-pending");
			if (terminal) terminal.textContent = String(this.pendingCount);
			this.renderPalette();
			this.updateFooterStatus();
		}

		updateFooterStatus(message = "") {
			const footer = this.root.querySelector(".cbt-footer-status");
			if (!footer) return;
			if (message) {
				footer.textContent = message;
				return;
			}
			footer.textContent = this.pendingCount
				? `${this.pendingCount} answer${this.pendingCount === 1 ? "" : "s"} saved in browser, awaiting sync`
				: "Answers are saved automatically";
		}

		updateTimerUI() {
			const timer = this.root.querySelector(".cbt-timer");
			const remaining = this.secondsRemaining();
			if (timer) {
				timer.textContent = formatDuration(remaining);
				timer.classList.toggle("warning", remaining <= 300 && remaining > 60);
				timer.classList.toggle("danger", remaining <= 60);
			}
			if (remaining <= 0) this.handleLocalTimeout();
		}

		startBackgroundWork() {
			window.clearInterval(this.timerInterval);
			window.clearInterval(this.periodicSyncInterval);
			window.clearInterval(this.heartbeatInterval);
			this.timerInterval = window.setInterval(() => this.updateTimerUI(), 1000);
			this.periodicSyncInterval = window.setInterval(() => this.flushSync(), PERIODIC_SYNC_MS);
			this.heartbeatInterval = window.setInterval(() => this.heartbeat(), HEARTBEAT_MS);
		}

		installLifecycleHandlers() {
			window.addEventListener("online", async () => {
				this.setConnection("checking");
				await this.flushSync();
				await this.refreshState();
			});
			window.addEventListener("offline", () => this.setConnection("offline"));
			document.addEventListener("visibilitychange", () => {
				if (!document.hidden) {
					this.flushSync();
					this.heartbeat();
				}
			});
			window.addEventListener("beforeunload", (event) => {
				if (this.serverState?.status === "In Progress" || this.pendingCount || this.submissionRequested) {
					event.preventDefault();
					event.returnValue = "";
				}
			});
		}
	}

	async function boot() {
		const root = document.getElementById("eduedge-cbt-candidate-root");
		if (!root) return;
		const runtime = new CandidateRuntime(root);
		window.EduEdgeCBTCandidateRuntime = runtime;
		await runtime.init();
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", boot, { once: true });
	} else {
		boot();
	}
})();
