const SCHOOL_FALLBACK_ICON = `
<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
	<path d="M4 21h16M5 21V9l7-5 7 5v12M9 21v-6h6v6M8 11h.01M12 11h.01M16 11h.01" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`;

const PRODUCT_FALLBACK_ICON = `
<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
	<path d="m3 8.5 9-4.5 9 4.5-9 4.5-9-4.5Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
	<path d="M7 10.5v4.2c0 1.4 2.2 2.8 5 2.8s5-1.4 5-2.8v-4.2M21 8.5v6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
</svg>`;

const EDGE_MANAGED_SURFACE_SELECTOR = [
	".edge-app-shell",
	".edge-sidebar",
	".edge-product-menu",
	".edge-product-menu__panel",
	".edge-product-menu-panel",
	"[data-edge-product-menu]",
].join(", ");

const ACTIVE_CONTEXT_METHOD = "eduedge.api.branch_context.get_active_branch_context";
const BRANCH_SWITCH_METHOD = "eduedge.api.branch_context.switch_school_branch";

let observer;
let scheduled = false;
let contextDialogOpening = false;

function getIdentity() {
	return globalThis.frappe?.boot?.eduedge_ui_identity || {};
}

function isEduEdgeSurface() {
	const path = window.location.pathname.replace(/\/+$/, "");
	return /\/(?:app|desk)\/eduedge-/.test(path) || /\/app\/(?:assessment-plan|assessment-result|assessment-group|program-enrollment|student-group|course-schedule|student-attendance|student-applicant|student|program|course)(?:\/|$)/.test(path);
}

function normalizedText(value) {
	return String(value || "").replace(/\s+/g, " ").trim();
}

function responseMessage(response) {
	return response?.message || response || {};
}

function markManagedTerminologySurfaces(root = document) {
	if (!root?.querySelectorAll) return;
	const elements = [];
	if (root.matches?.(EDGE_MANAGED_SURFACE_SELECTOR)) elements.push(root);
	elements.push(...root.querySelectorAll(EDGE_MANAGED_SURFACE_SELECTOR));
	for (const element of elements) {
		element.setAttribute("data-eduedge-terminology-managed", "1");
	}
}

function setText(element, value) {
	if (!element) return;
	const next = normalizedText(value);
	if (normalizedText(element.textContent) !== next) element.textContent = next;
}

function setMark(mark, logo, fallbackMarkup, altText) {
	if (!mark) return;
	const resolvedLogo = normalizedText(logo);
	const currentLogo = mark.dataset.eduedgeIdentityLogo || "";
	if (currentLogo === resolvedLogo && mark.dataset.eduedgeIdentityReady === "1") return;

	mark.replaceChildren();
	mark.dataset.eduedgeIdentityReady = "1";
	mark.dataset.eduedgeIdentityLogo = resolvedLogo;
	mark.classList.toggle("edge-identity-mark--image", Boolean(resolvedLogo));

	if (resolvedLogo) {
		const image = document.createElement("img");
		image.className = "edge-identity-logo";
		image.src = resolvedLogo;
		image.alt = altText || "";
		image.loading = "eager";
		image.decoding = "async";
		mark.appendChild(image);
		return;
	}

	mark.innerHTML = fallbackMarkup;
}

function ensureContextStyles() {
	if (document.getElementById("eduedge-active-context-style")) return;
	const style = document.createElement("style");
	style.id = "eduedge-active-context-style";
	style.textContent = `
		.eduedge-active-context { display:flex; align-items:center; gap:.45rem; flex-wrap:wrap; }
		.eduedge-active-context__item { display:grid; gap:.05rem; min-width:0; padding:.32rem .55rem; border:1px solid var(--border-color); border-radius:.6rem; background:var(--control-bg); }
		.eduedge-active-context__item small { color:var(--text-muted); font-size:.68rem; line-height:1; text-transform:uppercase; letter-spacing:.04em; }
		.eduedge-active-context__item strong { max-width:15rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:.78rem; }
		.eduedge-page-context-fallback { margin:.75rem 0 1rem; padding:.6rem; border:1px solid var(--border-color); border-radius:.75rem; background:var(--card-bg); }
		.eduedge-context-switcher { cursor:pointer; position:relative; padding-right:1.7rem !important; transition:border-color .15s ease, background .15s ease, box-shadow .15s ease; }
		.eduedge-context-switcher:hover { border-color:var(--primary); background:var(--control-bg); }
		.eduedge-context-switcher:focus-visible { outline:none; border-color:var(--primary); box-shadow:0 0 0 2px color-mix(in srgb, var(--primary) 22%, transparent); }
		.eduedge-context-switcher__caret { position:absolute; right:.55rem; top:50%; width:.42rem; height:.42rem; border-right:1.5px solid currentColor; border-bottom:1.5px solid currentColor; transform:translateY(-65%) rotate(45deg); opacity:.65; pointer-events:none; }
		.eduedge-context-switch-summary { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.65rem; margin-bottom:1rem; }
		.eduedge-context-switch-summary > div { display:grid; gap:.15rem; padding:.7rem; border:1px solid var(--border-color); border-radius:.65rem; background:var(--control-bg); }
		.eduedge-context-switch-summary span { color:var(--text-muted); font-size:.7rem; text-transform:uppercase; letter-spacing:.04em; }
		@media (max-width:720px) {
			.eduedge-active-context__item strong { max-width:9rem; }
			.eduedge-context-switch-summary { grid-template-columns:1fr; }
		}
	`;
	document.head.appendChild(style);
}

function contextMarkup({ includeBranch = true } = {}) {
	return `
		<div class="eduedge-active-context__item" data-eduedge-context="institution"><small>Institution</small><strong></strong></div>
		${includeBranch ? '<div class="eduedge-active-context__item" data-eduedge-context="branch"><small>Branch</small><strong></strong></div>' : ""}
	`;
}

function populateContext(strip, identity) {
	const context = identity.institution_context || globalThis.frappe?.boot?.eduedge_institution_context || {};
	setText(strip.querySelector('[data-eduedge-context="institution"] strong'), context.institution_name || identity.tenant_name || "Not selected");
	setText(strip.querySelector('[data-eduedge-context="branch"] strong'), context.branch_name || identity.branch_name || "Not selected");
}

function ensureActiveContext(topbar, identity) {
	let strip = topbar.querySelector(".eduedge-active-context");
	if (!strip) {
		strip = document.createElement("div");
		strip.className = "eduedge-active-context";
		strip.innerHTML = contextMarkup({ includeBranch: false });
		const host = topbar.querySelector(".edge-topbar-context, .edge-topbar__context, .edge-topbar__actions") || topbar;
		host.appendChild(strip);
	} else if (strip.querySelector('[data-eduedge-context="branch"]')) {
		strip.innerHTML = contextMarkup({ includeBranch: false });
	}
	populateContext(strip, identity);
}

function ensureFallbackContext(identity, hasTopbar) {
	const existing = document.querySelector(".eduedge-page-context-fallback");
	if (hasTopbar) {
		existing?.remove();
		return;
	}
	const host = document.querySelector(".layout-main-section, .page-content, main");
	if (!host) return;
	const fallback = existing || document.createElement("div");
	if (!existing) {
		fallback.className = "eduedge-page-context-fallback eduedge-active-context";
		fallback.innerHTML = contextMarkup({ includeBranch: true });
		host.prepend(fallback);
	}
	populateContext(fallback, identity);
}

function selectOptions(rows, labelField) {
	return (rows || []).map((row) => ({
		value: row.name,
		label: normalizedText(row[labelField] || row.name),
	}));
}

function institutionOptions(payload) {
	return selectOptions(payload.allowed_institutions, "institution_name");
}

function branchOptions(payload, institution) {
	const rows = (payload.allowed_branches || []).filter((row) => row.institution === institution);
	const options = rows.map((row) => ({
		value: row.name,
		label: normalizedText(`${row.branch_name || row.name}${row.branch_code ? ` · ${row.branch_code}` : ""}`),
	}));
	const canUseInstitutionScope = Boolean(
		payload.can_view_all_branches &&
		(payload.all_branch_institutions || []).includes(institution)
	);
	if (canUseInstitutionScope) {
		const institutionRow = (payload.allowed_institutions || []).find((row) => row.name === institution) || {};
		options.unshift({
			value: payload.all_branches_key || "__all__",
			label: `All Branches — ${institutionRow.institution_name || institution}`,
		});
	}
	return options;
}

function refreshSelectField(field, options) {
	if (!field) return;
	if (typeof field.set_data === "function") {
		field.set_data(options);
		return;
	}
	field.df.options = options;
	field.refresh?.();
}

function currentInstitution(payload) {
	return payload.current_branch?.institution || payload.active_institution || payload.institution_context?.institution || payload.allowed_institutions?.[0]?.name || "";
}

function currentBranchValue(payload, institution) {
	if (payload.current_branch?.is_all_branches && payload.current_branch?.institution === institution) {
		return payload.all_branches_key || "__all__";
	}
	const current = payload.current_branch?.name || "";
	if ((payload.allowed_branches || []).some((row) => row.name === current && row.institution === institution)) return current;
	return branchOptions(payload, institution)[0]?.value || "";
}

async function switchContext(dialog, payload) {
	const values = dialog.get_values();
	if (!values?.institution || !values?.branch) return;
	const institution = values.institution;
	const branchRow = (payload.allowed_branches || []).find((row) => row.name === values.branch) || {};
	const institutionRow = (payload.allowed_institutions || []).find((row) => row.name === institution) || {};
	try {
		dialog.get_primary_btn()?.prop("disabled", true);
		const response = await globalThis.frappe.call({
			method: BRANCH_SWITCH_METHOD,
			type: "POST",
			freeze: true,
			freeze_message: __("Switching Institution and Branch..."),
			args: {
				branch: values.branch,
				company: branchRow.company || institutionRow.company || undefined,
				institution,
			},
		});
		const switched = responseMessage(response);
		if (switched.institution_context && globalThis.frappe?.eduedge?.applyInstitutionContext) {
			globalThis.frappe.eduedge.applyInstitutionContext(switched.institution_context);
		}
		dialog.hide();
		globalThis.frappe.show_alert?.({
			message: __("Institution and Branch context switched"),
			indicator: "green",
		});
		window.setTimeout(() => window.location.reload(), 120);
	} catch (error) {
		dialog.get_primary_btn()?.prop("disabled", false);
		globalThis.frappe.msgprint({
			title: __("Unable to switch context"),
			message: error?.message || __("The selected Institution and Branch context could not be activated."),
			indicator: "red",
		});
	}
}

async function openContextSwitcher() {
	if (contextDialogOpening || globalThis.frappe?.session?.user === "Guest") return;
	contextDialogOpening = true;
	try {
		const response = await globalThis.frappe.call(ACTIVE_CONTEXT_METHOD);
		const payload = responseMessage(response);
		const institutions = institutionOptions(payload);
		if (!institutions.length) {
			globalThis.frappe.msgprint({
				title: __("No Institution available"),
				message: __("Your user does not have an enabled EduEdge Institution and Branch context."),
				indicator: "orange",
			});
			return;
		}

		const initialInstitution = currentInstitution(payload);
		const initialBranches = branchOptions(payload, initialInstitution);
		const dialog = new globalThis.frappe.ui.Dialog({
			title: __("Switch Institution and Branch"),
			fields: [
				{
					fieldtype: "HTML",
					fieldname: "current_context",
					options: `
						<div class="eduedge-context-switch-summary">
							<div><span>Current Institution</span><strong>${globalThis.frappe.utils.escape_html(payload.institution_context?.institution_name || "Not selected")}</strong></div>
							<div><span>Current Branch</span><strong>${globalThis.frappe.utils.escape_html(payload.institution_context?.branch_name || payload.active_label || "Not selected")}</strong></div>
						</div>
					`,
				},
				{
					fieldtype: "Select",
					fieldname: "institution",
					label: __("Institution"),
					reqd: 1,
					options: institutions,
					default: initialInstitution,
					onchange() {
						const institution = dialog.get_value("institution");
						const options = branchOptions(payload, institution);
						refreshSelectField(dialog.get_field("branch"), options);
						dialog.set_value("branch", options[0]?.value || "");
					},
				},
				{
					fieldtype: "Select",
					fieldname: "branch",
					label: __("Branch / Campus"),
					reqd: 1,
					options: initialBranches,
					default: currentBranchValue(payload, initialInstitution),
					description: __("Only Branches permitted for your user are shown."),
				},
			],
			primary_action_label: __("Switch Context"),
			primary_action: () => switchContext(dialog, payload),
		});
		dialog.show();
	} catch (error) {
		globalThis.frappe.msgprint({
			title: __("Unable to load context switcher"),
			message: error?.message || __("Your available Institution and Branch contexts could not be loaded."),
			indicator: "red",
		});
	} finally {
		contextDialogOpening = false;
	}
}

function findNativeBranchControl(topbar, identity) {
	const context = identity.institution_context || globalThis.frappe?.boot?.eduedge_institution_context || {};
	const branchName = normalizedText(context.branch_name || identity.branch_name);
	if (!branchName) return null;
	const host = topbar.querySelector(".edge-topbar-context, .edge-topbar__context") || topbar;
	const candidates = [...host.querySelectorAll("button, [role='button'], a, div, span, strong")]
		.filter((element) => !element.closest(".eduedge-active-context"))
		.filter((element) => normalizedText(element.textContent) === branchName)
		.sort((left, right) => left.querySelectorAll("*").length - right.querySelectorAll("*").length);
	let control = candidates[0] || [...host.children].find((element) => {
		return !element.classList.contains("eduedge-active-context") && normalizedText(element.textContent).includes(branchName);
	});
	if (!control) return null;
	while (
		control.parentElement &&
		control.parentElement !== host &&
		!control.parentElement.closest(".eduedge-active-context") &&
		normalizedText(control.parentElement.textContent) === branchName
	) {
		control = control.parentElement;
	}
	return control;
}

function bindBranchSwitcher(topbar, identity) {
	const control = findNativeBranchControl(topbar, identity);
	if (!control) return;
	control.classList.add("eduedge-context-switcher");
	control.setAttribute("role", "button");
	control.setAttribute("tabindex", "0");
	control.setAttribute("title", __("Switch Institution or Branch"));
	control.setAttribute("aria-label", __("Switch Institution or Branch"));
	if (!control.querySelector(".eduedge-context-switcher__caret")) {
		const caret = document.createElement("span");
		caret.className = "eduedge-context-switcher__caret";
		caret.setAttribute("aria-hidden", "true");
		control.appendChild(caret);
	}
	if (control.dataset.eduedgeContextSwitcherBound === "1") return;
	control.dataset.eduedgeContextSwitcherBound = "1";
	control.addEventListener("click", (event) => {
		event.preventDefault();
		event.stopPropagation();
		openContextSwitcher();
	});
	control.addEventListener("keydown", (event) => {
		if (!["Enter", " "].includes(event.key)) return;
		event.preventDefault();
		event.stopPropagation();
		openContextSwitcher();
	});
}

function enhanceTopbar(topbar, identity) {
	const context = identity.institution_context || globalThis.frappe?.boot?.eduedge_institution_context || {};
	const tenantName = normalizedText(context.institution_name || identity.tenant_name) || "EduEdge Institution";
	const subtitle = normalizedText(context.institution_type_name || identity.tenant_subtitle) || "Education workspace";

	const brand = topbar.querySelector(".edge-topbar__brand");
	if (brand) {
		setMark(
			brand.querySelector(".edge-topbar__mark"),
			identity.tenant_logo || "",
			SCHOOL_FALLBACK_ICON,
			tenantName
		);
		const copy = brand.querySelector(".edge-topbar__title-copy");
		setText(copy?.querySelector("strong"), tenantName);
		setText(copy?.querySelector("small"), subtitle);
	}
	ensureActiveContext(topbar, identity);
	bindBranchSwitcher(topbar, identity);
}

function enhanceSidebar(shell, identity) {
	const brand = shell.querySelector(".edge-sidebar__brand");
	if (!brand) return;
	const productName = normalizedText(identity.product_name) || "EduEdge";
	setMark(
		brand.querySelector(".edge-sidebar__mark"),
		identity.product_logo || "/assets/eduedge/images/eduedge-mark.svg",
		PRODUCT_FALLBACK_ICON,
		productName
	);
	const copy = brand.querySelector(".edge-sidebar__brand-copy");
	setText(copy?.querySelector("strong"), productName);
	setText(copy?.querySelector("small"), "Education Management");
}

function applyIdentity() {
	scheduled = false;
	if (!isEduEdgeSurface()) return;
	markManagedTerminologySurfaces();
	ensureContextStyles();
	const identity = getIdentity();
	const shells = [...document.querySelectorAll(".edge-app-shell")];
	for (const shell of shells) enhanceSidebar(shell, identity);

	const topbars = [...new Set(document.querySelectorAll(".edge-topbar, .edge-app-shell__topbar"))];
	for (const topbar of topbars) enhanceTopbar(topbar, identity);
	ensureFallbackContext(identity, Boolean(topbars.length));
}

function scheduleIdentity() {
	if (scheduled) return;
	scheduled = true;
	requestAnimationFrame(applyIdentity);
}

function processShellMutations(mutations) {
	for (const mutation of mutations || []) {
		for (const node of mutation.addedNodes || []) {
			if (node.nodeType === Node.ELEMENT_NODE) markManagedTerminologySurfaces(node);
		}
	}
	scheduleIdentity();
}

function startIdentityEnhancer() {
	if (observer || !document.body) return;
	markManagedTerminologySurfaces();
	observer = new MutationObserver(processShellMutations);
	observer.observe(document.body, { childList: true, subtree: true });
	document.addEventListener("page-change", scheduleIdentity);
	globalThis.frappe?.router?.on?.("change", scheduleIdentity);
	window.addEventListener("eduedge:institution-context-changed", scheduleIdentity);
	globalThis.frappe?.eduedge?.syncInstitutionContext?.({ force: true });
	scheduleIdentity();
}

if (document.readyState === "loading") {
	document.addEventListener("DOMContentLoaded", startIdentityEnhancer, { once: true });
} else {
	startIdentityEnhancer();
}

export { applyIdentity, markManagedTerminologySurfaces, openContextSwitcher, startIdentityEnhancer };
