(() => {
	"use strict";

	const DB_NAME = "eduedge-cbt-runtime";
	const DB_VERSION = 1;
	const ANSWERS = "answers";
	const BATCHES = "batches";
	const META = "meta";

	function requestPromise(request) {
		return new Promise((resolve, reject) => {
			request.onsuccess = () => resolve(request.result);
			request.onerror = () => reject(request.error || new Error("IndexedDB request failed."));
		});
	}

	function transactionPromise(transaction) {
		return new Promise((resolve, reject) => {
			transaction.oncomplete = () => resolve();
			transaction.onerror = () => reject(transaction.error || new Error("IndexedDB transaction failed."));
			transaction.onabort = () => reject(transaction.error || new Error("IndexedDB transaction was aborted."));
		});
	}

	function openDatabase() {
		return new Promise((resolve, reject) => {
			if (!window.indexedDB) {
				reject(new Error("This browser does not provide IndexedDB storage."));
				return;
			}

			const request = window.indexedDB.open(DB_NAME, DB_VERSION);
			request.onupgradeneeded = () => {
				const database = request.result;
				if (!database.objectStoreNames.contains(ANSWERS)) {
					const answers = database.createObjectStore(ANSWERS, { keyPath: "id" });
					answers.createIndex("attempt", "attempt", { unique: false });
				}
				if (!database.objectStoreNames.contains(BATCHES)) {
					const batches = database.createObjectStore(BATCHES, { keyPath: "id" });
					batches.createIndex("attempt", "attempt", { unique: false });
				}
				if (!database.objectStoreNames.contains(META)) {
					database.createObjectStore(META, { keyPath: "id" });
				}
			};
			request.onsuccess = () => resolve(request.result);
			request.onerror = () => reject(request.error || new Error("Unable to open browser answer storage."));
			request.onblocked = () => reject(new Error("Browser answer storage is blocked by another open EduEdge CBT tab."));
		});
	}

	class AttemptStorage {
		constructor(database, attempt) {
			this.database = database;
			this.attempt = attempt;
		}

		answerId(questionKey) {
			return `${this.attempt}::${questionKey}`;
		}

		metaId(key) {
			return `${this.attempt}::${key}`;
		}

		batchId() {
			return `${this.attempt}::active-sync-batch`;
		}

		async getAnswer(questionKey) {
			const transaction = this.database.transaction(ANSWERS, "readonly");
			return requestPromise(transaction.objectStore(ANSWERS).get(this.answerId(questionKey)));
		}

		async putAnswer(row) {
			const transaction = this.database.transaction(ANSWERS, "readwrite");
			transaction.objectStore(ANSWERS).put({
				...row,
				id: this.answerId(row.question_snapshot_key),
				attempt: this.attempt,
			});
			await transactionPromise(transaction);
		}

		async listAnswers() {
			const transaction = this.database.transaction(ANSWERS, "readonly");
			const index = transaction.objectStore(ANSWERS).index("attempt");
			return requestPromise(index.getAll(this.attempt));
		}

		async seedServerAnswers(serverAnswers = {}) {
			const transaction = this.database.transaction(ANSWERS, "readwrite");
			const store = transaction.objectStore(ANSWERS);
			for (const [questionKey, serverRow] of Object.entries(serverAnswers || {})) {
				const id = this.answerId(questionKey);
				const local = await requestPromise(store.get(id));
				const serverRevision = Number(serverRow.client_revision || 0);
				if (local && Number(local.client_revision || 0) > serverRevision) continue;
				store.put({
					id,
					attempt: this.attempt,
					question_snapshot_key: questionKey,
					answer: serverRow.answer || {},
					client_revision: serverRevision,
					synced_revision: serverRevision,
					client_saved_at: serverRow.client_saved_at || null,
					server_saved_at: serverRow.server_saved_at || null,
				});
			}
			await transactionPromise(transaction);
		}

		async pendingAnswers() {
			const rows = await this.listAnswers();
			return rows.filter(
				(row) => Number(row.client_revision || 0) > Number(row.synced_revision || 0)
			);
		}

		async markBatchSynced(batch) {
			const transaction = this.database.transaction([ANSWERS, BATCHES], "readwrite");
			const answerStore = transaction.objectStore(ANSWERS);
			for (const sent of batch.answers || []) {
				const id = this.answerId(sent.question_snapshot_key);
				const current = await requestPromise(answerStore.get(id));
				if (!current) continue;
				current.synced_revision = Math.max(
					Number(current.synced_revision || 0),
					Number(sent.client_revision || 0)
				);
				answerStore.put(current);
			}
			transaction.objectStore(BATCHES).delete(this.batchId());
			await transactionPromise(transaction);
		}

		async getActiveBatch() {
			const transaction = this.database.transaction(BATCHES, "readonly");
			return requestPromise(transaction.objectStore(BATCHES).get(this.batchId()));
		}

		async putActiveBatch(batch) {
			const transaction = this.database.transaction(BATCHES, "readwrite");
			transaction.objectStore(BATCHES).put({
				...batch,
				id: this.batchId(),
				attempt: this.attempt,
			});
			await transactionPromise(transaction);
		}

		async clearActiveBatch() {
			const transaction = this.database.transaction(BATCHES, "readwrite");
			transaction.objectStore(BATCHES).delete(this.batchId());
			await transactionPromise(transaction);
		}

		async getMeta(key, fallback = null) {
			const transaction = this.database.transaction(META, "readonly");
			const row = await requestPromise(transaction.objectStore(META).get(this.metaId(key)));
			return row ? row.value : fallback;
		}

		async setMeta(key, value) {
			const transaction = this.database.transaction(META, "readwrite");
			transaction.objectStore(META).put({ id: this.metaId(key), attempt: this.attempt, value });
			await transactionPromise(transaction);
		}

		async removeMeta(key) {
			const transaction = this.database.transaction(META, "readwrite");
			transaction.objectStore(META).delete(this.metaId(key));
			await transactionPromise(transaction);
		}

		close() {
			this.database.close();
		}
	}

	async function openAttemptStorage(attempt) {
		if (!attempt) throw new Error("Attempt reference is required for browser storage.");
		const database = await openDatabase();
		return new AttemptStorage(database, attempt);
	}

	window.EduEdgeCBTRuntimeStorage = Object.freeze({
		open: openAttemptStorage,
		databaseName: DB_NAME,
		version: DB_VERSION,
	});
})();
