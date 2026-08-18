frappe.pages["eduedge-cbt-marking"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("CBT Marking"),
		single_column: true,
	});
};

frappe.pages["eduedge-cbt-marking"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	page.clear_inner_toolbar();
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount CBT Marking", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(`<div class="p-6 text-center text-muted">${__("Loading CBT marking…")}</div>`).appendTo(page.body);
	const fail = (message) => {
		$loading.remove();
		$(`<div class="alert alert-danger p-6 text-center"><strong>${__("CBT marking failed to load")}</strong><div>${frappe.utils.escape_html(message || "")}</div></div>`).appendTo(page.body);
	};

	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		const runtime = window.EdgeSuiteUI || window.EdgeUI;
		if (!runtime?.install || !runtime?.components?.EdgeAppShell) {
			fail(__("The standalone EdgeSuite UI runtime is unavailable or incomplete."));
			return;
		}
		frappe.require("eduedge_cbt_marking.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (typeof window.createEduEdgeCBTMarkingApp !== "function") {
				fail(__("The EduEdge CBT Marking bundle is unavailable or incomplete."));
				return;
			}
			$loading.remove();
			const root = $('<div class="eduedge-cbt-marking-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeCBTMarkingApp({ pageName: "eduedge-cbt-marking" });
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount CBT Marking", error);
				fail(error.message || String(error));
			}
		});
	});
};
