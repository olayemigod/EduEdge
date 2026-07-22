function getEduEdgeInstitutionContext() {
	return frappe.boot?.eduedge_institution_context || frappe.boot?.eduedge_ui_identity?.institution_context || {};
}

function getEduEdgeTerm(canonicalKey, options = {}) {
	const context = options.context || getEduEdgeInstitutionContext();
	const term = context?.terms?.[canonicalKey] || {};
	const label = options.plural ? term.plural : term.singular;
	return label || options.fallback || String(canonicalKey || "").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function applyEduEdgeInstitutionContext(context = {}) {
	frappe.boot = frappe.boot || {};
	frappe.boot.eduedge_institution_context = context;
	if (frappe.boot.eduedge_ui_identity) {
		frappe.boot.eduedge_ui_identity.institution_context = context;
		frappe.boot.eduedge_ui_identity.tenant_name = context.institution_name || context.company || frappe.boot.eduedge_ui_identity.tenant_name || "";
		frappe.boot.eduedge_ui_identity.tenant_subtitle = context.institution_type_name || "Education workspace";
	}
	window.dispatchEvent(new CustomEvent("eduedge:institution-context-changed", { detail: context }));
	return context;
}

window.EduEdgeTerminology = {
	context: getEduEdgeInstitutionContext,
	term: getEduEdgeTerm,
	applyContext: applyEduEdgeInstitutionContext,
};

frappe.eduedge = frappe.eduedge || {};
frappe.eduedge.institutionContext = getEduEdgeInstitutionContext;
frappe.eduedge.term = getEduEdgeTerm;
frappe.eduedge.applyInstitutionContext = applyEduEdgeInstitutionContext;
