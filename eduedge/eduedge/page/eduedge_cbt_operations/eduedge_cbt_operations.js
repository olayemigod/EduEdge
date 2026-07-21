const CBT_CREATE_OPTIONS = [
	{
		label: "Examination Centre",
		description: "Set up a school CBT centre and manage its operational status.",
		route: "/app/eduedge-examination-centre/new-eduedge-examination-centre",
		edgesuite: false,
		resource: "examination_centre",
		permission: "create",
	},
	{
		label: "Single Question",
		description: "Create one governed question in the friendly EduEdge Question Builder.",
		route: "/app/eduedge-question-builder",
		edgesuite: true,
		resource: "cbt_question",
		permission: "create",
	},
	{
		label: "Multiple Questions",
		description: "Enter several questions with shared Branch, Subject, Topic and source details.",
		route: "/app/eduedge-question-batch?mode=entry",
		edgesuite: true,
		resource: "cbt_question",
		permission: "create",
	},
	{
		label: "Upload Questions",
		description: "Validate and import a prepared CSV or XLSX question file as Draft records.",
		route: "/app/eduedge-question-batch?mode=upload",
		edgesuite: true,
		resource: "cbt_question",
		permission: "create",
	},
	{
		label: "Exam Template",
		description: "Create a reusable examination definition from approved questions.",
		route: "/app/eduedge-cbt-exam-template/new-eduedge-cbt-exam-template",
		edgesuite: false,
		resource: "cbt_template",
		permission: "create",
	},
];

function resourceAllowed(resource, permission) {
	if (frappe.session.user === "Administrator") return true;
	return Boolean(frappe.boot?.eduedge_access_manifest?.resources?.[resource]?.[permission]);
}

function availableCreateOptions() {
	return CBT_CREATE_OPTIONS.filter((option) => resourceAllowed(option.resource, option.permission));
}

function openNativeDeskRouteInNewTab(route) {
	const url = new URL(route, window.location.origin);
	window.open(url.toString(), "_blank", "noopener,noreferrer");
}

function openCreateRoute(route, edgesuite) {
	if (edgesuite) {
		window.location.href = route;
		return;
	}
	openNativeDeskRouteInNewTab(route);
}

function showCreateDialog() {
	const options = availableCreateOptions();
	if (!options.length) return;

	const dialog = new frappe.ui.Dialog({
		title: __("Create New"),
		fields: [{ fieldname: "create_options", fieldtype: "HTML" }],
	});
	const escape = frappe.utils.escape_html;
	const cards = options.map(
		(option) => `
			<button type="button" class="btn btn-default btn-block text-left mb-3 p-3" data-create-route="${escape(option.route)}" data-create-edgesuite="${option.edgesuite ? "1" : "0"}">
				<div class="font-weight-bold mb-1">${escape(__(option.label))}</div>
				<div class="text-muted small">${escape(__(option.description))}</div>
				<div class="text-muted small mt-1">${escape(
					__(option.edgesuite ? "Opens in the EduEdge workspace" : "Opens in a new EduEdge Desk tab")
				)}</div>
			</button>`
	).join("");

	$(dialog.fields_dict.create_options.wrapper).html(
		`<div class="eduedge-cbt-create-options">${cards}</div>`
	);
	$(dialog.fields_dict.create_options.wrapper)
		.find("[data-create-route]")
		.on("click", function () {
			const route = $(this).attr("data-create-route");
			const edgesuite = $(this).attr("data-create-edgesuite") === "1";
			dialog.hide();
			openCreateRoute(route, edgesuite);
		});
	dialog.show();
}

function installHeaderCreateLauncher(root) {
	if (!availableCreateOptions().length || !root) return;

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

function publicAccessPreferenceKey() {
	return `eduedge:cbt-public-access-expanded:${frappe.session.user || "user"}`;
}

function readPublicAccessPreference() {
	try {
		return window.localStorage.getItem(publicAccessPreferenceKey());
	} catch (error) {
		return null;
	}
}

function writePublicAccessPreference(expanded) {
	try {
		window.localStorage.setItem(publicAccessPreferenceKey(), expanded ? "1" : "0");
	} catch (error) {
		// Private browsing or a restricted browser may disable local storage.
	}
}

function installPublicAccessDisclosure(root) {
	if (!root) return false;
	const panel = root.querySelector(".eduedge-cbt-access-panel");
	if (!panel) return false;
	if (panel.dataset.eduedgeAccessDisclosure === "1") return true;

	const heading = panel.querySelector(".eduedge-cbt-panel-heading");
	if (!heading) return false;

	const headingText = (heading.textContent || "").trim();
	const operationallyRelevant = /Authority Site|Capabilities Active/.test(headingText);
	const savedPreference = readPublicAccessPreference();
	let expanded = operationallyRelevant || savedPreference === "1";

	const toggle = document.createElement("button");
	toggle.type = "button";
	toggle.className = "edge-button eduedge-cbt-access-toggle";
	toggle.style.marginLeft = "auto";
	toggle.style.whiteSpace = "nowrap";

	const detailRows = Array.from(panel.children).filter((child) => child !== heading);
	const render = () => {
		for (const row of detailRows) row.hidden = !expanded;
		heading.style.marginBottom = expanded ? "1rem" : "0";
		heading.style.alignItems = "center";
		heading.style.flexWrap = "wrap";
		panel.style.paddingTop = expanded ? "" : "0.85rem";
		panel.style.paddingBottom = expanded ? "" : "0.85rem";
		toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
		toggle.textContent = expanded ? __("Hide access details") : __("Show access details");
	};

	toggle.addEventListener("click", () => {
		expanded = !expanded;
		writePublicAccessPreference(expanded);
		render();
	});

	heading.appendChild(toggle);
	panel.dataset.eduedgeAccessDisclosure = "1";
	render();
	return true;
}

function queuePublicAccessDisclosure(root) {
	if (installPublicAccessDisclosure(root)) return;
	const observer = new MutationObserver(() => {
		if (installPublicAccessDisclosure(root)) observer.disconnect();
	});
	observer.observe(root, { childList: true, subtree: true });
	window.setTimeout(() => observer.disconnect(), 5000);
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
				window.requestAnimationFrame(() => {
					installHeaderCreateLauncher(root[0]);
					queuePublicAccessDisclosure(root[0]);
				});
			} catch (error) {
				console.error("Failed to mount EduEdge CBT Operations", error);
				fail(error.message || String(error));
			}
		});
	});
};
