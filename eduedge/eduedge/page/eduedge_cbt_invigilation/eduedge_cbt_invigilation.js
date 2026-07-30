frappe.pages["eduedge-cbt-invigilation"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("CBT Invigilation"),
		single_column: true,
	});
};

frappe.pages["eduedge-cbt-invigilation"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	page.clear_inner_toolbar();
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount CBT Invigilation", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(`<div class="p-6 text-center text-muted">${__("Loading CBT invigilation…")}</div>`).appendTo(page.body);
	const fail = (message) => {
		$loading.remove();
		$(`<div class="alert alert-danger p-6 text-center"><strong>${__("CBT invigilation failed to load")}</strong><div>${frappe.utils.escape_html(message || "")}</div></div>`).appendTo(page.body);
	};

	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		const runtime = window.EdgeSuiteUI || window.EdgeUI;
		if (!runtime?.install || !runtime?.components?.EdgeAppShell) {
			fail(__("The standalone EdgeSuite UI runtime is unavailable or incomplete."));
			return;
		}
		frappe.require("eduedge_cbt_invigilation.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (typeof window.createEduEdgeCBTInvigilationApp !== "function") {
				fail(__("The EduEdge CBT Invigilation bundle is unavailable or incomplete."));
				return;
			}
			$loading.remove();
			const root = $('<div class="eduedge-cbt-invigilation-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeCBTInvigilationApp({
					pageName: "eduedge-cbt-invigilation",
				});
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount CBT Invigilation", error);
				fail(error.message || String(error));
			}
		});
	});
};
