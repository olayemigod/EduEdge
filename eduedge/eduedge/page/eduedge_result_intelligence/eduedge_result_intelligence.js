frappe.pages["eduedge-result-intelligence"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Result Intelligence"),
		single_column: true,
	});
};

frappe.pages["eduedge-result-intelligence"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;
	if (wrapper.vue_app) {
		try { wrapper.vue_app.unmount(); } catch (error) { console.error("Failed to unmount Result Intelligence", error); }
		wrapper.vue_app = null;
	}
	$(page.body).empty();
	const $loading = $(
		`<div class="p-6 text-center text-muted">${__("Loading result intelligence...")}</div>`
	).appendTo(page.body);
	const fail = (message) => {
		$loading.remove();
		$(`<div class="alert alert-danger p-6 text-center"><strong>${__("Result Intelligence failed to load")}</strong><div>${frappe.utils.escape_html(message || "")}</div></div>`).appendTo(page.body);
	};
	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		frappe.require("eduedge_result_intelligence.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (!window.EduEdgeResultIntelligence || typeof window.createEduEdgeResultIntelligenceApp !== "function") {
				return fail(__("The EduEdge Result Intelligence bundle is unavailable."));
			}
			$loading.remove();
			const root = $('<div class="eduedge-result-intelligence-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeResultIntelligenceApp({ pageName: "eduedge-result-intelligence" });
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount Result Intelligence", error);
				fail(error.message || String(error));
			}
		});
	});
};
