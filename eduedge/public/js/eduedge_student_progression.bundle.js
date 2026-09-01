import EduEdgeStudentProgression from "./eduedge_student_progression/EduEdgeStudentProgression.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeStudentProgressionApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeStudentProgression, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeStudentProgression = EduEdgeStudentProgression;
	window.createEduEdgeStudentProgressionApp = createEduEdgeStudentProgressionApp;
}

export default EduEdgeStudentProgression;
