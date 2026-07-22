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
	return /\/(?:app|desk)\/eduedge-/.test(path) || /\/app\/(?:assessment-(?:plan|result|group)|student(?:\/|$)|student-)/.test(path);
}

function terminologyFamilyPairs(variants, target) {
	return variants
		.filter((variant) => variant && target && variant !== target)
		.map((variant) => [variant, target]);
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
	const student = getEduEdgeTerm("student", { fallback: "Student" });
	const students = getEduEdgeTerm("student", { plural: true, fallback: "Students" });
	const studentGroup = getEduEdgeTerm("student_group", { fallback: "Student Group" });
	const studentGroups = getEduEdgeTerm("student_group", { plural: true, fallback: "Student Groups" });
	const studentBatch = getEduEdgeTerm("student_batch", { fallback: "Student Batch" });
	const studentBatches = getEduEdgeTerm("student_batch", { plural: true, fallback: "Student Batches" });

	const pairs = [
		...terminologyFamilyPairs(
			["Assessments & Results", "Examinations & Results", "Evaluations & Results"],
			`${assessments} & Results`
		),
		...terminologyFamilyPairs(
			["Assessment and Results", "Examination and Results", "Evaluation and Results"],
			`${assessments} and Results`
		),
		...terminologyFamilyPairs(
			["assessment and results", "examination and results", "evaluation and results"],
			`${assessments.toLowerCase()} and results`
		),
		...terminologyFamilyPairs(
			["Assessment Operations", "Examination Operations", "Evaluation Operations"],
			`${assessment} Operations`
		),
		...terminologyFamilyPairs(
			["Assessment operations", "Examination operations", "Evaluation operations"],
			`${assessment} operations`
		),
		...terminologyFamilyPairs(
			["assessment operations", "examination operations", "evaluation operations"],
			`${assessment.toLowerCase()} operations`
		),
		...terminologyFamilyPairs(
			["Assessment Results", "Examination Results", "Evaluation Results"],
			assessmentResults
		),
		...terminologyFamilyPairs(
			["Assessment Result", "Examination Result", "Evaluation Result"],
			assessmentResult
		),
		...terminologyFamilyPairs(
			["assessment results", "examination results", "evaluation results"],
			assessmentResults.toLowerCase()
		),
		...terminologyFamilyPairs(
			["assessment result", "examination result", "evaluation result"],
			assessmentResult.toLowerCase()
		),
		...terminologyFamilyPairs(
			["Assessment Plans", "Examination Plans", "Evaluation Plans"],
			assessmentPlans
		),
		...terminologyFamilyPairs(
			["Assessment Plan", "Examination Plan", "Evaluation Plan"],
			assessmentPlan
		),
		...terminologyFamilyPairs(
			["assessment plans", "examination plans", "evaluation plans"],
			assessmentPlans.toLowerCase()
		),
		...terminologyFamilyPairs(
			["assessment plan", "examination plan", "evaluation plan"],
			assessmentPlan.toLowerCase()
		),
		...terminologyFamilyPairs(
			["Assessment Groups", "Examination Groups", "Evaluation Groups"],
			assessmentGroups
		),
		...terminologyFamilyPairs(
			["Assessment Group", "Examination Group", "Evaluation Group"],
			assessmentGroup
		),
		...terminologyFamilyPairs(
			["assessment groups", "examination groups", "evaluation groups"],
			assessmentGroups.toLowerCase()
		),
		...terminologyFamilyPairs(
			["assessment group", "examination group", "evaluation group"],
			assessmentGroup.toLowerCase()
		),
		...terminologyFamilyPairs(["Assessments", "Examinations", "Evaluations"], assessments),
		...terminologyFamilyPairs(["Assessment", "Examination", "Evaluation"], assessment),
		...terminologyFamilyPairs(
			["assessments", "examinations", "evaluations"],
			assessments.toLowerCase()
		),
		...terminologyFamilyPairs(
			["assessment", "examination", "evaluation"],
			assessment.toLowerCase()
		),
		...terminologyFamilyPairs(
			["Student Groups", "Pupil Groups", "Trainee Groups", "Lecture Groups", "Class Arms"],
			studentGroups
		),
		...terminologyFamilyPairs(
			["Student Group", "Pupil Group", "Trainee Group", "Lecture Group", "Class Arm"],
			studentGroup
		),
		...terminologyFamilyPairs(
			["student groups", "pupil groups", "trainee groups", "lecture groups", "class arms"],
			studentGroups.toLowerCase()
		),
		...terminologyFamilyPairs(
			["student group", "pupil group", "trainee group", "lecture group", "class arm"],
			studentGroup.toLowerCase()
		),
		...terminologyFamilyPairs(
			["Student Batches", "Pupil Batches", "Trainee Batches", "Admission Sets", "Entry Cohorts"],
			studentBatches
		),
		...terminologyFamilyPairs(
			["Student Batch", "Pupil Batch", "Trainee Batch", "Admission Set", "Entry Cohort"],
			studentBatch
		),
		...terminologyFamilyPairs(
			["student batches", "pupil batches", "trainee batches", "admission sets", "entry cohorts"],
			studentBatches.toLowerCase()
		),
		...terminologyFamilyPairs(
			["student batch", "pupil batch", "trainee batch", "admission set", "entry cohort"],
			studentBatch.toLowerCase()
		),
		...terminologyFamilyPairs(["Students", "Pupils", "Trainees"], students),
		...terminologyFamilyPairs(["Student", "Pupil", "Trainee"], student),
		...terminologyFamilyPairs(["students", "pupils", "trainees"], students.toLowerCase()),
		...terminologyFamilyPairs(["student", "pupil", "trainee"], student.toLowerCase()),
	];

	return pairs.sort((left, right) => right[0].length - left[0].length);
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
