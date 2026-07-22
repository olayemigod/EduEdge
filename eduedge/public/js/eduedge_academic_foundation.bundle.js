import EduEdgeAcademicFoundation from "./eduedge_academic_foundation/EduEdgeAcademicFoundation.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

window.EduEdgeAcademicFoundation = EduEdgeAcademicFoundation;
window.createEduEdgeAcademicFoundationApp = function createEduEdgeAcademicFoundationApp(props = {}) {
	return createEduEdgeApp(EduEdgeAcademicFoundation, props);
};
