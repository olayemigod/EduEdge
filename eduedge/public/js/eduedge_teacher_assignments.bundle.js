import EduEdgeTeacherAssignments from "./eduedge_instructor_assignments/EduEdgeInstructorAssignments.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeTeacherAssignmentsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeTeacherAssignments, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeTeacherAssignments = EduEdgeTeacherAssignments;
	window.createEduEdgeTeacherAssignmentsApp = createEduEdgeTeacherAssignmentsApp;

	// Backward-compatible globals for older page loaders and saved browser sessions.
	window.EduEdgeInstructorAssignments = EduEdgeTeacherAssignments;
	window.createEduEdgeInstructorAssignmentsApp = createEduEdgeTeacherAssignmentsApp;
}

export default EduEdgeTeacherAssignments;
