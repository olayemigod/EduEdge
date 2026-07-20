import EduEdgeSetupCenter from "./eduedge_setup_center/EduEdgeSetupCenter.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeSetupCenterApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeSetupCenter, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeSetupCenter = EduEdgeSetupCenter;
	window.createEduEdgeSetupCenterApp = createEduEdgeSetupCenterApp;
}

export default EduEdgeSetupCenter;
