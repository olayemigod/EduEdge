import EduEdgeHome from "./eduedge_home/EduEdgeHome.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeHomeApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeHome, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeHome = EduEdgeHome;
	window.createEduEdgeHomeApp = createEduEdgeHomeApp;
}

export default EduEdgeHome;
