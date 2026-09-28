frappe.pages["eduedge-result-analytics"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({ parent: wrapper, title: __("Result Analytics"), single_column: true });
};

frappe.pages["eduedge-result-analytics"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;
	if (wrapper.vue_app) {
		try { wrapper.vue_app.unmount(); } catch (error) { console.error("Failed to unmount Result Analytics", error); }
		wrapper.vue_app = null;
	}
	$(page.body).empty();
	const $loading = $('<div class="p-6 text-center text-muted">Loading Result Analytics...</div>').appendTo(page.body);
	const fail = (message) => {
		$loading.remove();
		$('<div class="alert alert-danger p-6 text-center"><strong>Result Analytics failed to load</strong></div>').appendTo(page.body).append($("<div>").text(message || ""));
	};
	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		frappe.require("eduedge_result_analytics.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (typeof window.createEduEdgeResultAnalyticsApp !== "function") return fail(__("The EduEdge Result Analytics bundle is unavailable."));
			$loading.remove();
			const root = $('<div class="eduedge-result-analytics-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeResultAnalyticsApp({ pageName: "eduedge-result-analytics" });
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount Result Analytics", error);
				fail(error.message || String(error));
			}
		});
	});
};
