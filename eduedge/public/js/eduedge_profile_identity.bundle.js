import EduEdgeInstitutionProfile from "./eduedge_institution_profile/EduEdgeInstitutionProfile.vue";
import EduEdgeMyProfile from "./eduedge_my_profile/EduEdgeMyProfile.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const MY_PROFILE_ROUTE = "/app/eduedge-my-profile";
const PROFILE_LINK_ATTRIBUTE = "data-eduedge-my-profile-link";
const PROFILE_PHOTO_UPLOAD_METHOD = "eduedge.api.profile_uploads.upload_my_profile_photo";

export function createEduEdgeMyProfileApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeMyProfile, rootProps);
}

export function createEduEdgeInstitutionProfileApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeInstitutionProfile, rootProps);
}

function installProfilePhotoUploader() {
	if (!EduEdgeMyProfile?.methods) return;
	EduEdgeMyProfile.methods.uploadPhoto = function uploadPhoto() {
		if (!this.canEdit || !frappe.ui?.FileUploader) return;
		this.saveError = "";
		new frappe.ui.FileUploader({
			method: PROFILE_PHOTO_UPLOAD_METHOD,
			allow_multiple: false,
			make_attachments_public: false,
			allow_toggle_private: false,
			disable_file_browser: true,
			allow_web_link: false,
			allow_google_drive: false,
			restrictions: {
				allowed_file_types: [".jpg", ".jpeg", ".png", ".webp", "image/jpeg", "image/png", "image/webp"],
				max_file_size: 2 * 1024 * 1024,
			},
			upload_notes: __("JPG, PNG, or WebP only. Maximum size: 2 MB."),
			on_success: async (fileDoc) => {
				this.savingPhoto = true;
				try {
					if (!fileDoc?.file_url) {
						throw new Error(__("The uploaded profile photo response was incomplete."));
					}
					const response = await frappe.call("eduedge.api.profiles.get_my_profile");
					this.data = response.message || this.data;
					frappe.show_alert({ message: __("Profile photo updated"), indicator: "green" });
				} catch (error) {
					this.saveError = error?.message || __("Profile photo could not be updated.");
				} finally {
					this.savingPhoto = false;
				}
			},
		});
	};
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
	profileLink.removeAttribute("data-route");
	profileLink.removeAttribute("data-doctype");
	profileLink.removeAttribute("data-name");
}

function isAvatarProfileMenuItem(element) {
	if (!element) return false;
	if (element.hasAttribute(PROFILE_LINK_ATTRIBUTE)) return true;
	const menu = element.closest(".dropdown-menu, [role='menu']");
	return Boolean(menu && isUserMenu(menu) && normalizedMenuText(element) === "my profile");
}

function ensureProfileAvatarLink(root = document) {
	for (const menu of root.querySelectorAll?.(".dropdown-menu, [role='menu']") || []) {
		configureExistingProfileLink(menu);
	}
}

function startProfileAvatarIntegration() {
	if (!document.body || document.body.dataset.eduedgeProfileAvatarReady === "1") return;
	document.body.dataset.eduedgeProfileAvatarReady = "1";

	// Capture the click before Frappe's existing User-profile handler can route to /desk/user/{email}.
	document.addEventListener(
		"click",
		(event) => {
			const menuItem = event.target.closest?.("a, button");
			if (isAvatarProfileMenuItem(menuItem)) {
				event.preventDefault();
				event.stopPropagation();
				event.stopImmediatePropagation();
				window.location.assign(MY_PROFILE_ROUTE);
				return;
			}
			if (
				event.target.closest?.(
					".avatar, .dropdown-navbar-user, .navbar-user, .user-menu, .edge-topbar__user, .edge-topbar__profile, [data-user-menu]"
				)
			) {
				window.setTimeout(() => ensureProfileAvatarLink(), 0);
			}
		},
		true
	);

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

installProfilePhotoUploader();

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
