import { createApp } from "vue";

import EduEdgeSetupCenter from "./eduedge_setup_center/EduEdgeSetupCenter.vue";

export function createEduEdgeSetupCenterApp(rootProps = null) {
	const runtime = window.EdgeSuiteUI || window.EdgeUI;
	if (!runtime?.install || !runtime?.components?.EdgeAppShell) {
		throw new Error("The standalone EdgeSuite UI runtime is unavailable or incomplete.");
	}

	// The EduEdge SFC and its render helpers must use the same Vue runtime that
	// creates the application. EdgeSuite components are then registered on that
	// application through the public runtime contract.
	const app = createApp(EduEdgeSetupCenter, rootProps || {});
	runtime.install(app);
	return app;
}

if (typeof window !== "undefined") {
	window.EduEdgeSetupCenter = EduEdgeSetupCenter;
	window.createEduEdgeSetupCenterApp = createEduEdgeSetupCenterApp;
}

export default EduEdgeSetupCenter;
