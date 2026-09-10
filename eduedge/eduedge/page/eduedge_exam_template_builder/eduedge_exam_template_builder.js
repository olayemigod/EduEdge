function resolveTemplateName() {
	const route = frappe.get_route ? frappe.get_route() : [];
	if (route[0] === "eduedge-exam-template-builder" && route[1]) return route[1];
	try {
		return new URL(window.location.href).searchParams.get("template") || null;
	} catch (_error) {
		return null;
	}
}

frappe.pages["eduedge-exam-template-builder"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Exam Template Builder"),
		single_column: true,
	});
};

frappe.pages["eduedge-exam-template-builder"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	page.clear_inner_toolbar();
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge Exam Template Builder", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(`<div class="p-6 text-center text-muted">${__("Loading Exam Template Builder...")}</div>`).appendTo(page.body);

	const fail = (message) => {
		if (wrapper.current_visit_id !== visitId) return;
		$loading.remove();
		$(`<div class="alert alert-danger p-6 text-center">
			<strong>${__("Exam Template Builder failed to load")}</strong>
			<div>${frappe.utils.escape_html(message || "")}</div>
		</div>`).appendTo(page.body);
	};

	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		const runtime = window.EdgeSuiteUI || window.EdgeUI;
		if (!runtime?.install || !runtime?.components?.EdgeAppShell || !runtime?.components?.EdgeLinkField) {
			fail(__("The standalone EdgeSuite UI runtime is unavailable or incomplete."));
			return;
		}

		frappe.require("eduedge_exam_template_builder.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (!window.EduEdgeExamTemplateBuilder || typeof window.createEduEdgeExamTemplateBuilderApp !== "function") {
				fail(__("The EduEdge Exam Template Builder bundle is unavailable or incomplete."));
				return;
			}
			$loading.remove();
			const root = $('<div class="eduedge-exam-template-builder-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeExamTemplateBuilderApp({
					pageName: "eduedge-exam-template-builder",
					templateName: resolveTemplateName(),
				});
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount EduEdge Exam Template Builder", error);
				fail(error.message || String(error));
			}
		});
	});
};
