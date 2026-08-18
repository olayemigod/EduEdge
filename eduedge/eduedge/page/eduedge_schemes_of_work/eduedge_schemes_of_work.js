frappe.pages["eduedge-schemes-of-work"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({ parent: wrapper, title: __("Scheme of Work"), single_column: true });
};

frappe.pages["eduedge-schemes-of-work"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;
	if (wrapper.vue_app) {
		try { wrapper.vue_app.unmount(); } catch (error) { console.error("Failed to unmount Scheme of Work", error); }
		wrapper.vue_app = null;
	}
	$(page.body).empty();
	const $loading = $(`<div class="p-6 text-center text-muted">${__("Loading Scheme of Work...")}</div>`).appendTo(page.body);
	const fail = (message) => {
		$loading.remove();
		$(`<div class="alert alert-danger p-6 text-center"><strong>${__("Scheme of Work failed to load")}</strong><div>${frappe.utils.escape_html(message || "")}</div></div>`).appendTo(page.body);
	};
	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		frappe.require("eduedge_scheme_of_work.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (!window.EduEdgeSchemeOfWork || typeof window.createEduEdgeSchemeOfWorkApp !== "function") {
				return fail(__("The EduEdge Scheme of Work bundle is unavailable."));
			}
			$loading.remove();
			const root = $('<div class="eduedge-scheme-of-work-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeSchemeOfWorkApp({ pageName: "eduedge-schemes-of-work" });
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount Scheme of Work", error);
				fail(error.message || String(error));
			}
		});
	});
};
