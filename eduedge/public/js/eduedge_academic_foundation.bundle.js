import EduEdgeAcademicFoundation from "./eduedge_academic_foundation/EduEdgeAcademicFoundation.vue";
import { installAcademicFoundationQaFixes } from "./eduedge_academic_foundation/qa_fixes";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

installAcademicFoundationQaFixes(EduEdgeAcademicFoundation);

window.EduEdgeAcademicFoundation = EduEdgeAcademicFoundation;
window.createEduEdgeAcademicFoundationApp = function createEduEdgeAcademicFoundationApp(props = {}) {
	return createEduEdgeApp(EduEdgeAcademicFoundation, props);
};
