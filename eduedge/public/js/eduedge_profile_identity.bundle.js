import EduEdgeInstitutionProfile from "./eduedge_institution_profile/EduEdgeInstitutionProfile.vue";
import EduEdgeMyProfile from "./eduedge_my_profile/EduEdgeMyProfile.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const MY_PROFILE_ROUTE = "/app/eduedge-my-profile";
const PROFILE_LINK_ATTRIBUTE = "data-eduedge-my-profile-link";

export function createEduEdgeMyProfileApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeMyProfile, rootProps);
}

export function createEduEdgeInstitutionProfileApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeInstitutionProfile, rootProps);
}

function applyProfileIdentity(context = {}) {
	const frappeBoot = globalThis.frappe?.boot;
	if (!frappeBoot) return;
	const identity = frappeBoot.eduedge_ui_identity || {};
	identity.institution_context = context;
	identity.tenant_name = context.institution_name || context.company || "";
	identity.tenant_subtitle = context.institution_type_name || "Education workspace";
	identity.tenant_logo = context.logo || "";
	identity.branch_name = context.branch_name || "";
	identity.owner_company_name = context.company || "";
	identity.contact_identity = {
		phone: context.phone || "",
		whatsapp_number: context.whatsapp_number || "",
		email: context.email || "",
		website: context.website || "",
		formatted_address: context.formatted_address || "",
	};
	frappeBoot.eduedge_ui_identity = identity;
	const shared = frappeBoot.edgesuite_ui_identity || {};
	shared.eduedge = { ...(shared.eduedge || {}), ...identity };
	frappeBoot.edgesuite_ui_identity = shared;
}

function normalizedMenuText(element) {
	return String(element?.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
}

function isUserMenu(menu) {
	if (!menu) return false;
	if (
		menu.closest(
			".dropdown-navbar-user, .navbar-user, .user-menu, .edge-topbar__user, .edge-topbar__profile, [data-user-menu]"
		)
	) {
		return true;
	}
	const text = normalizedMenuText(menu);
	return ["log out", "logout", "my settings", "user settings", "session defaults", "my profile"].some((label) =>
		text.includes(label)
	);
}

function removeInjectedProfileLinks(menu, keep = null) {
	for (const injectedLink of menu.querySelectorAll(`[${PROFILE_LINK_ATTRIBUTE}]`)) {
		if (injectedLink === keep) continue;
		const removableItem = injectedLink.parentElement?.matches("li") ? injectedLink.parentElement : injectedLink;
		removableItem.remove();
	}
}

function configureExistingProfileLink(menu) {
	if (!isUserMenu(menu)) return;
	const menuItems = [...menu.querySelectorAll("a, button")];
	const profileLink = menuItems.find((item) => normalizedMenuText(item) === "my profile");

	if (!profileLink) {
		removeInjectedProfileLinks(menu);
		return;
	}

	removeInjectedProfileLinks(menu, profileLink);
	profileLink.setAttribute(PROFILE_LINK_ATTRIBUTE, "1");
	profileLink.setAttribute("href", MY_PROFILE_ROUTE);
	profileLink.setAttribute("role", profileLink.getAttribute("role") || "menuitem");
}

function ensureProfileAvatarLink(root = document) {
	for (const menu of root.querySelectorAll?.(".dropdown-menu, [role='menu']") || []) {
		configureExistingProfileLink(menu);
	}
}

function startProfileAvatarIntegration() {
	if (!document.body || document.body.dataset.eduedgeProfileAvatarReady === "1") return;
	document.body.dataset.eduedgeProfileAvatarReady = "1";

	document.addEventListener("click", (event) => {
		const profileLink = event.target.closest?.(`[${PROFILE_LINK_ATTRIBUTE}]`);
		if (profileLink) {
			event.preventDefault();
			window.location.href = MY_PROFILE_ROUTE;
			return;
		}
		if (
			event.target.closest?.(
				".avatar, .dropdown-navbar-user, .navbar-user, .user-menu, .edge-topbar__user, .edge-topbar__profile, [data-user-menu]"
			)
		) {
			window.setTimeout(() => ensureProfileAvatarLink(), 0);
		}
	});

	const observer = new MutationObserver((mutations) => {
		for (const mutation of mutations) {
			for (const node of mutation.addedNodes) {
				if (!(node instanceof Element)) continue;
				if (node.matches?.(".dropdown-menu, [role='menu']")) configureExistingProfileLink(node);
				ensureProfileAvatarLink(node);
			}
		}
	});
	observer.observe(document.body, { childList: true, subtree: true });
	ensureProfileAvatarLink();
}

window.addEventListener("eduedge:institution-context-changed", (event) => {
	applyProfileIdentity(event.detail || {});
});

applyProfileIdentity(
	globalThis.frappe?.boot?.eduedge_institution_context ||
	globalThis.frappe?.boot?.eduedge_ui_identity?.institution_context ||
	{}
);

if (typeof window !== "undefined") {
	window.EduEdgeMyProfile = EduEdgeMyProfile;
	window.EduEdgeInstitutionProfile = EduEdgeInstitutionProfile;
	window.createEduEdgeMyProfileApp = createEduEdgeMyProfileApp;
	window.createEduEdgeInstitutionProfileApp = createEduEdgeInstitutionProfileApp;
	window.EduEdgeProfileIdentity = {
		apply: applyProfileIdentity,
		installAvatarLink: ensureProfileAvatarLink,
	};
}

if (document.readyState === "loading") {
	document.addEventListener("DOMContentLoaded", startProfileAvatarIntegration, { once: true });
} else {
	startProfileAvatarIntegration();
}
