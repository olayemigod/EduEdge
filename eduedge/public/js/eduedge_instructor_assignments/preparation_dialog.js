import InstructorAssignmentPreparationDialog from "../eduedge_ui/components/InstructorAssignmentPreparationDialog.vue";
import { createEduEdgeApp } from "../eduedge_ui/app_factory";

export function openInstructorAssignmentPreparationDialog({ item, displayContext = {}, onBusy, onComplete }) {
	if (!item?.name) return null;

	const host = document.createElement("div");
	host.className = "eduedge-instructor-assignment-preparation-host";
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

	app = createEduEdgeApp(InstructorAssignmentPreparationDialog, {
		item,
		displayContext,
		onBusy,
		onComplete,
		onClosed: cleanup,
	});
	app.mount(host);
	return { app, host, close: cleanup };
}
