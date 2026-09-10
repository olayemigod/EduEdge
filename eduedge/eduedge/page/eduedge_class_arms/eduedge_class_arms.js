function configure_class_arm_fuzzy_search() {
	const component = window.EduEdgeClassArms;
	if (!component?.methods) return;

	component.methods.load = async function (resetStart = false) {
		if (resetStart) this.data.paging.start = 0;
		this.loading = true;
		this.error = "";
		try {
			const response = await frappe.call("eduedge.api.class_arm_fuzzy.get_class_arms_page", {
				...this.filters,
				start: this.data.paging.start || 0,
				page_length: this.data.paging.page_length || 25,
			});
			this.data = response.message || this.data;
			this.filters = { ...this.filters, ...(this.data.filters || {}) };
			this.loadedOnce = true;
			if (!this.draft.branch) this.draft.branch = this.filters.branch || "";
			if (!this.bulk.branch) this.bulk.branch = this.filters.branch || "";
		} catch (error) {
			this.error = error?.message || `${this.classArmPlural} could not be loaded.`;
		} finally {
			this.loading = false;
		}
	};
}

frappe.pages["eduedge-class-arms"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Class Arms"),
		single_column: true,
	});
};

frappe.pages["eduedge-class-arms"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge Class Arms", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(
		`<div class="p-6 text-center text-muted">${__("Loading Class Arms...")}</div>`
	).appendTo(page.body);

	const fail = (message) => {
		$loading.remove();
		$(
			`<div class="alert alert-danger p-6 text-center">
				<strong>${__("Class Arms failed to load")}</strong>
				<div>${frappe.utils.escape_html(message || "")}</div>
			</div>`
		).appendTo(page.body);
	};

	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		frappe.require("eduedge_class_arms.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (!window.EduEdgeClassArms || typeof window.createEduEdgeClassArmsApp !== "function") {
				fail(__("The EduEdge Class Arms bundle is unavailable or incomplete."));
				return;
			}
			configure_class_arm_fuzzy_search();
			$loading.remove();
			const root = $('<div class="eduedge-class-arms-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeClassArmsApp({ pageName: "eduedge-class-arms" });
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount EduEdge Class Arms", error);
				fail(error.message || String(error));
			}
		});
	});
};
