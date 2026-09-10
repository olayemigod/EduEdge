const OPERATIONS_BUNDLE_READY_TIMEOUT_MS = 1500;
const OPERATIONS_BUNDLE_READY_POLL_MS = 50;

function getInstitutionOperationsBundle() {
	const component = window.EduEdgeInstitutionOperationsSettings;
	const factory = window.createEduEdgeInstitutionOperationsSettingsApp;
	if (!component || typeof factory !== "function") return null;
	return { component, factory };
}

function waitForInstitutionOperationsBundle(callback, startedAt = Date.now()) {
	const bundle = getInstitutionOperationsBundle();
	if (bundle) {
		callback(bundle);
		return;
	}
	if (Date.now() - startedAt >= OPERATIONS_BUNDLE_READY_TIMEOUT_MS) {
		callback(null);
		return;
	}
	setTimeout(
		() => waitForInstitutionOperationsBundle(callback, startedAt),
		OPERATIONS_BUNDLE_READY_POLL_MS
	);
}

frappe.pages["eduedge-institution-operations-settings"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Institution Operations Settings"),
		single_column: true,
	});
};

frappe.pages["eduedge-institution-operations-settings"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge Institution Operations Settings", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(
		`<div class="p-6 text-center text-muted">${__("Loading Institution Operations Settings...")}</div>`
	).appendTo(page.body);

	const fail = (message) => {
		if (wrapper.current_visit_id !== visitId) return;
		$loading.remove();
		$(
			`<div class="alert alert-danger p-6 text-center">
				<strong>${__("Institution Operations Settings failed to load")}</strong>
				<div>${frappe.utils.escape_html(message || "")}</div>
			</div>`
		).appendTo(page.body);
	};

	const mount = (bundle) => {
		if (wrapper.current_visit_id !== visitId) return;
		if (!bundle) {
			fail(__("The EduEdge Institution Operations Settings bundle is unavailable or incomplete."));
			return;
		}
		$loading.remove();
		const root = $(
			'<div class="eduedge-institution-operations-settings-root" data-edge-product="eduedge"></div>'
		).appendTo(page.body);
		try {
			wrapper.vue_app = bundle.factory({
				pageName: "eduedge-institution-operations-settings",
			});
			wrapper.vue_app.mount(root[0]);
		} catch (error) {
			console.error("Failed to mount EduEdge Institution Operations Settings", error);
			fail(error.message || String(error));
		}
	};

	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		const runtime = window.EdgeSuiteUI || window.EdgeUI;
		if (!runtime?.install || !runtime?.components?.EdgeAppShell) {
			fail(__("The standalone EdgeSuite UI runtime is unavailable or incomplete."));
			return;
		}

		frappe.require("eduedge_institution_operations_settings.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			waitForInstitutionOperationsBundle(mount);
		});
	});
};
