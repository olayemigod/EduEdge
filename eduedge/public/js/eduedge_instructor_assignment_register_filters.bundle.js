import InstructorAssignmentRegisterFilters from "./eduedge_ui/components/InstructorAssignmentRegisterFilters.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const BASE_PAGE_METHOD = "eduedge.api.instructor_assignments.get_instructor_assignments_page";
const FILTERED_PAGE_METHOD = "eduedge.api.instructor_assignment_register.get_instructor_assignment_register_page";
const FILTER_PREFIX = "assignment_";
const filterApps = new WeakMap();

const FILTER_KEYS = [
	"branch",
	"academic_year",
	"academic_term",
	"program_offering",
	"student_group",
	"course",
	"assignment_type",
	"assignment_scope",
	"lifecycle_status",
	"origin",
	"date_from",
	"date_to",
	"search_text",
	"preset",
];

function urlFilters() {
	const params = new URLSearchParams(window.location.search || "");
	const result = {
		instructor: params.get("instructor") || "",
		preset: params.get(`${FILTER_PREFIX}preset`) || "current_upcoming",
	};
	for (const key of FILTER_KEYS) {
		if (key === "preset") continue;
		result[key] = params.get(`${FILTER_PREFIX}${key}`) || "";
	}
	return result;
}

function cleanFilters(source = {}) {
	const result = { instructor: String(source.instructor || "").trim() };
	for (const key of FILTER_KEYS) result[key] = String(source[key] || "").trim();
	if (!result.preset) result.preset = "current_upcoming";
	return result;
}

function updateUrl(proxy) {
	const params = new URLSearchParams(window.location.search || "");
	const filters = cleanFilters(proxy.registerFilters || {});
	if (proxy.instructor) params.set("instructor", proxy.instructor);
	else params.delete("instructor");
	for (const key of FILTER_KEYS) {
		const value = filters[key];
		const param = `${FILTER_PREFIX}${key}`;
		if (value && !(key === "preset" && value === "current_upcoming")) params.set(param, value);
		else params.delete(param);
	}
	if ((proxy.registerPage || 1) > 1) params.set(`${FILTER_PREFIX}page`, String(proxy.registerPage));
	else params.delete(`${FILTER_PREFIX}page`);
	const next = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ""}${window.location.hash || ""}`;
	window.history.replaceState(window.history.state, "", next);
}

function registerPageFromUrl() {
	const params = new URLSearchParams(window.location.search || "");
	const value = Number(params.get(`${FILTER_PREFIX}page`) || 1);
	return Number.isFinite(value) && value > 0 ? Math.floor(value) : 1;
}

function redirectPageCall(proxy, originalCall) {
	let redirected = false;
	return function redirectedFrappeCall(methodOrOptions, args, ...rest) {
		if (!redirected && methodOrOptions === BASE_PAGE_METHOD) {
			redirected = true;
			return originalCall.call(frappe, FILTERED_PAGE_METHOD, {
				...(args || {}),
				register_filters: JSON.stringify(proxy.registerFilters || {}),
				register_page: proxy.registerPage || 1,
				register_page_size: proxy.registerPageSize || 50,
			}, ...rest);
		}
		if (!redirected && methodOrOptions && typeof methodOrOptions === "object" && methodOrOptions.method === BASE_PAGE_METHOD) {
			redirected = true;
			return originalCall.call(frappe, {
				...methodOrOptions,
				method: FILTERED_PAGE_METHOD,
				args: {
					...(methodOrOptions.args || {}),
					register_filters: JSON.stringify(proxy.registerFilters || {}),
					register_page: proxy.registerPage || 1,
					register_page_size: proxy.registerPageSize || 50,
				},
			}, args, ...rest);
		}
		return originalCall.call(frappe, methodOrOptions, args, ...rest);
	};
}

function findRegisterPanel() {
	const root = document.querySelector(".eduedge-instructor-assignments-root");
	if (!root) return null;
	return [...root.querySelectorAll(".assignment-panel")].find(
		(panel) => panel.querySelector(".assignment-heading h2")?.textContent?.trim() === "Instructor Assignment Register",
	) || null;
}

function syncRegisterHeading(proxy, panel) {
	const summary = panel?.querySelector(":scope > .assignment-heading > span");
	if (!summary) return;
	const meta = proxy.registerMeta || {};
	if (!meta.total) {
		summary.textContent = "0";
		return;
	}
	summary.textContent = `${meta.total} total · ${meta.from_row || 0}–${meta.to_row || 0}`;
}

function mountRegisterFilters(proxy) {
	if (!proxy?.loaded || !proxy.instructor) return;
	const panel = findRegisterPanel();
	if (!panel) return;
	syncRegisterHeading(proxy, panel);

	const existing = filterApps.get(proxy);
	if (existing) {
		try { existing.app?.unmount?.(); } catch (error) { console.error("Failed to refresh Instructor Assignment filters", error); }
		existing.host?.remove?.();
	}

	const heading = panel.querySelector(":scope > .assignment-heading");
	if (!heading) return;
	const host = document.createElement("div");
	host.className = "eduedge-instructor-assignment-register-filter-host";
	heading.insertAdjacentElement("afterend", host);
	const app = createEduEdgeApp(InstructorAssignmentRegisterFilters, { controller: proxy });
	app.mount(host);
	filterApps.set(proxy, { app, host });
}

function install(component) {
	if (!component || component.__eduedgeAssignmentRegisterFiltersInstalled) return;
	component.__eduedgeAssignmentRegisterFiltersInstalled = true;

	const originalData = component.data;
	component.data = function (...args) {
		const base = typeof originalData === "function" ? originalData.apply(this, args) : {};
		return {
			...base,
			registerFilters: urlFilters(),
			registerPage: registerPageFromUrl(),
			registerPageSize: 50,
			registerMeta: {},
			registerFilterLoading: false,
		};
	};

	const methods = component.methods || (component.methods = {});
	methods.defaultRegisterFilters = function () {
		return cleanFilters({ instructor: this.instructor || "", preset: "current_upcoming" });
	};
	methods.applyRegisterFilters = async function (nextFilters = {}) {
		const cleaned = cleanFilters(nextFilters);
		const nextInstructor = cleaned.instructor || this.instructor || "";
		if (nextInstructor !== this.instructor) {
			this.instructor = nextInstructor;
			this.invalidatePreview?.();
		}
		cleaned.instructor = this.instructor || nextInstructor;
		this.registerFilters = cleaned;
		this.registerPage = 1;
		updateUrl(this);
		this.registerFilterLoading = true;
		try {
			await this.load?.();
		} finally {
			this.registerFilterLoading = false;
		}
	};
	methods.setRegisterPage = async function (page) {
		const target = Math.max(Number(page || 1), 1);
		this.registerPage = target;
		updateUrl(this);
		this.registerFilterLoading = true;
		try {
			await this.load?.();
		} finally {
			this.registerFilterLoading = false;
		}
	};

	const existingLoad = methods.load;
	if (typeof existingLoad === "function") {
		methods.load = async function (...args) {
			const originalCall = frappe.call;
			frappe.call = redirectPageCall(this, originalCall);
			let promise;
			try {
				// The existing load reaches its first await immediately after requesting the page.
				// Restore frappe.call at once so lifecycle and unrelated RPC calls stay untouched.
				promise = existingLoad.apply(this, args);
			} finally {
				frappe.call = originalCall;
			}
			const result = await promise;
			this.registerMeta = this.data?.assignment_register || {};
			if (this.registerMeta.page && this.registerMeta.page !== this.registerPage) this.registerPage = this.registerMeta.page;
			this.registerFilters = cleanFilters({
				...(this.registerFilters || {}),
				...(this.registerMeta.filters || {}),
				instructor: this.instructor || this.registerFilters?.instructor || "",
			});
			updateUrl(this);
			await this.$nextTick?.();
			mountRegisterFilters(this);
			return result;
		};
	}
}

export function installInstructorAssignmentRegisterFilters(component = window.EduEdgeInstructorAssignments) {
	install(component);
}

installInstructorAssignmentRegisterFilters(window.EduEdgeInstructorAssignments);
window.installInstructorAssignmentRegisterFilters = installInstructorAssignmentRegisterFilters;
