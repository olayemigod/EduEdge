frappe.pages["eduedge-cbt-operations"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("EduEdge CBT"),
		single_column: true,
	});
};

frappe.pages["eduedge-cbt-operations"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge CBT Operations", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(
		`<div class="p-6 text-center text-muted">${__("Loading CBT operations...")}</div>`
	).appendTo(page.body);

	const fail = (message) => {
		$loading.remove();
		$(
			`<div class="alert alert-danger p-6 text-center">
				<strong>${__("CBT operations failed to load")}</strong>
				<div>${frappe.utils.escape_html(message || "")}</div>
			</div>`
		).appendTo(page.body);
	};

	frappe.require("edgeui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		const runtime = window.EdgeSuiteUI || window.EdgeUI;
		if (!runtime?.install || !runtime?.components?.EdgeAppShell) {
			fail(__("The standalone EdgeSuite UI runtime is unavailable or incomplete."));
			return;
		}

		frappe.require("eduedge_cbt_operations.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (
				!window.EduEdgeCBTOperations ||
				typeof window.createEduEdgeCBTOperationsApp !== "function"
			) {
				fail(__("The EduEdge CBT Operations bundle is unavailable or incomplete."));
				return;
			}
			$loading.remove();
			const root = $(
				'<div class="eduedge-cbt-operations-root" data-edge-product="eduedge"></div>'
			).appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeCBTOperationsApp({
					pageName: "eduedge-cbt-operations",
				});
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount EduEdge CBT Operations", error);
				fail(error.message || String(error));
			}
		});
	});
};
