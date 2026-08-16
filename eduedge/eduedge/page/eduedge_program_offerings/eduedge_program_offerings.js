frappe.pages["eduedge-program-offerings"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Programme Offerings"),
		single_column: true,
	});
};

const SESSION_OPTIONS_METHOD = "eduedge.api.programme_offering_session_options.get_programme_offering_session_options";
const SESSION_OPTION_SETTLE_INTERVAL_MS = 50;
const SESSION_OPTION_SETTLE_ATTEMPTS = 80;

function calendar_setup_warning(proxy, result) {
	const year = String(proxy?.draft?.academic_year || "").trim();
	if (!year) return "";
	const selected = (result?.options?.academic_years || []).find((row) => row.name === year);
	if (!selected || selected.calendar_ready) return "";
	return __(
		`Academic Session ${year} exists, but its Institution Academic Calendar is not configured yet. ` +
		"You can select the Session now; configure its Terms / Semesters under Academic Sessions & Terms before saving or using this Class Intake."
	);
}

async function refresh_session_options(proxy) {
	if (!proxy) return null;
	try {
		const response = await frappe.call(SESSION_OPTIONS_METHOD, {
			institution: proxy.draft?.institution || undefined,
			branch: proxy.draft?.school_branch || undefined,
			academic_year: proxy.draft?.academic_year || undefined,
		});
		const result = response.message || {};
		const options = result.options || {};

		proxy.draftOptions = { ...(proxy.draftOptions || {}), ...options };
		proxy.draftContext = result.active_context || proxy.activeContext || {};
		proxy.data = {
			...(proxy.data || {}),
			options: {
				...(proxy.data?.options || {}),
				academic_years: options.academic_years || [],
			},
		};

		const warning = calendar_setup_warning(proxy, result);
		if (warning) {
			proxy.saveError = warning;
		} else if (String(proxy.saveError || "").startsWith("Academic Session ")) {
			proxy.saveError = "";
		}
		return result;
	} catch (error) {
		proxy.saveError = error?.message || __("Class Intake setup options could not be loaded.");
		return null;
	}
}

function wait_for_component_load(proxy) {
	return new Promise((resolve) => {
		let attempts = 0;
		const check = () => {
			attempts += 1;
			if (!proxy?.loading || attempts >= SESSION_OPTION_SETTLE_ATTEMPTS) {
				resolve();
				return;
			}
			setTimeout(check, SESSION_OPTION_SETTLE_INTERVAL_MS);
		};
		check();
	});
}

function install_session_option_loader(proxy) {
	if (!proxy || proxy.__eduedge_session_option_loader_installed) return;
	proxy.__eduedge_session_option_loader_installed = true;

	// The Vue component starts its first page request during mount. That request
	// can complete after this hook and overwrite draft/data options. Wait for the
	// initial load to settle, then apply the canonical all-session source.
	wait_for_component_load(proxy).then(() => refresh_session_options(proxy));

	// All subsequent editor option refreshes use the all-session source directly.
	proxy.loadDraftOptions = async function () {
		return refresh_session_options(proxy);
	};

	// Page/filter refreshes still need the canonical API for the offering list,
	// but re-apply all Academic Sessions after that request finishes so the filter
	// cannot regress to calendar-ready sessions only.
	if (typeof proxy.load === "function") {
		const originalLoad = proxy.load.bind(proxy);
		proxy.load = async function (...args) {
			const result = await originalLoad(...args);
			await refresh_session_options(proxy);
			return result;
		};
	}
}

frappe.pages["eduedge-program-offerings"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	// Keep Class Intakes as one EdgeSuite setup workflow. Curriculum and
	// Instructor Assignment are separate workflows and must not create a second
	// toolbar/panel above the app shell.
	page.clear_inner_toolbar?.();
	page.clear_primary_action?.();

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge Class Intakes", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(
		`<div class="p-6 text-center text-muted">${__("Loading Class Intakes...")}</div>`
	).appendTo(page.body);

	const fail = (message) => {
		$loading.remove();
		$(
			`<div class="alert alert-danger p-6 text-center">
				<strong>${__("Class Intakes failed to load")}</strong>
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
				fail(__("The EduEdge Class Intakes bundle is unavailable or incomplete."));
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
				install_session_option_loader(wrapper.vue_app?._instance?.proxy);
			} catch (error) {
				console.error("Failed to mount EduEdge Class Intakes", error);
				fail(error.message || String(error));
			}
		});
	});
};
