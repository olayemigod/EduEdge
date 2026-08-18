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
	const manualMode = params.get("mode") === "manual";

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge Academic Sessions", error);
		}
		wrapper.vue_app = null;
	}

	if (typeof page.clear_inner_toolbar === "function") page.clear_inner_toolbar();
	if (manualMode) {
		page.set_title(__("Academic Sessions and Terms"));
		page.add_inner_button(__("Session Launch"), () => {
			window.location.href = "/app/eduedge-academic-sessions";
		});
	} else {
		page.set_title(__("Academic Session Launch"));
	}

	$(page.body).empty();
	const loadingLabel = manualMode ? __("Loading Academic Sessions and Terms...") : __("Loading Academic Session Launch...");
	const $loading = $(`<div class="p-6 text-center text-muted">${loadingLabel}</div>`).appendTo(page.body);

	const fail = (title, message) => {
		$loading.remove();
		$(
			`<div class="alert alert-danger p-6 text-center">
				<strong>${frappe.utils.escape_html(title || "")}</strong>
				<div>${frappe.utils.escape_html(message || "")}</div>
			</div>`
		).appendTo(page.body);
	};

	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		const bundle = manualMode ? "eduedge_academic_sessions.bundle.js" : "eduedge_session_launch.bundle.js";
		frappe.require(bundle, () => {
			if (wrapper.current_visit_id !== visitId) return;
			$loading.remove();

			if (manualMode) {
				if (!window.EduEdgeAcademicSessions || typeof window.createEduEdgeAcademicSessionsApp !== "function") {
					fail(__("Academic Sessions and Terms failed to load"), __("The EduEdge Academic Sessions bundle is unavailable or incomplete."));
					return;
				}
				const root = $('<div class="eduedge-academic-sessions-root" data-edge-product="eduedge"></div>').appendTo(page.body);
				try {
					wrapper.vue_app = window.createEduEdgeAcademicSessionsApp({ pageName: "eduedge-academic-sessions" });
					wrapper.vue_app.mount(root[0]);
				} catch (error) {
					console.error("Failed to mount EduEdge Academic Sessions", error);
					fail(__("Academic Sessions and Terms failed to load"), error.message || String(error));
				}
				return;
			}

			if (!window.EduEdgeSessionLaunch || typeof window.createEduEdgeSessionLaunchApp !== "function") {
				fail(__("Academic Session Launch failed to load"), __("The EduEdge Session Launch bundle is unavailable or incomplete."));
				return;
			}
			const root = $('<div class="eduedge-session-launch-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeSessionLaunchApp({ pageName: "eduedge-academic-sessions" });
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount EduEdge Session Launch", error);
				fail(__("Academic Session Launch failed to load"), error.message || String(error));
			}
		});
	});
};
