import EduEdgeTeachingSchedule from "./eduedge_teaching_schedule/EduEdgeTeachingSchedule.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeTeachingScheduleApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeTeachingSchedule, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeTeachingSchedule = EduEdgeTeachingSchedule;
	window.createEduEdgeTeachingScheduleApp = createEduEdgeTeachingScheduleApp;
}

export default EduEdgeTeachingSchedule;
