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

window.addEventListener("eduedge:institution-context-changed", (event) => {
	applyProfileIdentity(event.detail || {});
});

applyProfileIdentity(
	globalThis.frappe?.boot?.eduedge_institution_context ||
	globalThis.frappe?.boot?.eduedge_ui_identity?.institution_context ||
	{}
);

window.EduEdgeProfileIdentity = { apply: applyProfileIdentity };
