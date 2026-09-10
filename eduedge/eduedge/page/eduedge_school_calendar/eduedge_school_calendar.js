frappe.pages["eduedge-school-calendar"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("School Calendar"),
		single_column: true,
	});
};

frappe.pages["eduedge-school-calendar"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	if (wrapper.vue_app) {
		try { wrapper.vue_app.unmount(); } catch (error) { console.error("Failed to unmount EduEdge School Calendar", error); }
		wrapper.vue_app = null;
	}
	$(page.body).empty();
	const $loading = $(`<div class="p-6 text-center text-muted">${__("Loading School Calendar...")}</div>`).appendTo(page.body);
	frappe.require("edgesuite_ui.bundle.js", () => {
		frappe.require("eduedge_school_calendar.bundle.js", () => {
			$loading.remove();
			if (!window.EduEdgeSchoolCalendar || typeof window.createEduEdgeSchoolCalendarApp !== "function") {
				$(`<div class="alert alert-danger p-6 text-center">${__("School Calendar failed to load.")}</div>`).appendTo(page.body);
				return;
			}
			const root = $('<div class="eduedge-school-calendar-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeSchoolCalendarApp({ pageName: "eduedge-school-calendar" });
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount EduEdge School Calendar", error);
				$(`<div class="alert alert-danger p-6 text-center">${frappe.utils.escape_html(error.message || String(error))}</div>`).appendTo(page.body);
			}
		});
	});
};
