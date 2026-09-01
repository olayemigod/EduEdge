import InstructorAssignmentEndDialog from "./eduedge_ui/components/InstructorAssignmentEndDialog.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeInstructorAssignmentEndApp(rootProps = null) {
	return createEduEdgeApp(InstructorAssignmentEndDialog, rootProps);
}

function ensureGovernanceThemeBridge() {
	if (document.getElementById("eduedge-assignment-governance-theme-bridge")) return;
	const style = document.createElement("style");
	style.id = "eduedge-assignment-governance-theme-bridge";
	style.textContent = `
		.eduedge-assignment-governance { color: var(--edge-color-ink-950, #122033); }
		.eduedge-assignment-governance__source { background: var(--edge-color-surface-muted, var(--edge-color-surface, #ffffff)) !important; color: var(--edge-color-ink-950, #122033) !important; }
		.eduedge-assignment-governance__notice { background: var(--edge-color-surface, transparent); color: var(--edge-color-ink-950, #122033); }
		.eduedge-assignment-governance .form-control { background: var(--edge-color-control-surface, var(--edge-color-surface, #ffffff)) !important; border-color: var(--edge-color-control-border, var(--edge-color-border, #d8e2ee)) !important; color: var(--edge-color-control-text, var(--edge-color-ink-950, #122033)) !important; }
		.eduedge-assignment-governance .form-control::placeholder { color: var(--edge-color-ink-400, #8998a8) !important; opacity: 1; }
	`;
	document.head.appendChild(style);
}

function showDialog(proxy, item) {
	if (!item?.name || !proxy?.canEndAssignment?.(item)) return null;
	const host = document.createElement("div");
	host.className = "eduedge-instructor-assignment-end-host";
	document.body.appendChild(host);
	let app = null;
	let closed = false;
	const cleanup = () => {
		if (closed) return;
		closed = true;
		window.setTimeout(() => {
			try { app?.unmount?.(); } finally { host.remove(); }
		}, 0);
	};
	app = createEduEdgeInstructorAssignmentEndApp({
		item,
		onBusy: (name) => { proxy.endingAssignment = name || ""; },
		onComplete: async () => { await proxy.load?.(); },
		onClosed: cleanup,
	});
	app.mount(host);
	return { app, host, close: cleanup };
}

function install(component) {
	if (!component || component.__eduedgeAssignmentEndDialogInstalled) return false;
	component.__eduedgeAssignmentEndDialogInstalled = true;
	const methods = component.methods || (component.methods = {});
	methods.endAssignment = function (item) { return showDialog(this, item); };
	return true;
}

export function installInstructorAssignmentEndDialog(component = window.EduEdgeInstructorAssignments) {
	ensureGovernanceThemeBridge();
	return install(component);
}

function installWhenReady(attempt = 0) {
	if (installInstructorAssignmentEndDialog(window.EduEdgeInstructorAssignments)) return;
	if (attempt < 100) window.setTimeout(() => installWhenReady(attempt + 1), 25);
}

if (typeof window !== "undefined") {
	window.createEduEdgeInstructorAssignmentEndApp = createEduEdgeInstructorAssignmentEndApp;
	window.installInstructorAssignmentEndDialog = installInstructorAssignmentEndDialog;
	installWhenReady();
}
