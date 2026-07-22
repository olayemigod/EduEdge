const BRANCH_SWITCH_METHOD = "eduedge.api.branch_context.switch_school_branch";
const ACTIVE_CONTEXT_METHOD = "eduedge.api.branch_context.get_active_branch_context";

let contextSyncPromise = null;
let terminologyObserver = null;
let terminologyScheduled = false;

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
	const identity = frappe.boot.eduedge_ui_identity || {};
	identity.institution_context = context;
	identity.tenant_name = context.institution_name || context.company || identity.tenant_name || "";
	identity.tenant_subtitle = context.institution_type_name || "Education workspace";
	identity.branch_name = context.branch_name || "";
	identity.owner_company_name = context.company || identity.owner_company_name || "";
	frappe.boot.eduedge_ui_identity = identity;

	const shared = frappe.boot.edgesuite_ui_identity || {};
	shared.eduedge = { ...(shared.eduedge || {}), ...identity };
	frappe.boot.edgesuite_ui_identity = shared;

	window.dispatchEvent(new CustomEvent("eduedge:institution-context-changed", { detail: context }));
	scheduleVisibleTerminology();
	return context;
}

function responseMessage(response) {
	return response?.message || response || {};
}

async function syncEduEdgeInstitutionContext({ force = false } = {}) {
	if (frappe.session?.user === "Guest" || typeof frappe.call !== "function") {
		return getEduEdgeInstitutionContext();
	}
	if (contextSyncPromise && !force) return contextSyncPromise;

	contextSyncPromise = Promise.resolve(frappe.call(ACTIVE_CONTEXT_METHOD))
		.then((response) => {
			const payload = responseMessage(response);
			const context = payload.institution_context || payload.context;
			return context ? applyEduEdgeInstitutionContext(context) : getEduEdgeInstitutionContext();
		})
		.catch(() => getEduEdgeInstitutionContext())
		.finally(() => {
			contextSyncPromise = null;
		});
	return contextSyncPromise;
}

function installBranchSwitchContextBridge() {
	if (typeof frappe.call !== "function" || frappe.call.__eduedgeContextBridge) return;
	const originalCall = frappe.call;
	const wrappedCall = function (...args) {
		const method = typeof args[0] === "string" ? args[0] : args[0]?.method;
		const result = originalCall.apply(this, args);
		if (method === BRANCH_SWITCH_METHOD) {
			Promise.resolve(result)
				.then((response) => {
					const payload = responseMessage(response);
					if (payload.institution_context) {
						applyEduEdgeInstitutionContext(payload.institution_context);
					} else {
						syncEduEdgeInstitutionContext({ force: true });
					}
				})
				.catch(() => {});
		}
		return result;
	};
	wrappedCall.__eduedgeContextBridge = true;
	wrappedCall.__eduedgeOriginalCall = originalCall;
	frappe.call = wrappedCall;
}

function isEduEdgeTerminologySurface() {
	const path = window.location.pathname.replace(/\/+$/, "");
	return /\/(?:app|desk)\/eduedge-/.test(path) || /\/app\/assessment-(?:plan|result|group)(?:\/|$)/.test(path);
}

function visibleTerminologyPairs() {
	const assessment = getEduEdgeTerm("assessment", { fallback: "Assessment" });
	const assessments = getEduEdgeTerm("assessment", { plural: true, fallback: "Assessments" });
	const assessmentGroup = getEduEdgeTerm("assessment_group", { fallback: "Assessment Group" });
	const assessmentGroups = getEduEdgeTerm("assessment_group", { plural: true, fallback: "Assessment Groups" });
	const assessmentPlan = getEduEdgeTerm("assessment_plan", { fallback: "Assessment Plan" });
	const assessmentPlans = getEduEdgeTerm("assessment_plan", { plural: true, fallback: "Assessment Plans" });
	const assessmentResult = getEduEdgeTerm("assessment_result", { fallback: "Assessment Result" });
	const assessmentResults = getEduEdgeTerm("assessment_result", { plural: true, fallback: "Assessment Results" });

	return [
		["Assessments & Results", `${assessments} & Results`],
		["Assessment and Results", `${assessments} and Results`],
		["Assessment Operations", `${assessment} Operations`],
		["Assessment operations", `${assessment} operations`],
		["assessment operations", `${assessment.toLowerCase()} operations`],
		["Assessment Results", assessmentResults],
		["Assessment Result", assessmentResult],
		["assessment results", assessmentResults.toLowerCase()],
		["assessment result", assessmentResult.toLowerCase()],
		["Assessment Plans", assessmentPlans],
		["Assessment Plan", assessmentPlan],
		["assessment plans", assessmentPlans.toLowerCase()],
		["assessment plan", assessmentPlan.toLowerCase()],
		["Assessment Groups", assessmentGroups],
		["Assessment Group", assessmentGroup],
		["assessment groups", assessmentGroups.toLowerCase()],
		["assessment group", assessmentGroup.toLowerCase()],
		["Assessments", assessments],
		["Assessment", assessment],
		["assessments", assessments.toLowerCase()],
		["assessment", assessment.toLowerCase()],
	].filter(([from, to]) => from && to && from !== to);
}

function replaceVisibleValue(value, pairs) {
	let next = String(value || "");
	for (const [from, to] of pairs) next = next.split(from).join(to);
	return next;
}

function applyVisibleTerminology(root = document.body) {
	if (!root || !isEduEdgeTerminologySurface()) return;
	const pairs = visibleTerminologyPairs();
	if (!pairs.length) return;

	const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
		acceptNode(node) {
			const parent = node.parentElement;
			if (!parent || !node.nodeValue?.trim()) return NodeFilter.FILTER_REJECT;
			if (parent.closest("script, style, textarea, code, pre, [contenteditable='true']")) return NodeFilter.FILTER_REJECT;
			return NodeFilter.FILTER_ACCEPT;
		},
	});
	const nodes = [];
	while (walker.nextNode()) nodes.push(walker.currentNode);
	for (const node of nodes) {
		const next = replaceVisibleValue(node.nodeValue, pairs);
		if (next !== node.nodeValue) node.nodeValue = next;
	}

	for (const element of root.querySelectorAll?.("[placeholder], [title], [aria-label]") || []) {
		for (const attribute of ["placeholder", "title", "aria-label"]) {
			if (!element.hasAttribute(attribute)) continue;
			const current = element.getAttribute(attribute) || "";
			const next = replaceVisibleValue(current, pairs);
			if (next !== current) element.setAttribute(attribute, next);
		}
	}
}

function scheduleVisibleTerminology() {
	if (terminologyScheduled) return;
	terminologyScheduled = true;
	requestAnimationFrame(() => {
		terminologyScheduled = false;
		applyVisibleTerminology();
	});
}

function startTerminologyObserver() {
	if (terminologyObserver || !document.body) return;
	terminologyObserver = new MutationObserver(scheduleVisibleTerminology);
	terminologyObserver.observe(document.body, { childList: true, subtree: true });
	document.addEventListener("page-change", scheduleVisibleTerminology);
	frappe.router?.on?.("change", () => {
		syncEduEdgeInstitutionContext({ force: true });
		scheduleVisibleTerminology();
	});
	window.addEventListener("eduedge:institution-context-changed", scheduleVisibleTerminology);
	scheduleVisibleTerminology();
}

function initialiseEduEdgeContext() {
	installBranchSwitchContextBridge();
	startTerminologyObserver();
	frappe.require?.(["eduedge_shell_identity.bundle.js"]);
	syncEduEdgeInstitutionContext({ force: true });
}

window.EduEdgeTerminology = {
	context: getEduEdgeInstitutionContext,
	term: getEduEdgeTerm,
	applyContext: applyEduEdgeInstitutionContext,
	syncContext: syncEduEdgeInstitutionContext,
	applyVisible: applyVisibleTerminology,
};

frappe.eduedge = frappe.eduedge || {};
frappe.eduedge.institutionContext = getEduEdgeInstitutionContext;
frappe.eduedge.term = getEduEdgeTerm;
frappe.eduedge.applyInstitutionContext = applyEduEdgeInstitutionContext;
frappe.eduedge.syncInstitutionContext = syncEduEdgeInstitutionContext;
frappe.eduedge.applyVisibleTerminology = applyVisibleTerminology;

if (document.readyState === "loading") {
	document.addEventListener("DOMContentLoaded", initialiseEduEdgeContext, { once: true });
} else {
	initialiseEduEdgeContext();
}
