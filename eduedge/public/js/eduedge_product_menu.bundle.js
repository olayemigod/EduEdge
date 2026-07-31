const EDUEDGE_PRODUCT_KEY = "eduedge";
const COMMAND_RESULT_LIMIT = 12;
const FAVORITES_STATE_VERSION = "v1";
const DENSITY_STATE_VERSION = "v1";
const DENSITY_MODES = new Set(["comfortable", "compact", "touch"]);
let activeCommandDialog = null;

function term(key, { plural = false, fallback = "" } = {}) {
	return frappe.eduedge?.term?.(key, { plural, fallback }) || fallback;
}

function item(label, description, icon, route, extra = {}) {
	return { label, description, icon, route, ...extra };
}

function normalizeRoute(route) {
	try {
		return new URL(route, window.location.origin).pathname.replace(/\/+$/, "") || "/";
	} catch (_error) {
		return String(route || "").split(/[?#]/, 1)[0].replace(/\/+$/, "");
	}
}

function preferenceKey(kind, version) {
	return `edgeui:eduedge:${kind}:${version}:${frappe.session?.user || "Guest"}`;
}

function readFavorites() {
	try {
		const value = JSON.parse(localStorage.getItem(preferenceKey("favorites", FAVORITES_STATE_VERSION)) || "[]");
		return Array.isArray(value) ? value.map(normalizeRoute).filter(Boolean) : [];
	} catch (_error) {
		return [];
	}
}

function writeFavorites(routes) {
	const normalized = [...new Set((routes || []).map(normalizeRoute).filter(Boolean))].slice(0, 12);
	localStorage.setItem(preferenceKey("favorites", FAVORITES_STATE_VERSION), JSON.stringify(normalized));
	window.dispatchEvent(new CustomEvent("edgesuite:favorites-changed", { detail: { product: EDUEDGE_PRODUCT_KEY, routes: normalized } }));
	return normalized;
}

function toggleFavorite(route) {
	const normalized = normalizeRoute(route);
	const routes = readFavorites();
	const next = routes.includes(normalized) ? routes.filter((value) => value !== normalized) : [...routes, normalized];
	return writeFavorites(next);
}

function getDensity() {
	const stored = localStorage.getItem(preferenceKey("density", DENSITY_STATE_VERSION)) || "compact";
	return DENSITY_MODES.has(stored) ? stored : "compact";
}

function setDensity(mode) {
	const next = DENSITY_MODES.has(mode) ? mode : "compact";
	localStorage.setItem(preferenceKey("density", DENSITY_STATE_VERSION), next);
	document.documentElement.dataset.eduedgeDensity = next;
	window.dispatchEvent(new CustomEvent("edgesuite:density-changed", { detail: { product: EDUEDGE_PRODUCT_KEY, density: next } }));
	return next;
}

function featureEnabled(feature) {
	if (!feature) return true;
	const features =
		frappe.boot?.eduedge_features ||
		frappe.boot?.eduedge_ui_identity?.features ||
		frappe.boot?.eduedge_access_manifest?.features;
	if (!features || !Object.prototype.hasOwnProperty.call(features, feature)) return true;
	return Boolean(features[feature]);
}

function buildEduEdgeProductMenu() {
	const programme = term("programme", { fallback: __("Programme") });
	const programmes = term("programme", { plural: true, fallback: __("Programmes") });
	const offerings = term("programme_offering", { plural: true, fallback: __("Programme Offerings") });
	const student = term("student", { fallback: __("Student") });
	const students = term("student", { plural: true, fallback: __("Students") });
	const applicants = term("student_applicant", { plural: true, fallback: __("Applicants") });
	const groups = term("student_group", { plural: true, fallback: __("Classes") });
	const assessments = term("assessment", { plural: true, fallback: __("Assessments") });

	return {
		product_key: EDUEDGE_PRODUCT_KEY,
		product: "EduEdge",
		label: "EduEdge",
		icon: "graduation",
		home_route: "/app/eduedge-home",
		route_patterns: ["/app/eduedge*", "/app/query-report/EduEdge*"],
		order: 30,
		subtitle: "School operations and intelligence",
		menu_source: "eduedge",
		accordion: true,
		sections: [
			{
				key: "overview",
				label: "Overview",
				description: "School command centre and your profile",
				icon: "home",
				items: [
					item("EduEdge Home", "Branch context, readiness, and daily priorities", "home", "/app/eduedge-home", { keywords: ["dashboard", "school", "home"], quick_action: true }),
					item("My Profile", "Your EduEdge identity and account profile", "user", "/app/eduedge-my-profile", { keywords: ["profile", "account", "identity"] }),
				],
			},
			{
				key: "students-admissions",
				label: "Students & Admissions",
				description: `Admissions, applicants, and ${students.toLowerCase()}`,
				icon: "students",
				items: [
					item("Admissions", "Configure and publish admission windows", "clipboard", "/app/eduedge-admissions", { keywords: ["admission", "session", "programme"], quick_action: true }),
					item(applicants, `Review prospective ${students.toLowerCase()}`, "user", "/app/eduedge-applicants", { keywords: ["applicant", "application", "enrolment"] }),
					item(students, `${student} records, profiles, and branch context`, "students", "/app/eduedge-students", { keywords: ["student", "pupil", "learner", "profile"], quick_action: true }),
				],
			},
			{
				key: "academic-setup",
				label: "Academic Setup",
				description: `${programmes}, offerings, ${groups.toLowerCase()}, schedules, and attendance`,
				icon: "graduation",
				items: [
					item("Academic Foundation", "Academic structure, levels, and calendars", "book", "/app/eduedge-academic-foundation", { keywords: ["academic", "foundation", "calendar", "level"] }),
					item(programmes, `Maintain the ${programme.toLowerCase()} catalogue`, "book", "/app/eduedge-programs", { keywords: ["programme", "class", "catalogue", "course"] }),
					item(offerings, `${programmes} available by campus and session`, "layers", "/app/eduedge-program-offerings", { keywords: ["programme", "class", "offering", "academic year"] }),
					item("Academic Operations", `Run ${groups.toLowerCase()}, schedules, and attendance`, "calendar", "/app/eduedge-academic-operations", { keywords: ["class", "schedule", "attendance"], quick_action: true }),
				],
			},
			{
				key: "assessment-results",
				label: "Assessments & Results",
				description: `Plan, approve, publish, and report ${assessments.toLowerCase()}`,
				icon: "assessment",
				items: [
					item(`${assessments} & Results`, `Plan, review, approve, and publish ${assessments.toLowerCase()}`, "assessment", "/app/eduedge-assessment-operations", { keywords: ["exam", "assessment", "result", "publication"], quick_action: true }),
					item("Report Cards", "Comments, progression, approval, and printing", "report", "/app/eduedge-report-cards", { keywords: ["report card", "progression", "promotion", "pdf"] }),
				],
			},
			{
				key: "cbt-delivery",
				label: "CBT Delivery",
				description: "Schedules, candidates, invigilation, review, scoring, and marking",
				icon: "monitor",
				feature: "cbt",
				items: [
					item("CBT Operations", "Centres, approved questions, templates, and readiness", "assessment", "/app/eduedge-cbt-operations", { keywords: ["cbt", "exam", "readiness"], quick_action: true }),
					item("CBT Schedules", "Schedules, candidates, check-in, release, and interventions", "calendar", "/app/eduedge-cbt-schedules", { keywords: ["cbt", "schedule", "candidate", "check in", "invigilator", "intervention"] }),
					item("CBT Invigilation", "Monitor candidates, sync health, and result readiness", "monitor", "/app/eduedge-cbt-invigilation", { resource: "cbt_attempt", permissions: ["read", "report"], keywords: ["cbt", "invigilation", "candidate", "pending sync", "monitor"] }),
					item("CBT Attempt Review", "Resolve integrity flags before scoring", "shield", "/app/eduedge-cbt-review-workbench", { resource: "cbt_attempt_review", permissions: ["create"], keywords: ["cbt", "attempt", "review", "integrity", "disqualify"] }),
					item("CBT Scoring & Marking", "Score objective responses, mark written answers, and approve results", "edit", "/app/eduedge-cbt-marking", { resource: "cbt_result", permissions: ["write"], keywords: ["cbt", "score", "marking", "result", "approval"] }),
				],
			},
			{
				key: "cbt-content",
				label: "CBT Content",
				description: "Question governance and reusable examination designs",
				icon: "book",
				feature: "cbt",
				items: [
					item("Question Bank", "Search and review governed CBT questions", "book", "/app/eduedge-question-bank", { keywords: ["cbt", "question", "bank", "review"] }),
					item("Question Builder", "Author and revise governed CBT questions", "edit", "/app/eduedge-question-builder", { keywords: ["cbt", "question", "author", "builder"], quick_action: true }),
					item("Question Batch", "Create governed CBT questions in batches", "layers", "/app/eduedge-question-batch", { keywords: ["cbt", "question", "batch", "import"] }),
					item("Question Responsibilities", "Manage scoped authors, reviewers, and approvers", "shield", "/app/eduedge-question-responsibilities", { keywords: ["cbt", "question", "author", "reviewer", "approver"] }),
					item("Exam Templates", "Review reusable approved examination designs", "layers", "/app/eduedge-exam-templates", { keywords: ["cbt", "exam", "template", "reuse"] }),
					item("Exam Template Builder", "Create and govern reusable examination designs", "edit", "/app/eduedge-exam-template-builder", { keywords: ["cbt", "exam", "template", "builder"] }),
				],
			},
			{
				key: "institution-access",
				label: "Institution & Access",
				description: "Institution identity, branches, access, accounting, and setup",
				icon: "building",
				items: [
					item("Institution Profile", "Institution identity, branding, address, and contacts", "building", "/app/eduedge-institution-profile", { keywords: ["institution", "profile", "branding", "identity"] }),
					item("Institution Structure", "Institution types and academic terminology", "layers", "/app/eduedge-institution-structure", { keywords: ["institution", "structure", "terminology"] }),
					item("Institution Operations", "Company defaults and institution workflow preferences", "settings", "/app/eduedge-institution-operations-settings", { keywords: ["institution", "operations", "settings", "defaults"] }),
					item("School Branches", "Campus identity and operational defaults", "building", "/app/eduedge-school-branches", { keywords: ["campus", "branch", "cost centre", "account"], quick_action: true }),
					item("Branch Governance", "Campus access coverage and accounting readiness", "shield", "/app/eduedge-branch-governance", { keywords: ["branch", "campus", "access", "accounting"] }),
					item("User Branch Access", "Maintain staff campus assignments inside Branch Governance", "students", "/app/eduedge-branch-governance", { resource: "user_branch_access", permissions: ["read", "write"], keywords: ["user", "role", "assignment", "hq"] }),
					item("Setup Center", "Review foundation readiness and configuration", "settings", "/app/eduedge-setup-center", { keywords: ["setup", "readiness", "configuration"] }),
					item("EduEdge Settings", "Defaults, controls, and optional features", "settings", "/app/eduedge-settings-center", { keywords: ["settings", "features", "defaults"] }),
				],
			},
			{
				key: "help-training",
				label: "Help & Training",
				description: "Role-based learning, practice, and readiness",
				icon: "book",
				items: [item("EduEdge Training Centre", "Step-by-step guides, flowcharts, videos, and progress", "book", "/app/eduedge-training-centre", { keywords: ["training", "guide", "help", "video", "onboarding"] })],
			},
		],
	};
}

function itemAllowed(menuItem) {
	if (frappe.session.user === "Administrator") return true;
	const manifest = frappe.boot?.eduedge_access_manifest;
	if (!manifest) return true;
	if (menuItem.resource) {
		const resource = manifest.resources?.[menuItem.resource] || {};
		return (menuItem.permissions || ["read"]).some((permission) => Boolean(resource[permission]));
	}
	const route = normalizeRoute(menuItem.route);
	if (!Object.prototype.hasOwnProperty.call(manifest.routes || {}, route)) return true;
	return Boolean(manifest.routes[route]);
}

function permissionFilteredMenu() {
	const source = buildEduEdgeProductMenu();
	const baseSections = source.sections
		.filter((section) => featureEnabled(section.feature))
		.map((section) => ({
			...section,
			items: section.items.filter(itemAllowed).map(({ resource, permissions, ...menuItem }) => menuItem),
		}))
		.filter((section) => section.items.length);
	const favorites = new Set(readFavorites());
	const favoriteItems = [];
	const seenFavorites = new Set();
	for (const section of baseSections) {
		for (const menuItem of section.items) {
			const route = normalizeRoute(menuItem.route);
			if (!favorites.has(route) || seenFavorites.has(route)) continue;
			favoriteItems.push({ ...menuItem, favorite: true });
			seenFavorites.add(route);
		}
	}
	const sections = [...baseSections];
	if (favoriteItems.length) {
		const insertAt = Math.max(0, sections.findIndex((section) => section.key === "overview") + 1);
		sections.splice(insertAt, 0, {
			key: "favorites",
			label: __("Favorites"),
			description: __("Your pinned EduEdge pages"),
			icon: "star",
			items: favoriteItems,
		});
	}
	const quickActions = [];
	const seenActions = new Set();
	for (const section of baseSections) {
		for (const menuItem of section.items) {
			const route = normalizeRoute(menuItem.route);
			if (!menuItem.quick_action || seenActions.has(route)) continue;
			quickActions.push(menuItem);
			seenActions.add(route);
		}
	}
	return { ...source, sections, quick_actions: quickActions };
}

function commandEntries(menu = permissionFilteredMenu()) {
	const favorites = new Set(readFavorites());
	const entries = new Map();
	for (const section of menu.sections.filter((entry) => entry.key !== "favorites")) {
		for (const menuItem of section.items) {
			const route = normalizeRoute(menuItem.route);
			if (!route || entries.has(route)) continue;
			entries.set(route, {
				...menuItem,
				favorite: favorites.has(route),
				section: section.label,
				searchText: [menuItem.label, menuItem.description, section.label, ...(menuItem.keywords || [])].filter(Boolean).join(" ").toLowerCase(),
			});
		}
	}
	return [...entries.values()].sort(
		(left, right) =>
			Number(Boolean(right.favorite)) - Number(Boolean(left.favorite)) ||
			Number(Boolean(right.quick_action)) - Number(Boolean(left.quick_action)) ||
			left.label.localeCompare(right.label)
	);
}

function getProfile() {
	const bootUser = frappe.boot?.user || {};
	const userDefaults = bootUser.defaults || {};
	return {
		name: bootUser.full_name || frappe.session?.user || "EduEdge User",
		email: frappe.session?.user || "",
		company: userDefaults.company || frappe.defaults?.get_default?.("company") || "",
		branch: userDefaults.eduedge_school_branch || frappe.defaults?.get_user_default?.("eduedge_school_branch") || "",
	};
}

function isEduEdgeSurface() {
	const path = normalizeRoute(window.location.pathname);
	return path === "/app/eduedge" || path.startsWith("/app/eduedge-") || path.startsWith("/desk/eduedge-");
}

function openEduEdgeCommandPalette() {
	if (!isEduEdgeSurface() || !frappe.ui?.Dialog) return false;
	if (activeCommandDialog) {
		activeCommandDialog.show();
		activeCommandDialog.__eduedgeCommandInput?.focus();
		return true;
	}

	let entries = commandEntries();
	const dialog = new frappe.ui.Dialog({
		title: __("Search EduEdge"),
		size: "large",
		fields: [{ fieldtype: "HTML", fieldname: "command_palette" }],
	});
	const root = dialog.fields_dict.command_palette.$wrapper.empty()[0];
	const shell = document.createElement("div");
	shell.className = "eduedge-command-palette";
	const controls = document.createElement("div");
	controls.className = "eduedge-command-palette__controls";
	const input = document.createElement("input");
	input.type = "search";
	input.className = "form-control eduedge-command-palette__input";
	input.placeholder = __("Search pages, workbenches, and quick actions");
	input.setAttribute("aria-label", __("Search EduEdge navigation"));
	const density = document.createElement("select");
	density.className = "form-control eduedge-command-palette__density";
	density.setAttribute("aria-label", __("Display density"));
	for (const [value, label] of [["compact", __("Compact")], ["comfortable", __("Comfortable")], ["touch", __("Touch")]]) {
		const option = document.createElement("option");
		option.value = value;
		option.textContent = label;
		density.appendChild(option);
	}
	density.value = getDensity();
	controls.append(input, density);
	const hint = document.createElement("div");
	hint.className = "eduedge-command-palette__hint";
	hint.textContent = __("Use ↑ and ↓ to move, Enter to open, and the star to pin a page.");
	const list = document.createElement("div");
	list.className = "eduedge-command-palette__results";
	list.setAttribute("role", "listbox");
	shell.append(controls, hint, list);
	root.appendChild(shell);

	let results = entries.slice(0, COMMAND_RESULT_LIMIT);
	let selectedIndex = 0;

	function openEntry(entry) {
		if (!entry?.route) return;
		dialog.hide();
		window.location.assign(entry.route);
	}

	function renderResults() {
		list.replaceChildren();
		if (!results.length) {
			const empty = document.createElement("p");
			empty.className = "eduedge-command-palette__empty";
			empty.textContent = __("No permitted EduEdge action matches this search.");
			list.appendChild(empty);
			return;
		}
		results.forEach((entry, index) => {
			const row = document.createElement("div");
			row.className = `eduedge-command-palette__result${index === selectedIndex ? " is-selected" : ""}`;
			const button = document.createElement("button");
			button.type = "button";
			button.className = "eduedge-command-palette__open";
			button.setAttribute("role", "option");
			button.setAttribute("aria-selected", index === selectedIndex ? "true" : "false");
			const text = document.createElement("span");
			const label = document.createElement("strong");
			label.textContent = entry.label;
			const description = document.createElement("small");
			description.textContent = entry.description || "";
			text.append(label, description);
			const section = document.createElement("span");
			section.className = "eduedge-command-palette__section";
			section.textContent = entry.section;
			button.append(text, section);
			const favorite = document.createElement("button");
			favorite.type = "button";
			favorite.className = "eduedge-command-palette__favorite";
			favorite.textContent = entry.favorite ? "★" : "☆";
			favorite.title = entry.favorite ? __("Remove from Favorites") : __("Add to Favorites");
			favorite.setAttribute("aria-label", favorite.title);
			favorite.addEventListener("click", () => {
				toggleFavorite(entry.route);
				entries = commandEntries();
				filterResults();
				registerEduEdgeProductMenu();
			});
			row.addEventListener("mouseenter", () => {
				selectedIndex = index;
				renderResults();
			});
			button.addEventListener("click", () => openEntry(entry));
			row.append(button, favorite);
			list.appendChild(row);
		});
	}

	function filterResults() {
		const query = input.value.trim().toLowerCase();
		results = (query ? entries.filter((entry) => entry.searchText.includes(query)) : entries).slice(0, COMMAND_RESULT_LIMIT);
		selectedIndex = 0;
		renderResults();
	}

	input.addEventListener("input", filterResults);
	input.addEventListener("keydown", (event) => {
		if (event.key === "ArrowDown" && results.length) {
			event.preventDefault();
			selectedIndex = (selectedIndex + 1) % results.length;
			renderResults();
		} else if (event.key === "ArrowUp" && results.length) {
			event.preventDefault();
			selectedIndex = (selectedIndex - 1 + results.length) % results.length;
			renderResults();
		} else if (event.key === "Enter" && results[selectedIndex]) {
			event.preventDefault();
			openEntry(results[selectedIndex]);
		} else if (event.key === "Escape") {
			dialog.hide();
		}
	});
	density.addEventListener("change", () => setDensity(density.value));

	dialog.__eduedgeCommandInput = input;
	dialog.$wrapper.on("hidden.bs.modal", () => {
		activeCommandDialog = null;
	});
	activeCommandDialog = dialog;
	renderResults();
	dialog.show();
	requestAnimationFrame(() => input.focus());
	return true;
}

function registerEduEdgeProductMenu() {
	frappe.require("edgesuite_ui.bundle.js", () => {
		const runtime = window.EdgeSuiteUI || window.EdgeUI;
		if (!runtime?.registerProductMenu) return;
		const menu = permissionFilteredMenu();
		runtime.registerProductMenu({ ...menu, profile: getProfile(), commands: commandEntries(menu).map(({ searchText, ...entry }) => entry) });
		runtime.refreshProductMenu?.();
		scheduleVisibleFriendlyNames();
	});
}

function friendlyPairs() {
	const student = term("student", { fallback: "Student" });
	const students = term("student", { plural: true, fallback: "Students" });
	const applicants = term("student_applicant", { plural: true, fallback: "Applicants" });
	const group = term("student_group", { fallback: "Student Group" });
	const groups = term("student_group", { plural: true, fallback: "Student Groups" });
	const programme = term("programme", { fallback: "Programme" });
	const programmes = term("programme", { plural: true, fallback: "Programmes" });
	const offerings = term("programme_offering", { plural: true, fallback: "Programme Offerings" });
	const assessment = term("assessment", { fallback: "Assessment" });
	const assessments = term("assessment", { plural: true, fallback: "Assessments" });
	return [
		["Add School Branches", "Add School Branch"], ["Add School Branche", "Add School Branch"], ["School Branche", "School Branch"],
		["Student Groups / Classes", groups], ["Student Groups", groups], ["Student Group", group],
		["Student Applicants", applicants], ["Applicants", applicants], ["Students", students], ["Student", student],
		["Program Offerings", offerings], ["Programme Offerings", offerings], ["Programs", programmes], ["Programmes", programmes],
		["Program", programme], ["Programme", programme], ["Assessment Operations", `${assessment} Operations`],
		["Assessment Plans", `${assessment} Plans`], ["Assessment Results", `${assessment} Results`],
		["Assessments & Results", `${assessments} & Results`],
	].filter(([from, to]) => from && to && from !== to).sort((left, right) => right[0].length - left[0].length);
}

function replaceValue(value, pairs) {
	let next = String(value || "");
	for (const [from, to] of pairs) next = next.split(from).join(to);
	return next;
}

function applyVisibleFriendlyNames(root = document.body) {
	if (!root || !isEduEdgeSurface()) return;
	const pairs = friendlyPairs();
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
		const next = replaceValue(node.nodeValue, pairs);
		if (next !== node.nodeValue) node.nodeValue = next;
	}
	for (const element of root.querySelectorAll?.("[placeholder], [title], [aria-label]") || []) {
		for (const attribute of ["placeholder", "title", "aria-label"]) {
			if (!element.hasAttribute(attribute)) continue;
			const current = element.getAttribute(attribute) || "";
			const next = replaceValue(current, pairs);
			if (next !== current) element.setAttribute(attribute, next);
		}
	}
}

let terminologyScheduled = false;
function scheduleVisibleFriendlyNames() {
	if (terminologyScheduled) return;
	terminologyScheduled = true;
	requestAnimationFrame(() => {
		terminologyScheduled = false;
		applyVisibleFriendlyNames();
	});
}

function initialiseEduEdgeMenu() {
	setDensity(getDensity());
	registerEduEdgeProductMenu();
	scheduleVisibleFriendlyNames();
	if (!window.__eduedgeFriendlyNameObserver && document.body) {
		window.__eduedgeFriendlyNameObserver = new MutationObserver(scheduleVisibleFriendlyNames);
		window.__eduedgeFriendlyNameObserver.observe(document.body, { childList: true, subtree: true });
	}
}

window.openEduEdgeCommandPalette = openEduEdgeCommandPalette;
window.setEduEdgeDensity = setDensity;
window.addEventListener("edgesuite:command-palette-request", (event) => {
	if (event.detail?.handled || !isEduEdgeSurface()) return;
	event.detail.handled = openEduEdgeCommandPalette();
});
window.addEventListener("edgesuite:favorites-changed", registerEduEdgeProductMenu);

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialiseEduEdgeMenu, { once: true });
else initialiseEduEdgeMenu();

["desktop_screen", "sidebar_setup", "toolbar_setup", "page-change"].forEach((eventName) => {
	document.addEventListener(eventName, initialiseEduEdgeMenu);
});
window.addEventListener("eduedge:institution-context-changed", initialiseEduEdgeMenu);
