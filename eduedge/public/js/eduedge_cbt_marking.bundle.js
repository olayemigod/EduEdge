import EduEdgeCBTMarking from "./eduedge_cbt_marking/EduEdgeCBTMarking.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeCBTMarkingApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeCBTMarking, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeCBTMarking = EduEdgeCBTMarking;
	window.createEduEdgeCBTMarkingApp = createEduEdgeCBTMarkingApp;
}

export default EduEdgeCBTMarking;
