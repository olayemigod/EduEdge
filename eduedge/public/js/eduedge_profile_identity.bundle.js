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
	if (!menu || menu.querySelector(`[${PROFILE_LINK_ATTRIBUTE}]`)) return false;
	if (
		menu.closest(
			".dropdown-navbar-user, .navbar-user, .user-menu, .edge-topbar__user, .edge-topbar__profile, [data-user-menu]"
		)
	) {
		return true;
	}
	const text = normalizedMenuText(menu);
	return ["log out", "logout", "my settings", "session defaults", "user profile"].some((label) =>
		text.includes(label)
	);
}

function createProfileMenuLink() {
	const link = document.createElement("a");
	link.className = "dropdown-item";
	link.href = MY_PROFILE_ROUTE;
	link.setAttribute(PROFILE_LINK_ATTRIBUTE, "1");
	link.setAttribute("role", "menuitem");
	link.textContent = globalThis.__ ? __("My Profile") : "My Profile";
	return link;
}

function installProfileLink(menu) {
	if (!isUserMenu(menu)) return;
	const link = createProfileMenuLink();
	const menuItems = [...menu.querySelectorAll("a, button")];
	const logoutItem = menuItems.find((item) => {
		const text = normalizedMenuText(item);
		return text === "log out" || text === "logout" || text.includes("log out");
	});
	const insertionTarget = logoutItem?.parentElement === menu ? logoutItem : logoutItem?.closest("li");
	if (insertionTarget?.parentElement === menu) {
		menu.insertBefore(link, insertionTarget);
	} else {
		menu.appendChild(link);
	}
}

function ensureProfileAvatarLink(root = document) {
	for (const menu of root.querySelectorAll?.(".dropdown-menu, [role='menu']") || []) {
		installProfileLink(menu);
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
				if (node.matches?.(".dropdown-menu, [role='menu']")) installProfileLink(node);
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
