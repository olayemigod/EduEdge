import InstructorAssignmentEndDialog from "./eduedge_ui/components/InstructorAssignmentEndDialog.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeInstructorAssignmentEndApp(rootProps = null) {
	return createEduEdgeApp(InstructorAssignmentEndDialog, rootProps);
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
	if (!component || component.__eduedgeAssignmentEndDialogInstalled) return;
	component.__eduedgeAssignmentEndDialogInstalled = true;
	const methods = component.methods || (component.methods = {});
	methods.endAssignment = function (item) { return showDialog(this, item); };
}

export function installInstructorAssignmentEndDialog(component = window.EduEdgeInstructorAssignments) {
	install(component);
}

installInstructorAssignmentEndDialog(window.EduEdgeInstructorAssignments);
window.createEduEdgeInstructorAssignmentEndApp = createEduEdgeInstructorAssignmentEndApp;
window.installInstructorAssignmentEndDialog = installInstructorAssignmentEndDialog;
