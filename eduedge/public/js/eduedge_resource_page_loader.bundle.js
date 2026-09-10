window.registerEduEdgeResourcePage = function registerEduEdgeResourcePage({
	pageName,
	title,
	resourceKey,
	activeRoute,
}) {
	if (!pageName || !resourceKey || !activeRoute) {
		throw new Error("EduEdge resource page registration requires pageName, resourceKey, and activeRoute.");
	}

	frappe.pages[pageName].on_page_load = function (wrapper) {
		wrapper.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __(title || "EduEdge"),
			single_column: true,
		});
	};

	frappe.pages[pageName].on_page_show = function (wrapper) {
		const page = wrapper.page;
		wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
		const visitId = wrapper.current_visit_id;

		if (wrapper.vue_app) {
			try {
				wrapper.vue_app.unmount();
			} catch (error) {
				console.error(`Failed to unmount ${title || pageName}`, error);
			}
			wrapper.vue_app = null;
		}

		$(page.body).empty();
		const $loading = $(`<div class="p-6 text-center text-muted">${__("Loading EduEdge page...")}</div>`).appendTo(page.body);
		const fail = (message) => {
			$loading.remove();
			$(`<div class="alert alert-danger p-6 text-center"><strong>${__("EduEdge page failed to load")}</strong><div>${frappe.utils.escape_html(message || "")}</div></div>`).appendTo(page.body);
		};

		frappe.require("edgesuite_ui.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			const runtime = [window.EdgeSuiteUI, window.EdgeUI].find(
				(candidate) => typeof candidate?.install === "function" && Boolean(candidate?.components?.EdgeAppShell)
			);
			if (!runtime) {
				fail(__("The standalone EdgeSuite UI runtime is unavailable or incomplete."));
				return;
			}

			frappe.require("eduedge_resource_center.bundle.js", () => {
				if (wrapper.current_visit_id !== visitId) return;
				if (!window.EduEdgeResourceCenter || typeof window.createEduEdgeResourceCenterApp !== "function") {
					fail(__("The EduEdge resource-center bundle is unavailable or incomplete."));
					return;
				}
				$loading.remove();
				const root = $('<div class="eduedge-resource-center-root" data-edge-product="eduedge"></div>').appendTo(page.body);
				try {
					wrapper.vue_app = window.createEduEdgeResourceCenterApp({ resourceKey, activeRoute });
					wrapper.vue_app.mount(root[0]);
				} catch (error) {
					console.error(`Failed to mount ${title || pageName}`, error);
					fail(error.message || String(error));
				}
			});
		});
	};
};
