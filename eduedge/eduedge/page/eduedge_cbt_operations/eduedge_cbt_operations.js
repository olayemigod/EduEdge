const CBT_CONFIGURE_ROLES = new Set([
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Public Exam Administrator",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
	"Teacher",
	"Instructor",
]);

const CBT_CREATE_OPTIONS = [
	{
		doctype: "EduEdge Examination Centre",
		label: "Examination Centre",
		description: "Set up a school CBT centre and manage its operational status.",
	},
	{
		doctype: "EduEdge CBT Question",
		label: "Question",
		description: "Add a governed question to the school Question Bank.",
	},
	{
		doctype: "EduEdge CBT Exam Template",
		label: "Exam Template",
		description: "Create a reusable examination definition from approved questions.",
	},
];

function canConfigureCBT() {
	if (frappe.session.user === "Administrator") return true;
	return (frappe.user_roles || []).some((role) => CBT_CONFIGURE_ROLES.has(role));
}

function showCreateDialog() {
	if (!canConfigureCBT()) return;

	const dialog = new frappe.ui.Dialog({
		title: __("Create New"),
		fields: [{ fieldname: "create_options", fieldtype: "HTML" }],
	});
	const escape = frappe.utils.escape_html;
	const cards = CBT_CREATE_OPTIONS.map(
		(option) => `
			<button type="button" class="btn btn-default btn-block text-left mb-3 p-3" data-create-doctype="${escape(option.doctype)}">
				<div class="font-weight-bold mb-1">${escape(__(option.label))}</div>
				<div class="text-muted small">${escape(__(option.description))}</div>
			</button>`
	).join("");

	$(dialog.fields_dict.create_options.wrapper).html(
		`<div class="eduedge-cbt-create-options">${cards}</div>`
	);
	$(dialog.fields_dict.create_options.wrapper)
		.find("[data-create-doctype]")
		.on("click", function () {
			const doctype = $(this).attr("data-create-doctype");
			dialog.hide();
			frappe.new_doc(doctype);
		});
	dialog.show();
}

function installHeaderCreateLauncher(root) {
	if (!canConfigureCBT() || !root) return;

	const acceptedLabels = new Set([
		"New Exam Template",
		__("New Exam Template"),
		"Create New",
		__("Create New"),
	]);
	const install = () => {
		const button = Array.from(root.querySelectorAll("button")).find((candidate) =>
			acceptedLabels.has((candidate.textContent || "").trim())
		);
		if (!button) return false;

		button.textContent = __("Create New");
		if (button.dataset.eduedgeCreateLauncher === "1") return true;
		button.dataset.eduedgeCreateLauncher = "1";
		button.addEventListener(
			"click",
			(event) => {
				event.preventDefault();
				event.stopPropagation();
				event.stopImmediatePropagation();
				showCreateDialog();
			},
			true
		);
		return true;
	};

	if (install()) return;
	const observer = new MutationObserver(() => {
		if (install()) observer.disconnect();
	});
	observer.observe(root, { childList: true, subtree: true });
	window.setTimeout(() => observer.disconnect(), 3000);
}

frappe.pages["eduedge-cbt-operations"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("EduEdge CBT"),
		single_column: true,
	});
};

frappe.pages["eduedge-cbt-operations"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	page.clear_inner_toolbar();
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge CBT Operations", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(
		`<div class="p-6 text-center text-muted">${__("Loading CBT operations...")}</div>`
	).appendTo(page.body);

	const fail = (message) => {
		$loading.remove();
		$(
			`<div class="alert alert-danger p-6 text-center">
				<strong>${__("CBT operations failed to load")}</strong>
				<div>${frappe.utils.escape_html(message || "")}</div>
			</div>`
		).appendTo(page.body);
	};

	frappe.require("edgeui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		const runtime = window.EdgeSuiteUI || window.EdgeUI;
		if (!runtime?.install || !runtime?.components?.EdgeAppShell) {
			fail(__("The standalone EdgeSuite UI runtime is unavailable or incomplete."));
			return;
		}

		frappe.require("eduedge_cbt_operations.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (
				!window.EduEdgeCBTOperations ||
				typeof window.createEduEdgeCBTOperationsApp !== "function"
			) {
				fail(__("The EduEdge CBT Operations bundle is unavailable or incomplete."));
				return;
			}
			$loading.remove();
			const root = $(
				'<div class="eduedge-cbt-operations-root" data-edge-product="eduedge"></div>'
			).appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeCBTOperationsApp({
					pageName: "eduedge-cbt-operations",
				});
				wrapper.vue_app.mount(root[0]);
				window.requestAnimationFrame(() => installHeaderCreateLauncher(root[0]));
			} catch (error) {
				console.error("Failed to mount EduEdge CBT Operations", error);
				fail(error.message || String(error));
			}
		});
	});
};
