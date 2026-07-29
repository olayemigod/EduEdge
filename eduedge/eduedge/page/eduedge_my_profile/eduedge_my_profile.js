frappe.pages["eduedge-my-profile"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("My Profile"),
		single_column: true,
	});
};

frappe.pages["eduedge-my-profile"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount My Profile", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(
		`<div class="p-6 text-center text-muted">${__("Loading My Profile...")}</div>`
	).appendTo(page.body);
	const fail = (message) => {
		$loading.remove();
		$(
			`<div class="alert alert-danger p-6 text-center"><strong>${__(
				"My Profile failed to load"
			)}</strong><div>${frappe.utils.escape_html(message || "")}</div></div>`
		).appendTo(page.body);
	};

	const mountProfile = () => {
		if (wrapper.current_visit_id !== visitId) return;
		if (!window.EduEdgeMyProfile || typeof window.createEduEdgeMyProfileApp !== "function") {
			fail(
				__(
					"The EduEdge profile runtime is unavailable. Rebuild EduEdge assets, clear cache, and hard-refresh the Desk."
				)
			);
			return;
		}
		$loading.remove();
		const root = $(
			'<div class="eduedge-my-profile-root" data-edge-product="eduedge"></div>'
		).appendTo(page.body);
		try {
			wrapper.vue_app = window.createEduEdgeMyProfileApp({ pageName: "eduedge-my-profile" });
			wrapper.vue_app.mount(root[0]);
		} catch (error) {
			console.error("Failed to mount My Profile", error);
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
		if (window.createEduEdgeMyProfileApp) {
			mountProfile();
			return;
		}
		frappe.require("eduedge_profile_identity.bundle.js", mountProfile);
	});
};
