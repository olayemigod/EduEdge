frappe.pages["eduedge-marks-entry"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({ parent: wrapper, title: __("Marks Entry"), single_column: true });
};

frappe.pages["eduedge-marks-entry"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;
	if (wrapper.vue_app) {
		try { wrapper.vue_app.unmount(); } catch (error) { console.error("Failed to unmount Marks Entry", error); }
		wrapper.vue_app = null;
	}
	$(page.body).empty();
	const $loading = $('<div class="p-6 text-center text-muted">Loading Marks Entry...</div>').appendTo(page.body);
	const fail = (message) => {
		$loading.remove();
		$('<div class="alert alert-danger p-6 text-center"><strong>Marks Entry failed to load</strong></div>').appendTo(page.body).append($("<div>").text(message || ""));
	};
	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		frappe.require("eduedge_marks_entry.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (typeof window.createEduEdgeMarksEntryApp !== "function") return fail(__("The EduEdge Marks Entry bundle is unavailable."));
			$loading.remove();
			const root = $('<div class="eduedge-marks-entry-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeMarksEntryApp({ pageName: "eduedge-marks-entry" });
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount Marks Entry", error);
				fail(error.message || String(error));
			}
		});
	});
};
