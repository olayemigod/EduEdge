const SCHOOL_CALENDAR_ROUTE = "/app/eduedge-school-calendar";
const EDUEDGE_DESKTOP_HOME_ROUTE = "/desk/eduedge-home";
const EDUEDGE_DESKTOP_LABEL = "EduEdge";
const EDUEDGE_DESKTOP_LAUNCHER_ATTRIBUTE = "data-eduedge-home-launcher";

function calendarRouteAllowed() {
	if (frappe.session?.user === "Administrator") return true;
	const routes = frappe.boot?.eduedge_access_manifest?.routes;
	return Boolean(routes && Object.prototype.hasOwnProperty.call(routes, SCHOOL_CALENDAR_ROUTE) && routes[SCHOOL_CALENDAR_ROUTE]);
}

function patchEduEdgeProductMenu() {
	frappe.require("edgesuite_ui.bundle.js", () => {
		const runtime = [window.EdgeSuiteUI, window.EdgeUI].find(
			(candidate) => typeof candidate?.registerProductMenu === "function" && typeof candidate?.getProductMenuConfig === "function"
		);
		if (!runtime || !calendarRouteAllowed()) return;
		const config = runtime.getProductMenuConfig();
		if (!config || String(config.product_key || config.key || "").toLowerCase() !== "eduedge") return;
		if ((config.sections || []).some((section) => (section.items || []).some((item) => item.route === SCHOOL_CALENDAR_ROUTE))) return;

		const sections = (config.sections || []).map((section) => {
			if (section.label !== "Academic Setup") return section;
			const items = [...(section.items || [])];
			const calendarItem = {
				label: "School Calendar & Events",
				description: "Unified academic dates, assessments, CBT schedules, teaching overlays, and managed School Events",
				icon: "calendar",
				route: SCHOOL_CALENDAR_ROUTE,
				keywords: ["school", "calendar", "event", "academic", "assessment", "cbt", "schedule"],
			};
			const teachingIndex = items.findIndex((item) => item.route === "/app/eduedge-teaching-schedule");
			items.splice(teachingIndex >= 0 ? teachingIndex + 1 : 0, 0, calendarItem);
			return { ...section, items };
		});
		runtime.registerProductMenu({ ...config, sections });
		runtime.refreshProductMenu?.();
	});
}

function isPlainPrimaryClick(event) {
	return event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
}

function markEduEdgeDesktopAnchor(anchor) {
	if (!anchor) return false;
	anchor.setAttribute(EDUEDGE_DESKTOP_LAUNCHER_ATTRIBUTE, "1");
	anchor.setAttribute("href", EDUEDGE_DESKTOP_HOME_ROUTE);
	anchor.removeAttribute("target");
	return true;
}

function patchLegacyEduEdgeDesktopIcon() {
	let patched = false;
	document.querySelectorAll('a.desktop-icon[data-id="EduEdge"]').forEach((anchor) => {
		patched = markEduEdgeDesktopAnchor(anchor) || patched;
	});
	return patched;
}

function patchModernEduEdgeAppsTile() {
	let patched = false;
	document.querySelectorAll(".desktop-icon").forEach((tile) => {
		if (tile.matches?.("a.desktop-icon")) return;
		const title = tile.querySelector(".icon-title");
		if (String(title?.textContent || "").trim() !== EDUEDGE_DESKTOP_LABEL) return;
		tile.querySelectorAll(".icon-link, .icon-title").forEach((anchor) => {
			patched = markEduEdgeDesktopAnchor(anchor) || patched;
		});
	});
	return patched;
}

function patchEduEdgeDesktopLauncher() {
	patchLegacyEduEdgeDesktopIcon();
	patchModernEduEdgeAppsTile();
}

function navigateEduEdgeHomeSameTab() {
	// Use the exact canonical Desk route. location.assign navigates the current
	// browsing context, so a normal desktop-icon click cannot create a new tab.
	window.location.assign(EDUEDGE_DESKTOP_HOME_ROUTE);
}

function handleEduEdgeDesktopLauncherClick(event) {
	const anchor = event.target?.closest?.(`[${EDUEDGE_DESKTOP_LAUNCHER_ATTRIBUTE}="1"]`);
	if (!anchor || !isPlainPrimaryClick(event)) return;
	event.preventDefault();
	event.stopImmediatePropagation();
	navigateEduEdgeHomeSameTab();
}

function scheduleProductMenuPatch() {
	window.setTimeout(patchEduEdgeProductMenu, 0);
	window.setTimeout(patchEduEdgeDesktopLauncher, 0);
}

if (document.readyState === "loading") {
	document.addEventListener("DOMContentLoaded", scheduleProductMenuPatch, { once: true });
} else {
	scheduleProductMenuPatch();
}

document.addEventListener("click", handleEduEdgeDesktopLauncherClick, true);

["desktop_screen", "sidebar_setup", "toolbar_setup", "page-change"].forEach((eventName) => {
	document.addEventListener(eventName, scheduleProductMenuPatch);
});
window.addEventListener("eduedge:institution-context-changed", scheduleProductMenuPatch);
window.addEventListener("edgesuite:favorites-changed", scheduleProductMenuPatch);

window.EduEdgeDesktopLauncher = Object.freeze({
	route: EDUEDGE_DESKTOP_HOME_ROUTE,
	reconcile: patchEduEdgeDesktopLauncher,
});
