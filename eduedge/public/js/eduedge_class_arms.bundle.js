import EduEdgeClassArms from "./eduedge_class_arms/EduEdgeClassArms.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeClassArmsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeClassArms, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeClassArms = EduEdgeClassArms;
	window.createEduEdgeClassArmsApp = createEduEdgeClassArmsApp;
}

export default EduEdgeClassArms;
