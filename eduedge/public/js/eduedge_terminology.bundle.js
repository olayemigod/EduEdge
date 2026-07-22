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
	if (frappe.boot.eduedge_ui_identity) frappe.boot.eduedge_ui_identity.institution_context = context;
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
