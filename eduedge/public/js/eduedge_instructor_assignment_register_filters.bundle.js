import InstructorAssignmentRegisterFilters from "./eduedge_ui/components/InstructorAssignmentRegisterFilters.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const BASE_PAGE_METHOD = "eduedge.api.instructor_assignments.get_instructor_assignments_page";
const FILTERED_PAGE_METHOD = "eduedge.api.instructor_assignment_register.get_instructor_assignment_register_page";
const FILTER_PREFIX = "assignment_";
const DEFAULT_REGISTER_TAB = "register";
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

function assignmentRoot() {
	return document.querySelector(".eduedge-instructor-assignments-root");
}

function panelByHeading(title) {
	const root = assignmentRoot();
	if (!root) return null;
	return [...root.querySelectorAll(".assignment-panel")].find(
		(panel) => panel.querySelector(".assignment-heading h2")?.textContent?.trim() === title,
	) || null;
}

function findRegisterPanel() {
	return panelByHeading("Instructor Assignment Register");
}

function ensureRegisterTabStyles() {
	if (document.getElementById("eduedge-instructor-assignment-register-tabs-style")) return;
	const style = document.createElement("style");
	style.id = "eduedge-instructor-assignment-register-tabs-style";
	style.textContent = `
		.eduedge-instructor-assignment-tabs-layout { grid-template-columns: minmax(0, 1fr) !important; }
		.eduedge-instructor-assignment-record-toolbar { display:flex; align-items:center; justify-content:space-between; gap:.75rem; flex-wrap:wrap; padding:.8rem .9rem; border:1px solid var(--border-color); border-radius:12px; background:var(--card-bg); }
		.eduedge-instructor-assignment-record-toolbar__identity { display:grid; gap:.2rem; min-width:min(32rem,100%); }
		.eduedge-instructor-assignment-record-toolbar__identity strong { font-size:.95rem; }
		.eduedge-instructor-assignment-record-toolbar__identity small { color:var(--text-muted); }
		.eduedge-instructor-assignment-record-toolbar__actions { display:flex; align-items:end; gap:.5rem; flex-wrap:wrap; }
		.eduedge-instructor-assignment-record-toolbar label { display:grid; gap:.3rem; font-size:.72rem; font-weight:700; min-width:16rem; }
		.eduedge-instructor-assignment-tabs { display:flex; flex-wrap:wrap; gap:.45rem; padding:.15rem 0; }
		.eduedge-instructor-assignment-tabs button { background:var(--control-bg); border:1px solid var(--border-color); border-radius:999px; color:var(--text-color); cursor:pointer; font-size:.78rem; font-weight:700; padding:.45rem .75rem; }
		.eduedge-instructor-assignment-tabs button.is-active { border-color:var(--primary); color:var(--primary); background:var(--card-bg); }
		.eduedge-instructor-assignment-tabs button:focus-visible { outline:2px solid var(--primary); outline-offset:2px; }
		.eduedge-assignment-planner-open { scroll-margin-top:1rem; }
		@media(max-width:700px){.eduedge-instructor-assignment-record-toolbar,.eduedge-instructor-assignment-record-toolbar__actions{align-items:stretch;flex-direction:column}.eduedge-instructor-assignment-record-toolbar label{min-width:0;width:100%}.eduedge-instructor-assignment-record-toolbar__actions .edge-button{width:100%}}
	`;
	document.head.appendChild(style);
}

function plannerParts() {
	const plannerPanel = panelByHeading("Who is being assigned?");
	if (!plannerPanel) return null;
	const rowsStack = plannerPanel.nextElementSibling?.classList?.contains("rows-stack")
		? plannerPanel.nextElementSibling
		: null;
	const actionPanel = rowsStack?.nextElementSibling?.classList?.contains("assignment-panel")
		? rowsStack.nextElementSibling
		: null;
	return { plannerPanel, rowsStack, actionPanel };
}

function applyPlannerVisibility(proxy, parts, toolbar) {
	if (!parts) return;
	const open = Boolean(proxy.canManage && proxy.assignmentPlannerOpen);
	for (const element of [parts.plannerPanel, parts.rowsStack, parts.actionPanel]) {
		if (element) element.hidden = !open;
	}
	parts.plannerPanel?.classList.toggle("eduedge-assignment-planner-open", open);
	const button = toolbar?.querySelector("[data-eduedge-toggle-assignment-planner]");
	if (button) {
		button.textContent = open ? "Close Assignment Planner" : "Add Assignment";
		button.setAttribute("aria-expanded", open ? "true" : "false");
	}
}

function syncToolbarInstructor(proxy, toolbar) {
	const select = toolbar?.querySelector("select[data-eduedge-view-instructor]");
	if (!select) return;
	const current = proxy.instructor || "";
	select.innerHTML = '<option value="">Select Instructor</option>';
	for (const row of proxy.data?.instructors || []) {
		const option = document.createElement("option");
		option.value = row.name;
		option.textContent = row.instructor_name || row.name;
		select.appendChild(option);
	}
	select.value = current;
}

function ensureViewFirstPlanner(proxy) {
	const root = assignmentRoot();
	const parts = plannerParts();
	if (!root || !proxy?.canManage || !parts) return;
	ensureRegisterTabStyles();
	let toolbar = root.querySelector("[data-eduedge-instructor-record-toolbar]");
	if (!toolbar) {
		toolbar = document.createElement("section");
		toolbar.className = "eduedge-instructor-assignment-record-toolbar";
		toolbar.dataset.eduedgeInstructorRecordToolbar = "1";
		toolbar.innerHTML = `
			<div class="eduedge-instructor-assignment-record-toolbar__identity">
				<strong>Instructor records</strong>
				<small>Review assignments and Branch eligibility first. Open the planner only when you need to add responsibility.</small>
			</div>
			<div class="eduedge-instructor-assignment-record-toolbar__actions">
				<label><span>Instructor</span><select class="form-control" data-eduedge-view-instructor></select></label>
				<button type="button" class="edge-button edge-button--primary" data-eduedge-toggle-assignment-planner aria-expanded="false">Add Assignment</button>
			</div>
		`;
		parts.plannerPanel.insertAdjacentElement("beforebegin", toolbar);
		toolbar.querySelector("select[data-eduedge-view-instructor]")?.addEventListener("change", async (event) => {
			proxy.instructor = event.target.value || "";
			proxy.invalidatePreview?.();
			await proxy.load?.();
		});
		toolbar.querySelector("[data-eduedge-toggle-assignment-planner]")?.addEventListener("click", () => {
			proxy.assignmentPlannerOpen = !proxy.assignmentPlannerOpen;
			const currentParts = plannerParts();
			applyPlannerVisibility(proxy, currentParts, toolbar);
			if (proxy.assignmentPlannerOpen) currentParts?.plannerPanel?.scrollIntoView?.({ behavior: "smooth", block: "start" });
		});
	}
	syncToolbarInstructor(proxy, toolbar);
	applyPlannerVisibility(proxy, parts, toolbar);
}

function applyRegisterTab(proxy, layout, registerPanel, eligibilityPanel, tabs) {
	const requested = proxy.assignmentRegisterTab === "eligibility" ? "eligibility" : DEFAULT_REGISTER_TAB;
	const active = requested === "eligibility" && eligibilityPanel ? "eligibility" : DEFAULT_REGISTER_TAB;
	proxy.assignmentRegisterTab = active;
	registerPanel.hidden = active !== DEFAULT_REGISTER_TAB;
	if (eligibilityPanel) eligibilityPanel.hidden = active !== "eligibility";
	for (const button of tabs.querySelectorAll("button[data-register-tab]")) {
		const selected = button.dataset.registerTab === active;
		button.classList.toggle("is-active", selected);
		button.setAttribute("aria-selected", selected ? "true" : "false");
		button.tabIndex = selected ? 0 : -1;
	}
	layout.dataset.activeRegisterTab = active;
}

function ensureRegisterTabs(proxy) {
	const registerPanel = findRegisterPanel();
	const eligibilityPanel = panelByHeading("Branch Eligibility Periods");
	const layout = registerPanel?.closest(".register-layout");
	if (!layout || !registerPanel || !eligibilityPanel) return;
	ensureRegisterTabStyles();
	layout.classList.add("eduedge-instructor-assignment-tabs-layout");
	let tabs = layout.querySelector(":scope > [data-eduedge-assignment-register-tabs]");
	if (!tabs) {
		tabs = document.createElement("div");
		tabs.className = "eduedge-instructor-assignment-tabs";
		tabs.dataset.eduedgeAssignmentRegisterTabs = "1";
		tabs.setAttribute("role", "tablist");
		tabs.setAttribute("aria-label", "Instructor assignment records");
		tabs.innerHTML = `
			<button type="button" role="tab" data-register-tab="register">Instructor Assignment Register</button>
			<button type="button" role="tab" data-register-tab="eligibility">Branch Eligibility Periods</button>
		`;
		layout.prepend(tabs);
		for (const button of tabs.querySelectorAll("button[data-register-tab]")) {
			button.addEventListener("click", () => {
				proxy.assignmentRegisterTab = button.dataset.registerTab || DEFAULT_REGISTER_TAB;
				applyRegisterTab(proxy, layout, registerPanel, eligibilityPanel, tabs);
			});
		}
	}
	applyRegisterTab(proxy, layout, registerPanel, eligibilityPanel, tabs);
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

export function createEduEdgeInstructorAssignmentRegisterFiltersApp(rootProps = null) {
	return createEduEdgeApp(InstructorAssignmentRegisterFilters, rootProps);
}

function mountRegisterFilters(proxy) {
	if (!proxy?.loaded) return null;
	ensureViewFirstPlanner(proxy);
	if (!proxy.instructor) return null;
	ensureRegisterTabs(proxy);
	const panel = findRegisterPanel();
	if (!panel) return null;
	syncRegisterHeading(proxy, panel);

	const existing = filterApps.get(proxy);
	if (existing?.host?.isConnected && existing.instructor === proxy.instructor) {
		return existing;
	}
	// Never replace the child filter app while its request is still settling. The
	// old implementation remounted it with busy=true, which could strand the new
	// app in a permanent Filtering state.
	if (proxy.registerFilterLoading) return existing || null;
	if (existing) {
		try { existing.app?.unmount?.(); } catch (error) { console.error("Failed to refresh Instructor Assignment filters", error); }
		existing.host?.remove?.();
	}

	const heading = panel.querySelector(":scope > .assignment-heading");
	if (!heading) return null;
	const host = document.createElement("div");
	host.className = "eduedge-instructor-assignment-register-filter-host";
	heading.insertAdjacentElement("afterend", host);
	const app = createEduEdgeInstructorAssignmentRegisterFiltersApp({ controller: proxy });
	app.mount(host);
	const mounted = { app, host, instructor: proxy.instructor };
	filterApps.set(proxy, mounted);
	return mounted;
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
			assignmentRegisterTab: DEFAULT_REGISTER_TAB,
			assignmentPlannerOpen: false,
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
			await this.$nextTick?.();
			mountRegisterFilters(this);
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
			await this.$nextTick?.();
			mountRegisterFilters(this);
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
			ensureViewFirstPlanner(this);
			ensureRegisterTabs(this);
			mountRegisterFilters(this);
			return result;
		};
	}
}

export function installInstructorAssignmentRegisterFilters(component = window.EduEdgeInstructorAssignments) {
	install(component);
}

installInstructorAssignmentRegisterFilters(window.EduEdgeInstructorAssignments);
window.createEduEdgeInstructorAssignmentRegisterFiltersApp = createEduEdgeInstructorAssignmentRegisterFiltersApp;
window.installInstructorAssignmentRegisterFilters = installInstructorAssignmentRegisterFilters;
