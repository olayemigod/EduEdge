frappe.pages["eduedge-lesson-plans"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({ parent: wrapper, title: __("Lesson Plans"), single_column: true });
};

frappe.pages["eduedge-lesson-plans"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;
	if (wrapper.vue_app) {
		try { wrapper.vue_app.unmount(); } catch (error) { console.error("Failed to unmount Lesson Plans", error); }
		wrapper.vue_app = null;
	}
	$(page.body).empty();
	const $loading = $(`<div class="p-6 text-center text-muted">${__("Loading Lesson Plans...")}</div>`).appendTo(page.body);
	const fail = (message) => {
		$loading.remove();
		$(`<div class="alert alert-danger p-6 text-center"><strong>${__("Lesson Plans failed to load")}</strong><div>${frappe.utils.escape_html(message || "")}</div></div>`).appendTo(page.body);
	};
	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		frappe.require("eduedge_lesson_plans.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (!window.EduEdgeLessonPlans || typeof window.createEduEdgeLessonPlansApp !== "function") {
				return fail(__("The EduEdge Lesson Plans bundle is unavailable."));
			}
			$loading.remove();
			const root = $('<div class="eduedge-lesson-plans-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeLessonPlansApp({ pageName: "eduedge-lesson-plans" });
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount Lesson Plans", error);
				fail(error.message || String(error));
			}
		});
	});
};
