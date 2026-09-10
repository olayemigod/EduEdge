import EduEdgeStudentEnrollments from "./eduedge_student_enrollments/EduEdgeStudentEnrollments.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeStudentEnrollmentsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeStudentEnrollments, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeStudentEnrollments = EduEdgeStudentEnrollments;
	window.createEduEdgeStudentEnrollmentsApp = createEduEdgeStudentEnrollmentsApp;
}

export default EduEdgeStudentEnrollments;
