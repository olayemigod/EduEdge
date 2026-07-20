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

function companyEntries(identity) {
	return Object.entries(identity.companies || {}).map(([key, value]) => ({
		key,
		label: normalizedText(value?.label || value?.name || key),
		logo: value?.logo || "",
	}));
}

function resolveCompany(identity, chipTexts) {
	const entries = companyEntries(identity);
	for (const chipText of chipTexts) {
		const normalized = normalizedText(chipText);
		const match = entries.find(
			(entry) => normalizedText(entry.key) === normalized || entry.label === normalized
		);
		if (match) return match;
	}

	const activeName = normalizedText(identity.tenant_name);
	if (activeName) {
		return (
			entries.find(
				(entry) => normalizedText(entry.key) === activeName || entry.label === activeName
			) || {
				key: activeName,
				label: activeName,
				logo: identity.tenant_logo || "",
			}
		);
	}
	return null;
}

function enhanceTopbar(shell, identity) {
	const topbar = shell.querySelector(".edge-app-shell__topbar.edge-topbar");
	if (!topbar) return;

	const chips = Array.from(topbar.querySelectorAll(".edge-topbar-context .edge-context-chip"));
	const chipTexts = chips.map((chip) => normalizedText(chip.textContent));
	const company = resolveCompany(identity, chipTexts);
	const companyName = company?.label || company?.key || "School";

	const brand = topbar.querySelector(".edge-topbar__brand");
	if (brand) {
		setMark(
			brand.querySelector(".edge-topbar__mark"),
			company?.logo || identity.tenant_logo || "",
			SCHOOL_FALLBACK_ICON,
			companyName
		);
		const copy = brand.querySelector(".edge-topbar__title-copy");
		setText(copy?.querySelector("strong"), companyName);
		setText(copy?.querySelector("small"), "School workspace");
	}

	for (const chip of chips) {
		const text = normalizedText(chip.textContent);
		const isTenant = Boolean(
			company && (text === normalizedText(company.key) || text === normalizedText(company.label))
		);
		if (isTenant) chip.dataset.eduedgeTenantChip = "1";
		else delete chip.dataset.eduedgeTenantChip;
	}
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
	const identity = getIdentity();
	for (const shell of document.querySelectorAll('.edge-app-shell[data-edge-product="eduedge"]')) {
		enhanceTopbar(shell, identity);
		enhanceSidebar(shell, identity);
	}
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
	scheduleIdentity();
}

if (document.readyState === "loading") {
	document.addEventListener("DOMContentLoaded", startIdentityEnhancer, { once: true });
} else {
	startIdentityEnhancer();
}

export { applyIdentity, startIdentityEnhancer };
