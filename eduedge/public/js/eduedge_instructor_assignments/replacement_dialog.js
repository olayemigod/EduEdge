import InstructorAssignmentReplacementDialog from "../eduedge_ui/components/InstructorAssignmentReplacementDialog.vue";
import { createEduEdgeApp } from "../eduedge_ui/app_factory";

export function openInstructorAssignmentReplacementDialog({ item, instructors = [], onBusy, onComplete }) {
	if (!item?.name) return null;

	const host = document.createElement("div");
	host.className = "eduedge-instructor-assignment-replacement-host";
	document.body.appendChild(host);

	let app = null;
	let closed = false;
	const cleanup = () => {
		if (closed) return;
		closed = true;
		window.setTimeout(() => {
			try {
				app?.unmount?.();
			} finally {
				host.remove();
			}
		}, 0);
	};

	app = createEduEdgeApp(InstructorAssignmentReplacementDialog, {
		item,
		instructors,
		onBusy,
		onComplete,
		onClosed: cleanup,
	});
	app.mount(host);
	return { app, host, close: cleanup };
}
