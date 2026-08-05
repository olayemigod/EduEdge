frappe.pages["eduedge-program-offerings"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Programme Offerings"),
		single_column: true,
	});
};

function selected_offering_context(wrapper) {
	const proxy = wrapper.vue_app?._instance?.proxy;
	const draft = proxy?.draft || {};
	const filters = proxy?.filters || {};
	return {
		branch: draft.school_branch || filters.branch || "",
		offering: draft.name || "",
	};
}

function open_offering_operation(wrapper, route) {
	const context = selected_offering_context(wrapper);
	const params = new URLSearchParams();
	if (context.branch) params.set("branch", context.branch);
	if (context.offering) params.set("offering", context.offering);
	window.location.href = `${route}${params.toString() ? `?${params.toString()}` : ""}`;
}

function add_offering_operation_buttons(wrapper) {
	const page = wrapper.page;
	page.clear_inner_toolbar?.();
	page.add_inner_button(
		__("Manage Curriculum"),
		() => open_offering_operation(wrapper, "/app/eduedge-curriculum"),
		__("Class Operations")
	);
	page.add_inner_button(
		__("Assign Teachers"),
		() => open_offering_operation(wrapper, "/app/eduedge-instructor-assignments"),
		__("Class Operations")
	);
}

frappe.pages["eduedge-program-offerings"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge Programme Offerings", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(
		`<div class="p-6 text-center text-muted">${__("Loading Programme Offerings...")}</div>`
	).appendTo(page.body);

	const fail = (message) => {
		$loading.remove();
		$(
			`<div class="alert alert-danger p-6 text-center">
				<strong>${__("Programme Offerings failed to load")}</strong>
				<div>${frappe.utils.escape_html(message || "")}</div>
			</div>`
		).appendTo(page.body);
	};

	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		frappe.require("eduedge_programme_offerings.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (
				!window.EduEdgeProgrammeOfferings ||
				typeof window.createEduEdgeProgrammeOfferingsApp !== "function"
			) {
				fail(__("The EduEdge Programme Offerings bundle is unavailable or incomplete."));
				return;
			}
			$loading.remove();
			const root = $(
				'<div class="eduedge-programme-offerings-root" data-edge-product="eduedge"></div>'
			).appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeProgrammeOfferingsApp({
					pageName: "eduedge-program-offerings",
				});
				wrapper.vue_app.mount(root[0]);
				add_offering_operation_buttons(wrapper);
			} catch (error) {
				console.error("Failed to mount EduEdge Programme Offerings", error);
				fail(error.message || String(error));
			}
		});
	});
};
