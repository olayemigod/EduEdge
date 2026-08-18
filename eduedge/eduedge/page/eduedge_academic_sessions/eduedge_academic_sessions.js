frappe.pages["eduedge-academic-sessions"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Academic Sessions and Terms"),
		single_column: true,
	});
};

frappe.pages["eduedge-academic-sessions"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	if (wrapper.session_launch_app) {
		try {
			wrapper.session_launch_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge Session Launch", error);
		}
		wrapper.session_launch_app = null;
	}

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge Academic Sessions", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(
		`<div class="p-6 text-center text-muted">${__("Loading Academic Sessions and Terms...")}</div>`
	).appendTo(page.body);

	const fail = (message) => {
		$loading.remove();
		$(
			`<div class="alert alert-danger p-6 text-center">
				<strong>${__("Academic Sessions and Terms failed to load")}</strong>
				<div>${frappe.utils.escape_html(message || "")}</div>
			</div>`
		).appendTo(page.body);
	};

	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		frappe.require("eduedge_academic_sessions.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (!window.EduEdgeAcademicSessions || typeof window.createEduEdgeAcademicSessionsApp !== "function") {
				fail(__("The EduEdge Academic Sessions bundle is unavailable or incomplete."));
				return;
			}
			$loading.remove();
			const launchRoot = $('<div class="eduedge-session-launch-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			const root = $('<div class="eduedge-academic-sessions-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeAcademicSessionsApp({
					pageName: "eduedge-academic-sessions",
				});
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				console.error("Failed to mount EduEdge Academic Sessions", error);
				fail(error.message || String(error));
				return;
			}

			// Session Launch is additive: if its new bundle fails, manual Session/Term
			// management remains available below instead of taking down the page.
			frappe.require("eduedge_session_launch.bundle.js", () => {
				if (wrapper.current_visit_id !== visitId) return;
				if (!window.EduEdgeSessionLaunch || typeof window.createEduEdgeSessionLaunchApp !== "function") {
					launchRoot.html(
						`<div class="alert alert-warning">${__("Guided Session Launch is unavailable. Manual Academic Session management remains available below.")}</div>`
					);
					return;
				}
				try {
					wrapper.session_launch_app = window.createEduEdgeSessionLaunchApp({
						pageName: "eduedge-academic-sessions",
					});
					wrapper.session_launch_app.mount(launchRoot[0]);
				} catch (error) {
					console.error("Failed to mount EduEdge Session Launch", error);
					launchRoot.html(
						`<div class="alert alert-warning">${frappe.utils.escape_html(error.message || String(error))}</div>`
					);
				}
			});
		});
	});
};
