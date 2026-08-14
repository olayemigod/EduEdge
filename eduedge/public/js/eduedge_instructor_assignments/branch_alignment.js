import EduEdgeInstructorAssignments from "./EduEdgeInstructorAssignments.vue";

const LEGACY_BRANCH_ONLY_SCOPE = "Branch Access Only";
const STYLE_ID = "eduedge-instructor-branch-alignment-style";

function assignmentRoot() {
	return document.querySelector(".eduedge-instructor-assignments-root");
}

function panelByHeading(title) {
	const root = assignmentRoot();
	if (!root) return null;
	return [...root.querySelectorAll(".assignment-panel")].find(
		(panel) => panel.querySelector(".assignment-heading h2")?.textContent?.trim() === title,
	) || null;
}

function ensureStyles() {
	if (typeof document === "undefined" || document.getElementById(STYLE_ID)) return;
	const style = document.createElement("style");
	style.id = STYLE_ID;
	style.textContent = `
		.eduedge-instructor-branch-boundary {
			background: var(--edge-color-surface-muted, var(--card-bg));
			border: 1px solid var(--edge-color-border, var(--border-color));
			border-radius: 10px;
			color: var(--edge-color-ink-800, var(--text-color));
			display: grid;
			gap: .25rem;
			margin: .65rem 0 .85rem;
			padding: .7rem .8rem;
		}
		.eduedge-instructor-branch-boundary strong { font-size: .78rem; }
		.eduedge-instructor-branch-boundary span,
		.eduedge-instructor-branch-boundary small {
			color: var(--edge-color-ink-500, var(--text-muted));
			font-size: .72rem;
			line-height: 1.45;
		}
	`;
	document.head.appendChild(style);
}

function syncPlannerLanguage(root) {
	if (!root) return;
	for (const button of root.querySelectorAll("button")) {
		if (button.textContent?.trim() === "Add Branch Access Row") {
			button.textContent = "Add Branch Eligibility Row";
		}
	}
	for (const option of root.querySelectorAll("select option")) {
		if (option.value === LEGACY_BRANCH_ONLY_SCOPE || option.textContent?.trim() === LEGACY_BRANCH_ONLY_SCOPE) {
			option.textContent = "Branch Eligibility Only";
		}
	}
	for (const label of root.querySelectorAll(".preview-metrics span")) {
		if (label.textContent?.trim() === "Branch access changes") {
			label.textContent = "Branch eligibility changes";
		}
	}
}

function syncEligibilityBoundary() {
	const panel = panelByHeading("Branch Eligibility Periods");
	if (!panel || panel.querySelector("[data-eduedge-instructor-branch-boundary]")) return;
	const heading = panel.querySelector(":scope > .assignment-heading");
	if (!heading) return;
	const note = document.createElement("div");
	note.className = "eduedge-instructor-branch-boundary";
	note.dataset.eduedgeInstructorBranchBoundary = "1";
	note.innerHTML = `
		<strong>Instructor Branch Eligibility is not User Branch Access.</strong>
		<span>Eligibility defines the Branches where this Instructor may receive academic responsibilities. It does not grant the linked User permission to operate in those Branches.</span>
		<small>User access, Branch switching and security scope are managed separately under Branch Governance. The header Branch is navigation context and does not narrow this Instructor's eligibility history.</small>
	`;
	heading.insertAdjacentElement("afterend", note);
}

function syncPresentation() {
	ensureStyles();
	const root = assignmentRoot();
	if (!root) return;
	syncPlannerLanguage(root);
	syncEligibilityBoundary();
}

function install(component) {
	if (!component || component.__eduedgeInstructorBranchAlignmentInstalled) return;
	component.__eduedgeInstructorBranchAlignmentInstalled = true;
	const methods = component.methods || (component.methods = {});

	const existingRowTitle = methods.rowTitle;
	if (typeof existingRowTitle === "function") {
		methods.rowTitle = function (row) {
			if (row?.assignment_scope === LEGACY_BRANCH_ONLY_SCOPE) {
				return `${this.branchLabel?.(row.branch) || "Branch"} · Branch eligibility`;
			}
			return existingRowTitle.call(this, row);
		};
	}

	const existingLoad = methods.load;
	if (typeof existingLoad === "function") {
		methods.load = async function (...args) {
			const result = await existingLoad.apply(this, args);
			await this.$nextTick?.();
			syncPresentation();
			return result;
		};
	}

	const existingAddBranchAccessRow = methods.addBranchAccessRow;
	if (typeof existingAddBranchAccessRow === "function") {
		methods.addBranchAccessRow = function (...args) {
			const result = existingAddBranchAccessRow.apply(this, args);
			this.$nextTick?.(() => syncPresentation());
			return result;
		};
	}

	const existingPreviewPlan = methods.previewPlan;
	if (typeof existingPreviewPlan === "function") {
		methods.previewPlan = async function (...args) {
			const result = await existingPreviewPlan.apply(this, args);
			await this.$nextTick?.();
			syncPresentation();
			return result;
		};
	}

	const existingMounted = component.mounted;
	component.mounted = function (...args) {
		const result = typeof existingMounted === "function" ? existingMounted.apply(this, args) : undefined;
		this.$nextTick?.(() => syncPresentation());
		return result;
	};
}

install(EduEdgeInstructorAssignments);

export function installInstructorBranchAlignment(component = EduEdgeInstructorAssignments) {
	install(component);
}
