import EduEdgeInstructors from "./eduedge_instructors/EduEdgeInstructors.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeInstructorsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeInstructors, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeInstructors = EduEdgeInstructors;
	window.createEduEdgeInstructorsApp = createEduEdgeInstructorsApp;
}

export default EduEdgeInstructors;
