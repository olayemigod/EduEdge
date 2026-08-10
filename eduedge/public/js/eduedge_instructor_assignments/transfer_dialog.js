import InstructorAssignmentTransferDialog from "../eduedge_ui/components/InstructorAssignmentTransferDialog.vue";
import { createEduEdgeApp } from "../eduedge_ui/app_factory";

export function openInstructorAssignmentTransferDialog({ item, displayContext = {}, onBusy, onComplete }) {
	if (!item?.name) return null;

	const host = document.createElement("div");
	host.className = "eduedge-instructor-assignment-transfer-host";
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

	app = createEduEdgeApp(InstructorAssignmentTransferDialog, {
		item,
		displayContext,
		onBusy,
		onComplete,
		onClosed: cleanup,
	});
	app.mount(host);
	return { app, host, close: cleanup };
}
