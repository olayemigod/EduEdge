frappe.pages["eduedge-program-offerings"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Programme Offerings"),
		single_column: true,
	});
};

const SESSION_OPTIONS_METHOD = "eduedge.api.programme_offering_session_options.get_programme_offering_session_options";
const SESSION_PAGE_METHOD = "eduedge.api.programme_offering_session_options.get_programme_offerings_page_with_sessions";
const SESSION_OPTION_SETTLE_INTERVAL_MS = 50;
const SESSION_OPTION_SETTLE_ATTEMPTS = 80;

function selected_session_option(proxy, result = null) {
	const year = String(proxy?.draft?.academic_year || "").trim();
	if (!year) return null;
	const options = result?.options?.academic_years || proxy?.draftOptions?.academic_years || [];
	return options.find((row) => row.name === year) || null;
}

function calendar_setup_warning(proxy, result) {
	const year = String(proxy?.draft?.academic_year || "").trim();
	if (!year) return "";
	const selected = selected_session_option(proxy, result);
	if (!selected || selected.calendar_ready) return "";
	return __(
		`Academic Session ${year} has no Institution calendar mapping yet. ` +
		"EduEdge will prepare it automatically from the dated Terms configured under Academic Sessions & Terms when this Class Intake is saved."
	);
}

function prompt_missing_calendar(proxy, result) {
	const year = String(proxy?.draft?.academic_year || "").trim();
	const selected = selected_session_option(proxy, result);
	if (!year || !selected || selected.calendar_ready) {
		if (proxy) proxy.__eduedge_calendar_prompt_year = "";
		return;
	}
	if (proxy.__eduedge_calendar_prompt_year === year) return;
	proxy.__eduedge_calendar_prompt_year = year;

	frappe.msgprint({
		title: __("Institution Calendar Will Be Prepared"),
		indicator: "blue",
		message: __(
			`Academic Session ${year} is already selectable. This Institution does not yet have its operational calendar mapping, ` +
			"so EduEdge will create it automatically from the Session's dated Terms when you save the Class Intake. If the Terms are incomplete, the save will identify what still needs attention."
		),
		primary_action: {
			label: __("Review Academic Sessions & Terms"),
			action: () => frappe.set_route("eduedge-academic-sessions"),
		},
	});
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
			if (String(proxy.saveError || "").startsWith("Academic Session ")) proxy.saveError = "";
			prompt_missing_calendar(proxy, result);
		} else {
			proxy.__eduedge_calendar_prompt_year = "";
			if (String(proxy.saveError || "").startsWith("Academic Session ")) proxy.saveError = "";
		}
		return result;
	} catch (error) {
		proxy.saveError = error?.message || __("Class Intake setup options could not be loaded.");
		return null;
	}
}

async function load_session_filtered_page(proxy, resetStart = false, useActiveBranch = false) {
	if (!proxy) return null;
	const requestedFilters = { ...(proxy.filters || {}) };
	const selectedYear = String(requestedFilters.academic_year || "").trim();
	if (resetStart && proxy.data?.paging) proxy.data.paging.start = 0;
	const start = Number(proxy.data?.paging?.start || 0);
	const pageLength = Number(proxy.data?.paging?.page_length || 25);

	proxy.loading = true;
	proxy.error = "";
	try {
		const response = await frappe.call(SESSION_PAGE_METHOD, {
			...requestedFilters,
			use_active_branch: useActiveBranch ? 1 : 0,
			start,
			page_length: pageLength,
		});
		const result = response.message || {};
		const returnedYear = String(result?.filters?.academic_year || "").trim();
		if (selectedYear && returnedYear !== selectedYear) {
			throw new Error(__(`Academic Session filter ${selectedYear} was not preserved by the Class Intake service.`));
		}
		if (selectedYear && (result.offerings || []).some((row) => String(row.academic_year || "").trim() !== selectedYear)) {
			throw new Error(__(`Class Intake returned records outside Academic Session ${selectedYear}.`));
		}

		proxy.data = result;
		proxy.filters = { ...requestedFilters, ...(result.filters || {}) };
		proxy.loadedOnce = true;
		if (!proxy.draft?.institution) proxy.draft.institution = proxy.filters.institution || proxy.activeContext?.institution || "";
		if (!proxy.draft?.school_branch) proxy.draft.school_branch = proxy.filters.branch || proxy.activeContext?.branch || "";
		if (!proxy.draftOptions?.institutions?.length) proxy.draftOptions = { ...(proxy.draftOptions || {}), ...(result.options || {}) };
		if (!Object.keys(proxy.draftContext || {}).length) proxy.draftContext = proxy.activeContext || {};
		return result;
	} catch (error) {
		proxy.error = error?.message || __("Class Intakes could not be filtered.");
		return null;
	} finally {
		proxy.loading = false;
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

function apply_launch_query_filters(proxy) {
	if (!proxy) return false;
	const params = new URLSearchParams(window.location.search || "");
	const academicYear = String(params.get("destination_academic_year") || params.get("academic_year") || "").trim();
	const institution = String(params.get("institution") || "").trim();
	const branch = String(params.get("branch") || "").trim();
	if (!academicYear && !institution && !branch) return false;
	proxy.filters = {
		...(proxy.filters || {}),
		academic_year: academicYear || proxy.filters?.academic_year || "",
		institution: institution || proxy.filters?.institution || "",
		branch: branch || proxy.filters?.branch || "",
	};
	if (proxy.draft) {
		if (institution) proxy.draft.institution = institution;
		if (branch) proxy.draft.school_branch = branch;
		if (academicYear) proxy.draft.academic_year = academicYear;
	}
	return true;
}

function install_session_option_loader(proxy) {
	if (!proxy || proxy.__eduedge_session_option_loader_installed) return;
	proxy.__eduedge_session_option_loader_installed = true;

	const hasLaunchFilters = apply_launch_query_filters(proxy);
	wait_for_component_load(proxy).then(async () => {
		if (hasLaunchFilters) await load_session_filtered_page(proxy, true, false);
		await refresh_session_options(proxy);
	});

	proxy.loadDraftOptions = async function () {
		return refresh_session_options(proxy);
	};
	proxy.load = async function (resetStart = false, useActiveBranch = false) {
		return load_session_filtered_page(proxy, resetStart, useActiveBranch);
	};
	proxy.applyFilters = async function () {
		return load_session_filtered_page(proxy, true, false);
	};
	proxy.filterYearChanged = async function () {
		return load_session_filtered_page(proxy, true, false);
	};

	if (typeof proxy.saveOffering === "function") {
		const originalSaveOffering = proxy.saveOffering.bind(proxy);
		proxy.saveOffering = async function () {
			const saved = await originalSaveOffering();
			if (saved) {
				proxy.__eduedge_calendar_prompt_year = "";
				await refresh_session_options(proxy);
			}
			return saved;
		};
	}
}

frappe.pages["eduedge-program-offerings"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;
	page.clear_inner_toolbar?.();
	page.clear_primary_action?.();

	if (wrapper.vue_app) {
		try { wrapper.vue_app.unmount(); }
		catch (error) { console.error("Failed to unmount EduEdge Class Intakes", error); }
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(`<div class="p-6 text-center text-muted">${__("Loading Class Intakes...")}</div>`).appendTo(page.body);
	const fail = (message) => {
		$loading.remove();
		$(`<div class="alert alert-danger p-6 text-center"><strong>${__("Class Intakes failed to load")}</strong><div>${frappe.utils.escape_html(message || "")}</div></div>`).appendTo(page.body);
	};

	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		frappe.require("eduedge_programme_offerings.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (!window.EduEdgeProgrammeOfferings || typeof window.createEduEdgeProgrammeOfferingsApp !== "function") {
				fail(__("The EduEdge Class Intakes bundle is unavailable or incomplete."));
				return;
			}
			$loading.remove();
			const root = $('<div class="eduedge-programme-offerings-root" data-edge-product="eduedge"></div>').appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeProgrammeOfferingsApp({ pageName: "eduedge-program-offerings" });
				wrapper.vue_app.mount(root[0]);
				install_session_option_loader(wrapper.vue_app?._instance?.proxy);
			} catch (error) {
				console.error("Failed to mount EduEdge Class Intakes", error);
				fail(error.message || String(error));
			}
		});
	});
};
