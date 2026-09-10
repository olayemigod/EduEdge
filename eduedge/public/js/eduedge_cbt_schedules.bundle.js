import EduEdgeCBTSchedules from "./eduedge_cbt_schedules/EduEdgeCBTSchedules.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeCBTSchedulesApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeCBTSchedules, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeCBTSchedules = EduEdgeCBTSchedules;
	window.createEduEdgeCBTSchedulesApp = createEduEdgeCBTSchedulesApp;
}

export default EduEdgeCBTSchedules;
