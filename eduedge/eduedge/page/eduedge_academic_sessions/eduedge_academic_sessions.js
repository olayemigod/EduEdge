frappe.pages["eduedge-academic-sessions"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Academic Sessions and Terms"),
		single_column: true,
	});
};

frappe.pages["eduedge-academic-sessions"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge Academic Sessions", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(
		`<div class="p-6 text-center text-muted">${__("Loading Academic Sessions and Terms...")}</div>`
	).appendTo(page.body);

	const fail = (message) => {
		$loading.remove();
		$(
			`<div class="alert alert-danger p-6 text-center">
				<strong>${__("Academic Sessions and Terms failed to load")}</strong>
				<div>${frappe.utils.escape_html(message || "")}</div>
			</div>`
		).appendTo(page.body);
	};

	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		frappe.require("eduedge_academic_sessions.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (!window.EduEdgeAcademicSessions || typeof window.createEduEdgeAcademicSessionsApp !== "function") {
				fail(__("The EduEdge Academic Sessions bundle is unavailable or incomplete."));
				return;
			}
			$loading.remove();
			const root = $('<div class="eduedge-academic-sessions-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeAcademicSessionsApp({
					pageName: "eduedge-academic-sessions",
				});
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount EduEdge Academic Sessions", error);
				fail(error.message || String(error));
			}
		});
	});
};
