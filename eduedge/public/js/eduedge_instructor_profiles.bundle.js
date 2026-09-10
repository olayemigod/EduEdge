import EduEdgeInstructors from "./eduedge_instructors/EduEdgeInstructors.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeInstructorProfilesApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeInstructors, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeInstructorProfiles = EduEdgeInstructors;
	window.createEduEdgeInstructorProfilesApp = createEduEdgeInstructorProfilesApp;

	// Backward-compatible globals for older page loaders and saved browser sessions.
	window.EduEdgeInstructors = EduEdgeInstructors;
	window.createEduEdgeInstructorsApp = createEduEdgeInstructorProfilesApp;
}

export default EduEdgeInstructors;
