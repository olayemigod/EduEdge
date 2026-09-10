(() => {
	const COMMAND_VERSION = "1.0.0";
	const NAVIGATION_QA_STYLESHEET = "/assets/eduedge/css/eduedge_navigation_qa_fixes.css";
	const CALENDAR_DOCTYPE = "EduEdge Institution Academic Calendar";
	const CALENDAR_PERIOD_DOCTYPE = "EduEdge Academic Calendar Period";
	const CALENDAR_QUICK_ENTRY_MARKER = "__eduedgeCalendarQuickEntryAdapter";

	function calendarQuickEntryValue(entry, fieldname) {
		if (typeof entry?.get_value === "function") {
			const value = entry.get_value(fieldname);
			if (value !== undefined && value !== null) return value;
		}
		return entry?.doc?.[fieldname];
	}

	function escapeCalendarQuickEntryText(value) {
		const text = String(value || "");
		if (typeof frappe.utils?.escape_html === "function") return frappe.utils.escape_html(text);
		return $("<div>").text(text).html();
	}

	function calendarQuickEntryDate(value) {
		if (!value) return __("Not set");
		return typeof frappe.datetime?.str_to_user === "function"
			? frappe.datetime.str_to_user(value)
			: String(value);
	}

	function renderCalendarQuickEntrySummary(entry, academicYear, year, terms) {
		if (typeof entry?.set_intro !== "function") return;
		const range = `${calendarQuickEntryDate(year?.year_start_date)} – ${calendarQuickEntryDate(year?.year_end_date)}`;
		if (!terms.length) {
			entry.set_intro(
				__("{0} covers {1}. No Academic Terms are configured for this Academic Year.", [
					escapeCalendarQuickEntryText(academicYear),
					escapeCalendarQuickEntryText(range),
				]),
				"orange",
			);
			return;
		}
		const termSummary = terms
			.map((term) => `${escapeCalendarQuickEntryText(term.name)} (${calendarQuickEntryDate(term.term_start_date)} – ${calendarQuickEntryDate(term.term_end_date)})`)
			.join("<br>");
		entry.set_intro(
			`<strong>${escapeCalendarQuickEntryText(academicYear)}</strong> · ${escapeCalendarQuickEntryText(range)}<br>${termSummary}`,
			"blue",
		);
	}

	async function syncCalendarQuickEntryDefaults(entry) {
		if (!entry?.doc || entry.doctype !== CALENDAR_DOCTYPE) return;
		const academicYear = String(calendarQuickEntryValue(entry, "academic_year") || "").trim();
		const requestToken = Number(entry.__eduedgeCalendarSyncToken || 0) + 1;
		entry.__eduedgeCalendarSyncToken = requestToken;
		if (!academicYear) {
			if (typeof entry.set_intro === "function") {
				entry.set_intro(__("Select an Academic Year to load its calendar dates and Terms."), "blue");
			}
			return;
		}

		try {
			const [yearResponse, terms] = await Promise.all([
				frappe.db.get_value("Academic Year", academicYear, ["year_start_date", "year_end_date"]),
				frappe.db.get_list("Academic Term", {
					filters: { academic_year: academicYear },
					fields: ["name", "term_start_date", "term_end_date"],
					order_by: "term_start_date asc, name asc",
					limit: 0,
				}),
			]);
			if (
				entry.__eduedgeCalendarSyncToken !== requestToken
				|| String(calendarQuickEntryValue(entry, "academic_year") || "").trim() !== academicYear
			) return;

			const year = yearResponse?.message || {};
			if (typeof entry.set_value === "function") {
				await entry.set_value("start_date", year.year_start_date || "");
				await entry.set_value("end_date", year.year_end_date || "");
			} else {
				entry.doc.start_date = year.year_start_date || null;
				entry.doc.end_date = year.year_end_date || null;
			}

			frappe.model.clear_table(entry.doc, "periods");
			for (const [index, term] of terms.entries()) {
				const row = frappe.model.add_child(entry.doc, CALENDAR_PERIOD_DOCTYPE, "periods");
				row.academic_term = term.name;
				row.start_date = term.term_start_date || null;
				row.end_date = term.term_end_date || null;
				row.sequence = (index + 1) * 10;
			}
			renderCalendarQuickEntrySummary(entry, academicYear, year, terms);
		} catch (error) {
			console.error("EduEdge calendar Quick Entry autofill failed", error);
			if (typeof entry.set_intro === "function") {
				entry.set_intro(
					error?.message || __("Calendar dates and Terms could not be loaded for this Academic Year."),
					"red",
				);
			}
		}
	}

	function setupCalendarQuickEntry(entry) {
		if (
			!entry?.doc
			|| entry.doctype !== CALENDAR_DOCTYPE
			|| !entry.fields_dict
			|| entry.__eduedgeCalendarQuickEntryBound
		) return;
		entry.__eduedgeCalendarQuickEntryBound = true;
		const academicYearField = entry.fields_dict.academic_year;
		if (!academicYearField) return;

		academicYearField.$input
			?.off("change.eduedgeCalendarQuickEntry")
			.on("change.eduedgeCalendarQuickEntry", () => {
				setTimeout(() => syncCalendarQuickEntryDefaults(entry), 0);
			});
		if (calendarQuickEntryValue(entry, "academic_year")) {
			queueMicrotask(() => syncCalendarQuickEntryDefaults(entry));
		} else if (typeof entry.set_intro === "function") {
			entry.set_intro(__("Select an Academic Year to load its calendar dates and Terms."), "blue");
		}
	}

	function installCalendarQuickEntryAdapter() {
		if (window[CALENDAR_QUICK_ENTRY_MARKER]?.installed) return;
		const formApi = window.frappe?.ui?.form;
		if (typeof formApi?.make_quick_entry !== "function") return;
		const originalMakeQuickEntry = formApi.make_quick_entry;
		formApi.make_quick_entry = function (
			doctype,
			afterInsert,
			initCallback,
			doc,
			force,
			skipInsert,
		) {
			const combinedInitCallback = doctype !== CALENDAR_DOCTYPE
				? initCallback
				: (target) => {
					if (typeof initCallback === "function") initCallback(target);
					setupCalendarQuickEntry(target);
				};
			return originalMakeQuickEntry.call(
				this,
				doctype,
				afterInsert,
				combinedInitCallback,
				doc,
				force,
				skipInsert,
			);
		};
		window[CALENDAR_QUICK_ENTRY_MARKER] = {
			installed: true,
			sync: syncCalendarQuickEntryDefaults,
		};
	}

	function ensureNavigationQaStyles() {
		if (document.querySelector(`link[href="${NAVIGATION_QA_STYLESHEET}"]`)) return;
		const link = document.createElement("link");
		link.rel = "stylesheet";
		link.href = NAVIGATION_QA_STYLESHEET;
		link.dataset.eduedgeNavigationQa = "1";
		document.head.appendChild(link);
	}

	function disableGlobalFriendlyNameObserver() {
		const existing = window.__eduedgeFriendlyNameObserver;
		if (existing?.disconnect) existing.disconnect();
		window.__eduedgeFriendlyNameObserver = {
			optimized: true,
			disconnect() {},
		};
	}

	function normalizeRoute(value) {
		try {
			const path = new URL(value, window.location.origin).pathname.replace(/\/+$/, "") || "/";
			return path.startsWith("/desk/") ? `/app/${path.slice(6)}` : path;
		} catch (_error) {
			return String(value || "").split(/[?#]/, 1)[0].replace(/\/+$/, "");
		}
	}

	function installedEduEdgePageRoutes() {
		const routes = frappe.boot?.eduedge_page_routes;
		return new Set(Array.isArray(routes) ? routes.map(normalizeRoute) : []);
	}

	function hasEduEdgePageRouteAccess(route) {
		if (frappe.session?.user === "Administrator") return true;
		const normalized = normalizeRoute(route);
		if (!installedEduEdgePageRoutes().has(normalized)) return true;
		const routes = frappe.boot?.eduedge_access_manifest?.routes;
		if (!routes || !Object.prototype.hasOwnProperty.call(routes, normalized)) return false;
		return Boolean(routes[normalized]);
	}

	function notify(message, indicator = "blue") {
		if (window.frappe?.show_alert) frappe.show_alert({ message: __(message), indicator }, 4);
	}

	function showRouteDenied() {
		notify("Your current role does not provide access to this EduEdge page.", "orange");
	}

	function enforceCurrentEduEdgePage() {
		const route = normalizeRoute(window.location.pathname);
		if (!installedEduEdgePageRoutes().has(route) || hasEduEdgePageRouteAccess(route)) return;
		showRouteDenied();
		const home = "/app/eduedge-home";
		window.location.replace(hasEduEdgePageRouteAccess(home) ? home : "/app");
	}

	function onRouteClick(event) {
		const anchor = event.target instanceof Element ? event.target.closest("a[href]") : null;
		if (!anchor) return;
		let url;
		try {
			url = new URL(anchor.href, window.location.origin);
		} catch (_error) {
			return;
		}
		if (url.origin !== window.location.origin) return;
		const route = normalizeRoute(url.pathname);
		if (!installedEduEdgePageRoutes().has(route) || hasEduEdgePageRouteAccess(route)) return;
		event.preventDefault();
		event.stopPropagation();
		showRouteDenied();
	}

	function installEduEdgeRouteGuard() {
		if (window.__eduedgePageRouteGuardBound) return;
		window.__eduedgePageRouteGuardBound = true;
		document.addEventListener("click", onRouteClick, true);
		document.addEventListener("page-change", enforceCurrentEduEdgePage);
		window.addEventListener("popstate", enforceCurrentEduEdgePage);
		if (document.readyState === "loading") {
			document.addEventListener("DOMContentLoaded", enforceCurrentEduEdgePage, { once: true });
		} else {
			queueMicrotask(enforceCurrentEduEdgePage);
		}
		window.EdgeSuiteRouteGuard = {
			hasEduEdgePageRouteAccess,
			enforceCurrentEduEdgePage,
		};
	}

	ensureNavigationQaStyles();
	disableGlobalFriendlyNameObserver();
	installEduEdgeRouteGuard();
	installCalendarQuickEntryAdapter();
	if (window.EdgeSuiteCommands?.version === COMMAND_VERSION) return;

	const registry = (window.EdgeSuiteCommands = window.EdgeSuiteCommands || {});
	const saveHandlers = new Map();
	let activeSaveHandler = null;

	function isMac() {
		return /Mac|iPhone|iPad|iPod/i.test(navigator.platform || navigator.userAgent || "");
	}

	function primaryModifier(event) {
		return isMac() ? event.metaKey : event.ctrlKey;
	}

	function editingSurface(target) {
		if (!(target instanceof Element)) return false;
		return Boolean(target.closest("textarea, [contenteditable='true'], .ql-editor, .CodeMirror, .ace_editor"));
	}

	function isVisible(element) {
		return Boolean(element && !element.hidden && element.getClientRects().length && getComputedStyle(element).visibility !== "hidden");
	}

	function registerSaveHandler(key, handler) {
		if (!key || typeof handler !== "function") return () => {};
		saveHandlers.set(key, handler);
		activeSaveHandler = key;
		return () => {
			saveHandlers.delete(key);
			if (activeSaveHandler === key) activeSaveHandler = null;
		};
	}

	function activateSaveHandler(key) {
		activeSaveHandler = saveHandlers.has(key) ? key : null;
	}

	async function invokeRegisteredSave() {
		const handler = activeSaveHandler ? saveHandlers.get(activeSaveHandler) : null;
		if (!handler) return false;
		const result = await handler({ source: "keyboard", command: "save" });
		return result !== false;
	}

	async function invokeEventSave() {
		const detail = { handled: false, promise: null, source: "keyboard", command: "save" };
		window.dispatchEvent(new CustomEvent("edgesuite:save-request", { detail }));
		if (!detail.handled) return false;
		if (detail.promise && typeof detail.promise.then === "function") await detail.promise;
		return true;
	}

	function findVisibleSaveControl() {
		const explicit = [...document.querySelectorAll("[data-edgesuite-save]:not([disabled])")].reverse().find(isVisible);
		if (explicit) return explicit;

		const activeDialog = [...document.querySelectorAll(".modal.show, .edge-modal[open], .edge-modal.is-open")].reverse().find(isVisible);
		if (!activeDialog) return null;
		const labels = new Set(["save", "save changes", "update", "apply changes"]);
		return [...activeDialog.querySelectorAll("button:not([disabled]), [role='button']:not([aria-disabled='true'])")]
			.reverse()
			.find((control) => {
				if (!isVisible(control)) return false;
				const label = String(control.dataset.label || control.getAttribute("aria-label") || control.textContent || "").trim().toLowerCase();
				return labels.has(label);
			}) || null;
	}

	async function invokeVisibleSaveControl() {
		const control = findVisibleSaveControl();
		if (!control) return false;
		control.click();
		return true;
	}

	async function invokeFrappeFormSave() {
		const form = window.cur_frm;
		if (!form?.doc || typeof form.save !== "function") return false;
		if (Number(form.doc.docstatus || 0) !== 0) {
			notify("Submitted documents cannot be changed with this shortcut.", "orange");
			return true;
		}
		if (typeof form.is_dirty === "function" && !form.is_dirty()) {
			notify("No unsaved changes.");
			return true;
		}
		await form.save();
		return true;
	}

	async function saveCurrentContext() {
		try {
			if (await invokeRegisteredSave()) return true;
			if (await invokeEventSave()) return true;
			if (await invokeVisibleSaveControl()) return true;
			return await invokeFrappeFormSave();
		} catch (error) {
			console.error("EdgeSuite save command failed", error);
			notify(error?.message || "Unable to save the current page.", "red");
			return true;
		}
	}

	function openCommandPalette() {
		const runtime = window.EdgeSuiteUI || window.EdgeUI;
		if (typeof runtime?.openCommandPalette === "function") {
			runtime.openCommandPalette();
			return true;
		}
		const detail = { handled: false, source: "keyboard", command: "search" };
		window.dispatchEvent(new CustomEvent("edgesuite:command-palette-request", { detail }));
		return Boolean(detail.handled);
	}

	async function onKeydown(event) {
		if (!primaryModifier(event) || event.altKey) return;
		const key = String(event.key || "").toLowerCase();
		if (key === "s") {
			if (editingSurface(event.target) && !event.shiftKey) return;
			event.preventDefault();
			event.stopPropagation();
			await saveCurrentContext();
			return;
		}
		if (key === "k") {
			event.preventDefault();
			event.stopPropagation();
			openCommandPalette();
		}
	}

	registry.version = COMMAND_VERSION;
	registry.registerSaveHandler = registerSaveHandler;
	registry.activateSaveHandler = activateSaveHandler;
	registry.saveCurrentContext = saveCurrentContext;
	registry.openCommandPalette = openCommandPalette;

	if (!window.__edgeSuiteKeyboardCommandsBound) {
		window.__edgeSuiteKeyboardCommandsBound = true;
		document.addEventListener("keydown", onKeydown, true);
	}
})();
