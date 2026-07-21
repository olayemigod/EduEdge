import EduEdgeCBTOperations from "./eduedge_cbt_operations/EduEdgeCBTOperations.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeCBTOperationsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeCBTOperations, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeCBTOperations = EduEdgeCBTOperations;
	window.createEduEdgeCBTOperationsApp = createEduEdgeCBTOperationsApp;
}

export default EduEdgeCBTOperations;
