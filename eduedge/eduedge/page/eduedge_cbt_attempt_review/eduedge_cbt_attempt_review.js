frappe.pages["eduedge-cbt-attempt-review"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("CBT Attempt Review"),
		single_column: true,
	});
};

frappe.pages["eduedge-cbt-attempt-review"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	page.clear_inner_toolbar();
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount CBT Attempt Review", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(`<div class="p-6 text-center text-muted">${__("Loading CBT attempt reviews…")}</div>`).appendTo(page.body);
	let completed = false;
	const fail = (message) => {
		if (completed || wrapper.current_visit_id !== visitId) return;
		completed = true;
		clearTimeout(loadTimeout);
		$loading.remove();
		$(`<div class="alert alert-danger p-6 text-center"><strong>${__("CBT attempt review failed to load")}</strong><div>${frappe.utils.escape_html(message || "")}</div></div>`).appendTo(page.body);
	};
	const loadTimeout = setTimeout(
		() => fail(__("The page assets did not finish loading. Rebuild EduEdge assets and clear the site cache.")),
		15000
	);

	frappe.require("edgeui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId || completed) return;
		const runtime = window.EdgeSuiteUI || window.EdgeUI;
		if (!runtime?.install || !runtime?.components?.EdgeAppShell) {
			fail(__("The standalone EdgeSuite UI runtime is unavailable or incomplete."));
			return;
		}
		frappe.require("eduedge_cbt_attempt_review.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId || completed) return;
			if (typeof window.createEduEdgeCBTAttemptReviewApp !== "function") {
				fail(__("The EduEdge CBT Attempt Review bundle is unavailable or incomplete."));
				return;
			}
			completed = true;
			clearTimeout(loadTimeout);
			$loading.remove();
			const root = $('<div class="eduedge-cbt-attempt-review-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeCBTAttemptReviewApp({ pageName: "eduedge-cbt-attempt-review" });
				wrapper.vue_app.mount(root[0]);
			} catch (error) {
				completed = false;
				console.error("Failed to mount CBT Attempt Review", error);
				fail(error.message || String(error));
			}
		});
	});
};
