frappe.pages["eduedge-academic-sessions"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Academic Session Launch"),
		single_column: true,
	});
};

frappe.pages["eduedge-academic-sessions"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;
	const params = new URLSearchParams(window.location.search || "");
	let activeMode = params.get("mode") === "manual" ? "manual" : "guided";

	const unmountCurrent = () => {
		if (!wrapper.vue_app) return;
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge Academic Session mode", error);
		}
		wrapper.vue_app = null;
	};

	unmountCurrent();
	if (wrapper._session_tab_listener) {
		window.removeEventListener("eduedge:academic-session-tab", wrapper._session_tab_listener);
		wrapper._session_tab_listener = null;
	}
	if (typeof page.clear_inner_toolbar === "function") page.clear_inner_toolbar();
	$(page.body).empty();

	const $tabs = $(
		`<div class="eduedge-session-mode-tabs" role="tablist" aria-label="Academic Session workspace mode">
			<button type="button" class="eduedge-session-mode-tab" data-mode="guided" role="tab">${__("Guided Session Launch")}</button>
			<button type="button" class="eduedge-session-mode-tab" data-mode="manual" role="tab">${__("Manual Session & Term Management")}</button>
		</div>`
	).appendTo(page.body);
	const $host = $('<div class="eduedge-session-mode-host"></div>').appendTo(page.body);

	if (!document.getElementById("eduedge-session-mode-style")) {
		$(
			`<style id="eduedge-session-mode-style">
				.eduedge-session-mode-tabs{display:flex;gap:.35rem;margin:.25rem 0 .85rem;padding:.3rem;border:1px solid var(--border-color);border-radius:10px;background:var(--control-bg);width:max-content;max-width:100%}
				.eduedge-session-mode-tab{border:0;background:transparent;padding:.5rem .8rem;border-radius:7px;font-weight:600;color:var(--text-muted);white-space:nowrap}
				.eduedge-session-mode-tab.is-active{background:var(--card-bg);color:var(--text-color);box-shadow:0 1px 2px rgba(0,0,0,.08)}
				.eduedge-session-mode-host{min-width:0}
				@media(max-width:700px){.eduedge-session-mode-tabs{width:100%;overflow-x:auto}.eduedge-session-mode-tab{flex:1}}
			</style>`
		).appendTo(document.head);
	}

	const fail = (title, message) => {
		$host.empty();
		$(
			`<div class="alert alert-danger p-6 text-center">
				<strong>${frappe.utils.escape_html(title || "")}</strong>
				<div>${frappe.utils.escape_html(message || "")}</div>
			</div>`
		).appendTo($host);
	};

	const syncTabs = () => {
		$tabs.find(".eduedge-session-mode-tab").each(function () {
			const selected = $(this).data("mode") === activeMode;
			$(this).toggleClass("is-active", selected).attr("aria-selected", selected ? "true" : "false");
		});
		page.set_title(activeMode === "manual" ? __("Academic Sessions and Terms") : __("Academic Session Launch"));
	};

	const updateUrl = () => {
		const url = new URL(window.location.href);
		if (activeMode === "manual") url.searchParams.set("mode", "manual");
		else url.searchParams.delete("mode");
		window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
	};

	const mountMode = () => {
		if (wrapper.current_visit_id !== visitId) return;
		unmountCurrent();
		$host.empty();
		syncTabs();
		const loadingLabel = activeMode === "manual" ? __("Loading Academic Sessions and Terms...") : __("Loading Academic Session Launch...");
		const $loading = $(`<div class="p-6 text-center text-muted">${loadingLabel}</div>`).appendTo($host);

		const mountManual = () => {
			if (wrapper.current_visit_id !== visitId || activeMode !== "manual") return;
			if (!window.EduEdgeAcademicSessions || typeof window.createEduEdgeAcademicSessionsApp !== "function") {
				fail(__("Academic Sessions and Terms failed to load"), __("The EduEdge Academic Sessions bundle is unavailable or incomplete."));
				return;
			}
			$loading.remove();
			const root = $('<div class="eduedge-academic-sessions-root" data-edge-product="eduedge"></div>').appendTo($host);
			try {
				wrapper.vue_app = window.createEduEdgeAcademicSessionsApp({ pageName: "eduedge-academic-sessions" });
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount EduEdge Academic Sessions", error);
				fail(__("Academic Sessions and Terms failed to load"), error.message || String(error));
			}
		};

		const mountLaunch = () => {
			if (wrapper.current_visit_id !== visitId || activeMode !== "guided") return;
			if (!window.EduEdgeSessionLaunch || typeof window.createEduEdgeSessionLaunchApp !== "function") {
				fail(__("Academic Session Launch failed to load"), __("The EduEdge Session Launch bundle is unavailable or incomplete."));
				return;
			}
			$loading.remove();
			const root = $('<div class="eduedge-session-launch-root" data-edge-product="eduedge"></div>').appendTo($host);
			try {
				wrapper.vue_app = window.createEduEdgeSessionLaunchApp({ pageName: "eduedge-academic-sessions" });
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount EduEdge Session Launch", error);
				fail(__("Academic Session Launch failed to load"), error.message || String(error));
			}
		};

		frappe.require("edgesuite_ui.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (activeMode === "manual") frappe.require("eduedge_academic_sessions.bundle.js", mountManual);
			else frappe.require("eduedge_session_launch.bundle.js", mountLaunch);
		});
	};

	const switchMode = (mode, { updateHistory = true } = {}) => {
		const next = mode === "manual" ? "manual" : "guided";
		if (next === activeMode && wrapper.vue_app) return;
		activeMode = next;
		if (updateHistory) updateUrl();
		mountMode();
	};

	$tabs.on("click", ".eduedge-session-mode-tab", function () {
		switchMode($(this).data("mode"));
	});

	wrapper.switch_session_mode = switchMode;
	wrapper._session_tab_listener = (event) => {
		if (wrapper.current_visit_id !== visitId) return;
		switchMode(event?.detail?.mode || "guided");
	};
	window.addEventListener("eduedge:academic-session-tab", wrapper._session_tab_listener);

	syncTabs();
	mountMode();
};
