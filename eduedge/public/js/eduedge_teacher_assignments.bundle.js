import EduEdgeInstructorAssignments from "./eduedge_instructor_assignments/EduEdgeInstructorAssignments.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeInstructorAssignmentsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeInstructorAssignments, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeInstructorAssignments = EduEdgeInstructorAssignments;
	window.createEduEdgeInstructorAssignmentsApp = createEduEdgeInstructorAssignmentsApp;

	// Backward-compatible globals for older cached page loaders.
	window.EduEdgeTeacherAssignments = EduEdgeInstructorAssignments;
	window.createEduEdgeTeacherAssignmentsApp = createEduEdgeInstructorAssignmentsApp;
}

export default EduEdgeInstructorAssignments;
