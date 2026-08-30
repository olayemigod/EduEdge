const SCHOOL_CALENDAR_ROUTE = "/app/eduedge-school-calendar";

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

function scheduleProductMenuPatch() {
	window.setTimeout(patchEduEdgeProductMenu, 0);
}

if (document.readyState === "loading") {
	document.addEventListener("DOMContentLoaded", scheduleProductMenuPatch, { once: true });
} else {
	scheduleProductMenuPatch();
}

["desktop_screen", "sidebar_setup", "toolbar_setup", "page-change"].forEach((eventName) => {
	document.addEventListener(eventName, scheduleProductMenuPatch);
});
window.addEventListener("eduedge:institution-context-changed", scheduleProductMenuPatch);
window.addEventListener("edgesuite:favorites-changed", scheduleProductMenuPatch);
