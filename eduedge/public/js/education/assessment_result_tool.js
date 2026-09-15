frappe.ui.form.on("Assessment Result Tool", {
	refresh(frm) {
		install_eduedge_mark_entry_observer(frm);
	},
	assessment_plan(frm) {
		install_eduedge_mark_entry_observer(frm);
	},
});

function install_eduedge_mark_entry_observer(frm) {
	const wrapper = frm.fields_dict?.result_html?.wrapper;
	if (!wrapper || wrapper.dataset.eduedgeObserverInstalled) return;
	wrapper.dataset.eduedgeObserverInstalled = "1";

	const enhance = () => {
		const table = wrapper.querySelector("table.assessment-result-tool");
		if (!table || table.dataset.eduedgeEnhanced) return;
		table.dataset.eduedgeEnhanced = "1";
		setup_eduedge_mark_entry(frm, table);
	};

	new MutationObserver(enhance).observe(wrapper, { childList: true, subtree: true });
	setTimeout(enhance, 0);
}

async function setup_eduedge_mark_entry(frm, table) {
	if (!frm.doc.assessment_plan) return;

	const $table = $(table);
	$table.off("change", "input");

	const response = await frappe.call("eduedge.api.mark_entry.get_mark_entry_context", {
		assessment_plan: frm.doc.assessment_plan,
	});
	const context = response.message || {};
	const criteria = context.criteria || [];
	const resultState = context.results || {};
	const debounceTimers = new Map();
	const draftStorageKey = `eduedge:mark-entry:v1:${frappe.session.user}:${frm.doc.assessment_plan}`;
	let browserDrafts = readBrowserDrafts(draftStorageKey);

	add_eduedge_toolbar(frm, table, context);
	add_score_state_column(table, resultState);

	const rowForStudent = (student) =>
		table.querySelector(`tbody tr[data-student="${CSS.escape(student)}"]`);

	const collectRow = (row) => {
		const student = row.dataset.student;
		const stateSelect = row.querySelector(".eduedge-score-state");
		const score_state = stateSelect?.value || "Scored";
		const assessment_details = {};
		row.querySelectorAll("input.student-result-data").forEach((input) => {
			assessment_details[input.dataset.criteria] = input.value;
		});
		return {
			student,
			score_state,
			comment: row.querySelector(".result-comment")?.value || "",
			assessment_details,
		};
	};

	const persistBrowserRow = (row) => {
		if (!row || row.classList.contains("text-muted")) return;
		const payload = collectRow(row);
		browserDrafts[payload.student] = { ...payload, updated_at: new Date().toISOString() };
		writeBrowserDrafts(draftStorageKey, browserDrafts);
	};

	const clearBrowserRow = (student) => {
		if (!browserDrafts[student]) return;
		delete browserDrafts[student];
		writeBrowserDrafts(draftStorageKey, browserDrafts);
	};

	const rowReadyForServer = (row) => {
		const state = row.querySelector(".eduedge-score-state")?.value || "Scored";
		if (state !== "Scored") return true;
		return [...row.querySelectorAll("input.student-result-data")]
			.every((input) => String(input.value ?? "").trim() !== "");
	};

	const updateTotal = (row) => {
		const state = row.querySelector(".eduedge-score-state")?.value || "Scored";
		let total = 0;
		if (state === "Scored") {
			row.querySelectorAll("input.student-result-data").forEach((input) => {
				const value = Number(input.value);
				if (Number.isFinite(value)) total += value;
			});
		}
		const totalEl = row.querySelector(".total-score");
		if (totalEl) totalEl.textContent = total;
	};

	const saveRows = async (rows) => {
		const editable = rows.filter((row) => !row.classList.contains("text-muted"));
		if (!editable.length) return;
		const ready = editable.filter(rowReadyForServer);
		editable.forEach(persistBrowserRow);
		if (!ready.length) {
			set_autosave_status(table, navigator.onLine ? "Browser draft saved · complete the row to sync" : "Offline · browser draft saved");
			return;
		}
		const payload = ready.map(collectRow);
		try {
			const result = await frappe.call({
				method: "eduedge.api.mark_entry.save_mark_entry_batch",
				type: "POST",
				args: {
					assessment_plan: frm.doc.assessment_plan,
					rows: payload,
				},
				freeze: false,
			});
			(result.message?.saved || []).forEach((saved) => {
				clearBrowserRow(saved.student);
				const row = rowForStudent(saved.student);
				if (!row) return;
				row.classList.remove("eduedge-save-error");
				row.classList.add("eduedge-saved");
				const grade = row.querySelector(".total-score-grade");
				if (grade) grade.textContent = saved.grade || "";
				const link = row.querySelector(".total-result-link");
				if (link && saved.name) {
					link.style.display = "block";
					const anchor = link.querySelector("a");
					if (anchor) anchor.href = `/app/assessment-result/${saved.name}`;
				}
				setTimeout(() => row.classList.remove("eduedge-saved"), 900);
			});
			frm.doc.show_submit = true;
			if (frm.events?.submit_result) frm.events.submit_result(frm);
			set_autosave_status(table, "Saved");
		} catch (error) {
			editable.forEach((row) => row.classList.add("eduedge-save-error"));
			set_autosave_status(table, "Save failed");
			frappe.msgprint({
				title: __("Mark entry could not be saved"),
				message: error?.message || __("Review the highlighted rows and try again."),
				indicator: "red",
			});
		}
	};

	const scheduleRowSave = (row) => {
		if (!row || row.classList.contains("text-muted")) return;
		const student = row.dataset.student;
		clearTimeout(debounceTimers.get(student));
		persistBrowserRow(row);
		if (!rowReadyForServer(row)) {
			set_autosave_status(table, navigator.onLine ? "Browser draft saved · complete the row to sync" : "Offline · browser draft saved");
			return;
		}
		set_autosave_status(table, navigator.onLine ? "Saving…" : "Offline · browser draft saved");
		if (!navigator.onLine) return;
		debounceTimers.set(
			student,
			setTimeout(() => saveRows([row]), 650)
		);
	};

	table.querySelectorAll("tbody tr[data-student]").forEach((row) => {
		restoreBrowserDraft(row, browserDrafts[row.dataset.student]);
		apply_score_state(row);
		updateTotal(row);
		row.querySelectorAll("input.student-result-data, input.result-comment").forEach((input) => {
			input.addEventListener("input", () => {
				updateTotal(row);
				scheduleRowSave(row);
			});
		});
		row.querySelector(".eduedge-score-state")?.addEventListener("change", () => {
			apply_score_state(row);
			updateTotal(row);
			scheduleRowSave(row);
		});
	});

	$table.on("paste.eduedge", "input.student-result-data", (event) => {
		const text = event.originalEvent?.clipboardData?.getData("text/plain");
		if (!text || (!text.includes("\t") && !text.includes("\n"))) return;
		event.preventDefault();
		const startInput = event.currentTarget;
		const startRow = startInput.closest("tr[data-student]");
		const rows = [...table.querySelectorAll("tbody tr[data-student]")];
		const rowIndex = rows.indexOf(startRow);
		const inputs = [...startRow.querySelectorAll("input.student-result-data")];
		const colIndex = inputs.indexOf(startInput);
		const pasted = text.trimEnd().split(/\r?\n/).map((line) => line.split("\t"));
		const touched = new Set();

		pasted.forEach((cells, rOffset) => {
			const row = rows[rowIndex + rOffset];
			if (!row || row.classList.contains("text-muted")) return;
			const state = row.querySelector(".eduedge-score-state");
			if (state && state.value !== "Scored") return;
			const rowInputs = [...row.querySelectorAll("input.student-result-data")];
			cells.forEach((cell, cOffset) => {
				const input = rowInputs[colIndex + cOffset];
				if (!input || input.disabled) return;
				const number = Number(cell.trim());
				if (!Number.isFinite(number)) return;
				const max = Number(input.dataset.maxScore || 0);
				input.value = Math.min(Math.max(number, 0), max);
				touched.add(row);
			});
			updateTotal(row);
		});

		if (touched.size) {
			[...touched].forEach(persistBrowserRow);
			set_autosave_status(table, navigator.onLine ? `Pasted ${touched.size} row(s) · syncing complete rows…` : `Pasted ${touched.size} row(s) · offline browser draft saved`);
			if (navigator.onLine) saveRows([...touched]);
		}
	});

	table.dataset.eduedgeSaveAll = "1";
	table.eduedgeSaveAll = () =>
		saveRows([...table.querySelectorAll("tbody tr[data-student]")]);
}

function add_eduedge_toolbar(frm, table, context) {
	if (table.previousElementSibling?.classList.contains("eduedge-mark-entry-toolbar")) return;
	const bar = document.createElement("div");
	bar.className = "eduedge-mark-entry-toolbar";
	bar.innerHTML = `
		<div>
			<strong>${__("Smart Mark Entry")}</strong>
			<span>${__("Paste spreadsheet cells directly into score columns. Draft rows autosave.")}</span>
		</div>
		<div class="eduedge-mark-entry-actions">
			<span class="eduedge-autosave-status">${__("Ready")}</span>
			<button type="button" class="btn btn-default btn-sm eduedge-save-all">${__("Save all drafts")}</button>
		</div>
	`;
	table.parentElement.insertBefore(bar, table);
	bar.querySelector(".eduedge-save-all").addEventListener("click", () => {
		table.eduedgeSaveAll?.();
	});
}

function add_score_state_column(table, resultState) {
	const headerRows = table.querySelectorAll("thead tr");
	if (headerRows.length < 2) return;
	const first = document.createElement("th");
	first.rowSpan = 2;
	first.className = "eduedge-state-heading";
	first.textContent = __("Status");
	const comments = [...headerRows[0].children].find((cell) => cell.textContent.trim() === "Comments");
	headerRows[0].insertBefore(first, comments || headerRows[0].lastElementChild);

	table.querySelectorAll("tbody tr[data-student]").forEach((row) => {
		const student = row.dataset.student;
		const submitted = row.classList.contains("text-muted");
		const state = resultState[student]?.score_state || "Scored";
		const cell = document.createElement("td");
		cell.className = "eduedge-score-state-cell";
		cell.innerHTML = `
			<select class="form-control eduedge-score-state" ${submitted ? "disabled" : ""}>
				<option value="Scored">Scored</option>
				<option value="Absent">Absent</option>
				<option value="Exempt">Exempt</option>
				<option value="Not Offered">Not Offered</option>
			</select>
		`;
		cell.querySelector("select").value = state;
		const commentCell = row.querySelector(".result-comment")?.closest("td");
		row.insertBefore(cell, commentCell || row.lastElementChild);
	});
}

function apply_score_state(row) {
	const state = row.querySelector(".eduedge-score-state")?.value || "Scored";
	const locked = row.classList.contains("text-muted");
	row.querySelectorAll("input.student-result-data").forEach((input) => {
		input.disabled = locked || state !== "Scored";
		if (state !== "Scored") input.value = 0;
	});
	row.dataset.scoreState = state;
}

function readBrowserDrafts(key) {
	try {
		const value = JSON.parse(localStorage.getItem(key) || "{}");
		return value && typeof value === "object" ? value : {};
	} catch (_error) {
		return {};
	}
}

function writeBrowserDrafts(key, value) {
	try {
		if (Object.keys(value || {}).length) localStorage.setItem(key, JSON.stringify(value));
		else localStorage.removeItem(key);
	} catch (_error) {
		// Server validation remains authoritative even when browser storage is unavailable.
	}
}

function restoreBrowserDraft(row, draft) {
	if (!draft || row.classList.contains("text-muted")) return;
	const state = row.querySelector(".eduedge-score-state");
	if (state && draft.score_state) state.value = draft.score_state;
	for (const input of row.querySelectorAll("input.student-result-data")) {
		const value = draft.assessment_details?.[input.dataset.criteria];
		if (value !== undefined && value !== null) input.value = value;
	}
	const comment = row.querySelector(".result-comment");
	if (comment && draft.comment !== undefined) comment.value = draft.comment;
	row.classList.add("eduedge-browser-draft");
}

function set_autosave_status(table, text) {
	const toolbar = table.previousElementSibling;
	const status = toolbar?.querySelector(".eduedge-autosave-status");
	if (status) status.textContent = __(text);
}
