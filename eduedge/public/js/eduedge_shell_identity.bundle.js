const SCHOOL_FALLBACK_ICON = `
<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
	<path d="M4 21h16M5 21V9l7-5 7 5v12M9 21v-6h6v6M8 11h.01M12 11h.01M16 11h.01" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`;

const PRODUCT_FALLBACK_ICON = `
<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
	<path d="m3 8.5 9-4.5 9 4.5-9 4.5-9-4.5Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
	<path d="M7 10.5v4.2c0 1.4 2.2 2.8 5 2.8s5-1.4 5-2.8v-4.2M21 8.5v6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
</svg>`;

let observer;
let scheduled = false;

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
		@media (max-width: 720px) { .eduedge-active-context__item strong { max-width:9rem; } }
	`;
	document.head.appendChild(style);
}

function contextMarkup() {
	return `
		<div class="eduedge-active-context__item" data-eduedge-context="institution"><small>Institution</small><strong></strong></div>
		<div class="eduedge-active-context__item" data-eduedge-context="branch"><small>Branch</small><strong></strong></div>
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
		strip.innerHTML = contextMarkup();
		const host = topbar.querySelector(".edge-topbar-context, .edge-topbar__context, .edge-topbar__actions") || topbar;
		host.appendChild(strip);
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
		fallback.innerHTML = contextMarkup();
		host.prepend(fallback);
	}
	populateContext(fallback, identity);
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

function startIdentityEnhancer() {
	if (observer || !document.body) return;
	observer = new MutationObserver(scheduleIdentity);
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

export { applyIdentity, startIdentityEnhancer };
