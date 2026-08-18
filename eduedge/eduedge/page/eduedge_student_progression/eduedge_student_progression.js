frappe.pages["eduedge-student-progression"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({ parent: wrapper, title: __("Student Progression"), single_column: true });
};

function ensure_student_progression_runtime_styles() {
	const href = "/assets/eduedge/css/eduedge_student_progression_runtime_fix.css";
	if (document.querySelector(`link[data-eduedge-student-progression-runtime][href="${href}"]`)) return;
	const link = document.createElement("link");
	link.rel = "stylesheet";
	link.href = href;
	link.setAttribute("data-eduedge-student-progression-runtime", "1");
	document.head.appendChild(link);
}

frappe.pages["eduedge-student-progression"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	ensure_student_progression_runtime_styles();
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;
	if (wrapper.vue_app) {
		try { wrapper.vue_app.unmount(); } catch (error) { console.error("Failed to unmount Student Progression", error); }
		wrapper.vue_app = null;
	}
	$(page.body).empty();
	const $loading = $(`<div class="p-6 text-center text-muted">${__("Loading Student Progression...")}</div>`).appendTo(page.body);
	const fail = (message) => {
		$loading.remove();
		$(`<div class="alert alert-danger p-6 text-center"><strong>${__("Student Progression failed to load")}</strong><div>${frappe.utils.escape_html(message || "")}</div></div>`).appendTo(page.body);
	};
	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		frappe.require("eduedge_student_progression.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (!window.EduEdgeStudentProgression || typeof window.createEduEdgeStudentProgressionApp !== "function") {
				return fail(__("The EduEdge Student Progression bundle is unavailable."));
			}
			$loading.remove();
			const root = $('<div class="eduedge-student-progression-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeStudentProgressionApp({ pageName: "eduedge-student-progression" });
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount Student Progression", error);
				fail(error.message || String(error));
			}
		});
	});
};
