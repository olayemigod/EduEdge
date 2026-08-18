frappe.pages["eduedge-institution-profile"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Institution Profile"),
		single_column: true,
	});
};

frappe.pages["eduedge-institution-profile"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount Institution Profile", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(
		`<div class="p-6 text-center text-muted">${__("Loading Institution Profile...")}</div>`
	).appendTo(page.body);
	const fail = (message) => {
		$loading.remove();
		$(
			`<div class="alert alert-danger p-6 text-center"><strong>${__(
				"Institution Profile failed to load"
			)}</strong><div>${frappe.utils.escape_html(message || "")}</div></div>`
		).appendTo(page.body);
	};

	const mountProfile = () => {
		if (wrapper.current_visit_id !== visitId) return;
		if (
			!window.EduEdgeInstitutionProfile ||
			typeof window.createEduEdgeInstitutionProfileApp !== "function"
		) {
			fail(
				__(
					"The EduEdge Institution profile runtime is unavailable. Rebuild EduEdge assets, clear cache, and hard-refresh the Desk."
				)
			);
			return;
		}
		$loading.remove();
		const root = $(
			'<div class="eduedge-institution-profile-root" data-edge-product="eduedge"></div>'
		).appendTo(page.body);
		try {
			wrapper.vue_app = window.createEduEdgeInstitutionProfileApp({
				pageName: "eduedge-institution-profile",
			});
			wrapper.vue_app.mount(root[0]);
		} catch (error) {
			console.error("Failed to mount Institution Profile", error);
			fail(error.message || String(error));
		}
	};

	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		if (window.createEduEdgeInstitutionProfileApp) {
			mountProfile();
			return;
		}
		frappe.require("eduedge_profile_identity.bundle.js", mountProfile);
	});
};
