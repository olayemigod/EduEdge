import EduEdgeStudents from "./eduedge_students/EduEdgeStudents.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeStudentsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeStudents, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeStudents = EduEdgeStudents;
	window.createEduEdgeStudentsApp = createEduEdgeStudentsApp;
}

export default EduEdgeStudents;
