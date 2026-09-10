import EduEdgeLessonPlans from "./eduedge_lesson_plans/EduEdgeLessonPlans.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeLessonPlansApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeLessonPlans, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeLessonPlans = EduEdgeLessonPlans;
	window.createEduEdgeLessonPlansApp = createEduEdgeLessonPlansApp;
}

export default EduEdgeLessonPlans;
