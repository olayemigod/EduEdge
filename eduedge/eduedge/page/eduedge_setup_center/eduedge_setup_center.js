frappe.pages["eduedge-setup-center"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("EduEdge Setup Center"),
		single_column: true,
	});
};

frappe.pages["eduedge-setup-center"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge Setup Center", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(
		`<div class="p-6 text-center text-muted">${__("Loading EduEdge Setup Center...")}</div>`
	).appendTo(page.body);

	const fail = (message) => {
		$loading.remove();
		$(
			`<div class="alert alert-danger p-6 text-center">
				<strong>${__("EduEdge Setup Center failed to load")}</strong>
				<div>${frappe.utils.escape_html(message || "")}</div>
			</div>`
		).appendTo(page.body);
	};

	// The legacy `edgeui.bundle.js` manifest key is intentionally not loaded.
	// Mixed-app sites must resolve the collision-safe standalone runtime instead.
	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		const runtime = window.EdgeSuiteUI || window.EdgeUI;
		if (!runtime?.install || !runtime?.components?.EdgeAppShell) {
			fail(__("The standalone EdgeSuite UI runtime is unavailable or incomplete."));
			return;
		}

		frappe.require("eduedge_setup_center.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (
				!window.EduEdgeSetupCenter ||
				typeof window.createEduEdgeSetupCenterApp !== "function"
			) {
				fail(__("The EduEdge Setup Center product bundle is unavailable or incomplete."));
				return;
			}
			$loading.remove();
			const root = $('<div class="eduedge-setup-center-root" data-edge-product="eduedge"></div>')
				.appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeSetupCenterApp({
					pageName: "eduedge-setup-center",
				});
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount EduEdge Setup Center", error);
				fail(error.message || String(error));
			}
		});
	});
};
