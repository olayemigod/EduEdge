import EduEdgeResourceCenter from "./eduedge_resource_center/EduEdgeResourceCenter.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

window.EduEdgeResourceCenter = EduEdgeResourceCenter;
window.createEduEdgeResourceCenterApp = function createEduEdgeResourceCenterApp(props = {}) {
	return createEduEdgeApp(EduEdgeResourceCenter, props);
};
