frappe.pages["eduedge-instructor-assignments"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({ parent: wrapper, title: __("Instructor Assignments"), single_column: true });
};

function apply_instructor_assignment_route_context(wrapper, visitId) {
	const params = new URLSearchParams(window.location.search || "");
	const preset = {
		branch: params.get("branch") || "",
		program_offering: params.get("offering") || params.get("program_offering") || "",
		student_group: params.get("student_group") || "",
		course: params.get("course") || "",
	};
	if (!preset.branch && !preset.program_offering && !preset.student_group && !preset.course) return;

	let attempts = 0;
	const apply = async () => {
		if (wrapper.current_visit_id !== visitId || !wrapper.vue_app) return;
		const proxy = wrapper.vue_app?._instance?.proxy;
		if (!proxy || !proxy.loaded) {
			attempts += 1;
			if (attempts < 100) window.setTimeout(apply, 50);
			return;
		}
		try {
			proxy.applyRoutePreset?.(preset);
		} catch (error) {
			console.error("Failed to apply Instructor Assignment route context", error);
		}
	};
	window.setTimeout(apply, 0);
}

function instructor_assignment_factory() {
	return window.createEduEdgeInstructorAssignmentsApp || window.createEduEdgeTeacherAssignmentsApp;
}

function instructor_assignment_component() {
	return window.EduEdgeInstructorAssignments || window.EduEdgeTeacherAssignments;
}

function mount_instructor_assignments(wrapper, visitId, page, $loading, fail) {
	if (wrapper.current_visit_id !== visitId) return;
	const factory = instructor_assignment_factory();
	if (!instructor_assignment_component() || typeof factory !== "function") {
		return fail(
			__("The EduEdge Instructor Assignments bundle did not register correctly. Rebuild EduEdge assets and hard-refresh the browser.")
		);
	}

	$loading.remove();
	const root = $('<div class="eduedge-instructor-assignments-root" data-edge-product="eduedge"></div>').appendTo(page.body);
	try {
		wrapper.vue_app = factory({ pageName: "eduedge-instructor-assignments" });
		wrapper.vue_app.mount(root[0]);
		apply_instructor_assignment_route_context(wrapper, visitId);
	} catch (error) {
		console.error("Failed to mount Instructor Assignments", error);
		fail(error.message || String(error));
	}
}

function mount_instructor_assignments_with_register_filters(wrapper, visitId, page, $loading, fail) {
	frappe.require("eduedge_instructor_assignment_register_filters.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		if (typeof window.installInstructorAssignmentRegisterFilters === "function") {
			window.installInstructorAssignmentRegisterFilters(window.EduEdgeInstructorAssignments);
		}
		mount_instructor_assignments(wrapper, visitId, page, $loading, fail);
	});
}

function load_instructor_assignments_bundle(
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
		if (instructor_assignment_component() && typeof instructor_assignment_factory() === "function") {
			mount_instructor_assignments_with_register_filters(wrapper, visitId, page, $loading, fail);
			return;
		}

		frappe.require(legacyBundle, () => {
			mount_instructor_assignments(wrapper, visitId, page, $loading, fail);
		});
	});
}

frappe.pages["eduedge-instructor-assignments"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;
	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount Instructor Assignments", error);
		}
		wrapper.vue_app = null;
	}
	$(page.body).empty();
	const $loading = $(`<div class="p-6 text-center text-muted">${__("Loading Instructor Assignments...")}</div>`).appendTo(page.body);
	const fail = (message) => {
		$loading.remove();
		$(`<div class="alert alert-danger p-6 text-center"><strong>${__("Instructor Assignments failed to load")}</strong><div>${frappe.utils.escape_html(message || "")}</div></div>`).appendTo(page.body);
	};
	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		load_instructor_assignments_bundle(
			wrapper,
			visitId,
			page,
			$loading,
			fail,
			"eduedge_instructor_assignments.bundle.js",
			"eduedge_teacher_assignments.bundle.js"
		);
	});
};
