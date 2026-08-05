frappe.pages["eduedge-instructor-assignments"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({ parent: wrapper, title: __("Teacher Assignments"), single_column: true });
};

function apply_teacher_assignment_route_context(wrapper, visitId) {
	const params = new URLSearchParams(window.location.search || "");
	const offering = params.get("offering") || params.get("program_offering") || "";
	const studentGroup = params.get("student_group") || "";
	const course = params.get("course") || "";
	if (!offering && !studentGroup && !course) return;

	let attempts = 0;
	const apply = async () => {
		if (wrapper.current_visit_id !== visitId || !wrapper.vue_app) return;
		const proxy = wrapper.vue_app?._instance?.proxy;
		if (!proxy || !proxy.loaded) {
			attempts += 1;
			if (attempts < 100) window.setTimeout(apply, 50);
			return;
		}
		proxy.form.assignment_scope = studentGroup ? proxy.classArmScope : proxy.classScope;
		proxy.form.program_offerings = offering ? [offering] : [];
		proxy.form.student_groups = studentGroup ? [studentGroup] : [];
		proxy.form.courses = course ? [course] : [];
		proxy.invalidatePreview?.();
		try {
			await proxy.load?.();
		} catch (error) {
			console.error("Failed to apply Teacher Assignment route context", error);
		}
	};
	window.setTimeout(apply, 0);
}

function teacher_assignment_factory() {
	return window.createEduEdgeTeacherAssignmentsApp || window.createEduEdgeInstructorAssignmentsApp;
}

function teacher_assignment_component() {
	return window.EduEdgeTeacherAssignments || window.EduEdgeInstructorAssignments;
}

function mount_teacher_assignments(wrapper, visitId, page, $loading, fail) {
	if (wrapper.current_visit_id !== visitId) return;
	const factory = teacher_assignment_factory();
	if (!teacher_assignment_component() || typeof factory !== "function") {
		return fail(
			__("The EduEdge Teacher Assignments bundle did not register correctly. Rebuild EduEdge assets and hard-refresh the browser.")
		);
	}

	$loading.remove();
	const root = $('<div class="eduedge-instructor-assignments-root" data-edge-product="eduedge"></div>').appendTo(page.body);
	try {
		wrapper.vue_app = factory({ pageName: "eduedge-instructor-assignments" });
		wrapper.vue_app.mount(root[0]);
		apply_teacher_assignment_route_context(wrapper, visitId);
	} catch (error) {
		console.error("Failed to mount Teacher Assignments", error);
		fail(error.message || String(error));
	}
}

frappe.pages["eduedge-instructor-assignments"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;
	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount Teacher Assignments", error);
		}
		wrapper.vue_app = null;
	}
	$(page.body).empty();
	const $loading = $(`<div class="p-6 text-center text-muted">${__("Loading Teacher Assignments...")}</div>`).appendTo(page.body);
	const fail = (message) => {
		$loading.remove();
		$(`<div class="alert alert-danger p-6 text-center"><strong>${__("Teacher Assignments failed to load")}</strong><div>${frappe.utils.escape_html(message || "")}</div></div>`).appendTo(page.body);
	};
	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		frappe.require("eduedge_teacher_assignments.bundle.js", () => {
			mount_teacher_assignments(wrapper, visitId, page, $loading, fail);
		});
	});
};
