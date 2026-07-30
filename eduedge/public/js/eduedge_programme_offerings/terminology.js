const CANONICAL_TEXT = Symbol("eduedgeProgrammeOfferingCanonicalText");

function term(vm, key, plural, fallback) {
	return vm.term?.(key, plural, fallback) || fallback;
}

function translatedText(value, vm) {
	const session = term(vm, "academic_year", false, "Academic Year");
	const sessions = term(vm, "academic_year", true, "Academic Years");
	const period = term(vm, "academic_term", false, "Academic Period");
	const periods = term(vm, "academic_term", true, "Academic Periods");
	let next = String(value || "");
	for (const [from, to] of [
		["All years", `All ${sessions.toLowerCase()}`],
		["Select year", `Select ${session.toLowerCase()}`],
		["Year-wide", `${session}-wide`],
		["Academic Years", sessions],
		["Academic Year", session],
		["All periods", `All ${periods.toLowerCase()}`],
		["Academic Periods", periods],
		["Academic Period", period],
	]) {
		next = next.split(from).join(to);
	}
	return next;
}

function applyVisibleTerms(vm) {
	if (!vm?.$el) return;
	const walker = document.createTreeWalker(vm.$el, NodeFilter.SHOW_TEXT, {
		acceptNode(node) {
			const parent = node.parentElement;
			if (!parent || !node.nodeValue?.trim()) return NodeFilter.FILTER_REJECT;
			if (parent.closest("script, style, textarea, input, code, pre, [contenteditable='true']")) {
				return NodeFilter.FILTER_REJECT;
			}
			return NodeFilter.FILTER_ACCEPT;
		},
	});
	const nodes = [];
	while (walker.nextNode()) nodes.push(walker.currentNode);
	for (const node of nodes) {
		if (node[CANONICAL_TEXT] === undefined) node[CANONICAL_TEXT] = node.nodeValue;
		const translated = translatedText(node[CANONICAL_TEXT], vm);
		if (translated !== node.nodeValue) node.nodeValue = translated;
	}
}

function wrapLifecycle(component, hookName) {
	const original = component[hookName];
	component[hookName] = function wrappedTerminologyLifecycle(...args) {
		const result = typeof original === "function" ? original.apply(this, args) : undefined;
		this.$nextTick?.(() => applyVisibleTerms(this));
		return result;
	};
}

export function applyProgrammeOfferingTerminology(component) {
	if (!component || component.__eduedgeOfferingTerminologyReady) return component;
	component.__eduedgeOfferingTerminologyReady = true;
	wrapLifecycle(component, "mounted");
	wrapLifecycle(component, "updated");
	return component;
}
