import EduEdgeSessionLaunchPanel from "./eduedge_ui/components/EduEdgeSessionLaunchPanel.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeSessionLaunchApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeSessionLaunchPanel, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeSessionLaunch = EduEdgeSessionLaunchPanel;
	window.createEduEdgeSessionLaunchApp = createEduEdgeSessionLaunchApp;
}

export default EduEdgeSessionLaunchPanel;
