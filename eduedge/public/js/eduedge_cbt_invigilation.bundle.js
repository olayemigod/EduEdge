import EduEdgeCBTInvigilation from "./eduedge_cbt_invigilation/EduEdgeCBTInvigilation.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeCBTInvigilationApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeCBTInvigilation, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeCBTInvigilation = EduEdgeCBTInvigilation;
	window.createEduEdgeCBTInvigilationApp = createEduEdgeCBTInvigilationApp;
}

export default EduEdgeCBTInvigilation;
