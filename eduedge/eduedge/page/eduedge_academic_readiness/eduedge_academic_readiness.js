frappe.pages["eduedge-academic-readiness"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({ parent: wrapper, title: __("Academic Readiness"), single_column: true });
};

frappe.pages["eduedge-academic-readiness"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;
	if (wrapper.vue_app) {
		try { wrapper.vue_app.unmount(); } catch (error) { console.error("Failed to unmount Academic Readiness", error); }
		wrapper.vue_app = null;
	}
	$(page.body).empty();
	const $loading = $(`<div class="p-6 text-center text-muted">${__("Loading Academic Readiness...")}</div>`).appendTo(page.body);
	const fail = (message) => {
		$loading.remove();
		$(`<div class="alert alert-danger p-6 text-center"><strong>${__("Academic Readiness failed to load")}</strong><div>${frappe.utils.escape_html(message || "")}</div></div>`).appendTo(page.body);
	};
	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		frappe.require("eduedge_academic_readiness.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (!window.EduEdgeAcademicReadiness || typeof window.createEduEdgeAcademicReadinessApp !== "function") {
				return fail(__("The EduEdge Academic Readiness bundle is unavailable."));
			}
			$loading.remove();
			const root = $('<div class="eduedge-academic-readiness-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeAcademicReadinessApp({ pageName: "eduedge-academic-readiness" });
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount Academic Readiness", error);
				fail(error.message || String(error));
			}
		});
	});
};
