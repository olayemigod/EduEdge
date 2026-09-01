import EduEdgeInstructorAssignments from "./eduedge_instructor_assignments/EduEdgeInstructorAssignments.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";
import { EDUEDGE_MENU_ITEMS } from "./eduedge_ui/navigation";

function normalizeInstructorAssignmentMenu() {
	for (const group of EDUEDGE_MENU_ITEMS || []) {
		for (const item of group.items || []) {
			if (item.route !== "/app/eduedge-instructor-assignments") continue;
			item.label = __("Instructor Assignments");
			item.description = __("Assign Instructors across Institutions, Branches, Classes, Class Arms, and Subjects");
		}
	}
}

normalizeInstructorAssignmentMenu();

export function createEduEdgeInstructorAssignmentsApp(rootProps = null) {
	normalizeInstructorAssignmentMenu();
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
