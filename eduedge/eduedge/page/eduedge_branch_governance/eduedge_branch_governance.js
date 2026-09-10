const BRANCH_BUNDLE_READY_TIMEOUT_MS = 1500;
const BRANCH_BUNDLE_READY_POLL_MS = 50;

function getBranchGovernanceBundle() {
	const component = window.EduEdgeBranchGovernance;
	const factory = window.createEduEdgeBranchGovernanceApp;
	if (!component || typeof factory !== "function") return null;
	return { component, factory };
}

function waitForBranchGovernanceBundle(callback, startedAt = Date.now()) {
	const bundle = getBranchGovernanceBundle();
	if (bundle) {
		callback(bundle);
		return;
	}
	if (Date.now() - startedAt >= BRANCH_BUNDLE_READY_TIMEOUT_MS) {
		callback(null);
		return;
	}
	setTimeout(
		() => waitForBranchGovernanceBundle(callback, startedAt),
		BRANCH_BUNDLE_READY_POLL_MS
	);
}

frappe.pages["eduedge-branch-governance"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Branch Governance and Accounting"),
		single_column: true,
	});
};

frappe.pages["eduedge-branch-governance"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge Branch Governance", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(
		`<div class="p-6 text-center text-muted">${__("Loading branch governance...")}</div>`
	).appendTo(page.body);

	const fail = (message) => {
		if (wrapper.current_visit_id !== visitId) return;
		$loading.remove();
		$(
			`<div class="alert alert-danger p-6 text-center">
				<strong>${__("Branch governance failed to load")}</strong>
				<div>${frappe.utils.escape_html(message || "")}</div>
			</div>`
		).appendTo(page.body);
	};

	const mount = (bundle) => {
		if (wrapper.current_visit_id !== visitId) return;
		if (!bundle) {
			fail(__("The EduEdge Branch Governance bundle is unavailable or incomplete."));
			return;
		}
		$loading.remove();
		const root = $(
			'<div class="eduedge-branch-governance-root" data-edge-product="eduedge"></div>'
		).appendTo(page.body);
		try {
			wrapper.vue_app = bundle.factory({
				pageName: "eduedge-branch-governance",
			});
			wrapper.vue_app.mount(root[0]);
		} catch (error) {
			console.error("Failed to mount EduEdge Branch Governance", error);
			fail(error.message || String(error));
		}
	};

	// The legacy `edgeui.bundle.js` manifest key is intentionally not loaded.
	// Mixed-app sites must resolve the collision-safe standalone runtime instead.
	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		const runtime = window.EdgeSuiteUI || window.EdgeUI;
		if (!runtime?.install || !runtime?.components?.EdgeAppShell) {
			fail(__("The standalone EdgeSuite UI runtime is unavailable or incomplete."));
			return;
		}

		frappe.require("eduedge_branch_governance.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			waitForBranchGovernanceBundle(mount);
		});
	});
};
