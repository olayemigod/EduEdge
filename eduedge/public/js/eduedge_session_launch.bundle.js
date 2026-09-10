import EduEdgeSessionLaunch from "./eduedge_session_launch/EduEdgeSessionLaunch.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeSessionLaunchApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeSessionLaunch, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeSessionLaunch = EduEdgeSessionLaunch;
	window.createEduEdgeSessionLaunchApp = createEduEdgeSessionLaunchApp;
}

export default EduEdgeSessionLaunch;
