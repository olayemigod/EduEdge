const EXAM_TEMPLATE_LIST_READY_TIMEOUT_MS = 1500;
const EXAM_TEMPLATE_LIST_READY_POLL_MS = 50;

function getExamTemplateListBundle() {
	const component = window.EduEdgeExamTemplates;
	const factory = window.createEduEdgeExamTemplatesApp;
	if (!component || typeof factory !== "function") return null;
	return { component, factory };
}

function waitForExamTemplateListBundle(callback, startedAt = Date.now()) {
	const bundle = getExamTemplateListBundle();
	if (bundle) {
		callback(bundle);
		return;
	}
	if (Date.now() - startedAt >= EXAM_TEMPLATE_LIST_READY_TIMEOUT_MS) {
		callback(null);
		return;
	}
	setTimeout(() => waitForExamTemplateListBundle(callback, startedAt), EXAM_TEMPLATE_LIST_READY_POLL_MS);
}

frappe.pages["eduedge-exam-templates"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Exam Templates"),
		single_column: true,
	});
};

frappe.pages["eduedge-exam-templates"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	page.clear_inner_toolbar();
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge Exam Templates", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(`<div class="p-6 text-center text-muted">${__("Loading Exam Templates...")}</div>`).appendTo(page.body);

	const fail = (message) => {
		if (wrapper.current_visit_id !== visitId) return;
		$loading.remove();
		$(`<div class="alert alert-danger p-6 text-center">
			<strong>${__("Exam Templates failed to load")}</strong>
			<div>${frappe.utils.escape_html(message || "")}</div>
		</div>`).appendTo(page.body);
	};

	const mount = (bundle) => {
		if (wrapper.current_visit_id !== visitId) return;
		if (!bundle) {
			fail(__("The EduEdge Exam Templates bundle is unavailable or incomplete."));
			return;
		}
		$loading.remove();
		const root = $('<div class="eduedge-exam-templates-root" data-edge-product="eduedge"></div>').appendTo(page.body);
		try {
			wrapper.vue_app = bundle.factory({ pageName: "eduedge-exam-templates" });
			wrapper.vue_app.mount(root[0]);
		} catch (error) {
			console.error("Failed to mount EduEdge Exam Templates", error);
			fail(error.message || String(error));
		}
	};

	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		const runtime = window.EdgeSuiteUI || window.EdgeUI;
		if (!runtime?.install || !runtime?.components?.EdgeAppShell || !runtime?.components?.EdgeLinkField) {
			fail(__("The standalone EdgeSuite UI runtime is unavailable or incomplete."));
			return;
		}
		frappe.require("eduedge_exam_templates.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			waitForExamTemplateListBundle(mount);
		});
	});
};
