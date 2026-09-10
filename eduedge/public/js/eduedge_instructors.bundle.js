import EduEdgeInstructors from "./eduedge_instructors/EduEdgeInstructors.vue";
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

export function createEduEdgeInstructorsApp(rootProps = null) {
	normalizeInstructorAssignmentMenu();
	return createEduEdgeApp(EduEdgeInstructors, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeInstructors = EduEdgeInstructors;
	window.createEduEdgeInstructorsApp = createEduEdgeInstructorsApp;
}

export default EduEdgeInstructors;
