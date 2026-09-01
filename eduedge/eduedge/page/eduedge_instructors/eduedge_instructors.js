frappe.pages["eduedge-instructors"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({ parent: wrapper, title: __("Instructors"), single_column: true });
};

function instructor_profiles_factory() {
	return window.createEduEdgeInstructorProfilesApp || window.createEduEdgeInstructorsApp;
}

function instructor_profiles_component() {
	return window.EduEdgeInstructorProfiles || window.EduEdgeInstructors;
}

function mount_instructor_profiles(wrapper, visitId, page, $loading, fail) {
	if (wrapper.current_visit_id !== visitId) return;
	const factory = instructor_profiles_factory();
	if (!instructor_profiles_component() || typeof factory !== "function") {
		return fail(
			__("The EduEdge Instructors bundle did not register correctly. Rebuild EduEdge assets and hard-refresh the browser.")
		);
	}

	$loading.remove();
	const root = $('<div class="eduedge-instructors-root" data-edge-product="eduedge"></div>').appendTo(page.body);
	try {
		wrapper.vue_app = factory({ pageName: "eduedge-instructors" });
		wrapper.vue_app.mount(root[0]);
	} catch (error) {
		console.error("Failed to mount EduEdge Instructors", error);
		fail(error.message || String(error));
	}
}

function load_instructor_profiles_bundle(
	wrapper,
	visitId,
	page,
	$loading,
	fail,
	primaryBundle,
	legacyBundle
) {
	frappe.require(primaryBundle, () => {
		if (wrapper.current_visit_id !== visitId) return;
		if (instructor_profiles_component() && typeof instructor_profiles_factory() === "function") {
			mount_instructor_profiles(wrapper, visitId, page, $loading, fail);
			return;
		}

		frappe.require(legacyBundle, () => {
			mount_instructor_profiles(wrapper, visitId, page, $loading, fail);
		});
	});
}

frappe.pages["eduedge-instructors"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;
	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge Instructors", error);
		}
		wrapper.vue_app = null;
	}
	$(page.body).empty();
	const $loading = $(`<div class="p-6 text-center text-muted">${__("Loading Instructors...")}</div>`).appendTo(page.body);
	const fail = (message) => {
		$loading.remove();
		$(`<div class="alert alert-danger p-6 text-center"><strong>${__("Instructors failed to load")}</strong><div>${frappe.utils.escape_html(message || "")}</div></div>`).appendTo(page.body);
	};
	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		load_instructor_profiles_bundle(
			wrapper,
			visitId,
			page,
			$loading,
			fail,
			"eduedge_instructor_profiles.bundle.js",
			"eduedge_instructors.bundle.js"
		);
	});
};
